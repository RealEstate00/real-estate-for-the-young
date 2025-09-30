-- ============================================================================
-- Real Estate for the Young - Database Schema
-- ============================================================================

-- ============================================================================
-- RTMS (Real Transaction Management System) Schema
-- 국토교통부 실거래가 데이터
-- ============================================================================

-- 실거래가 - 전월세 - 원본 데이터 테이블 (통합)
CREATE TABLE IF NOT EXISTS rtms.transactions_rent (
    id BIGSERIAL PRIMARY KEY,
    
    -- 주택 유형 및 위치 정보
    building_type VARCHAR(20) NOT NULL,  -- '단독다가구', '아파트', '연립다세대', '오피스텔'
    sigungu VARCHAR(100) NOT NULL,       -- 시군구 (예: '서울특별시 강남구')
    dong VARCHAR(100),                   -- 법정동/단지명
    emd_code VARCHAR(10),                -- 읍면동 코드
    building_name VARCHAR(200),          -- 아파트명/건물명 (단독다가구는 NULL)
    
    -- 면적 및 층 정보
    area_type VARCHAR(20) NOT NULL,         -- 면적 유형 ('전용면적', '계약면적')
    area_m2 DECIMAL(10, 2) NOT NULL,         -- 면적(㎡)
    area_range VARCHAR(20),                  -- 면적구간 ('~60', '60~85', '85~102', '102~135', '135~')
    floor INT,                               -- 층 (단독다가구는 NULL)
    
    -- 계약 정보
    contract_type VARCHAR(10) NOT NULL,      -- 계약구분 ('전세', '월세')
    contract_year_month INT NOT NULL,        -- 계약년월 (YYYYMM)
    deposit_amount BIGINT NOT NULL,          -- 보증금(원)
    monthly_rent BIGINT NOT NULL DEFAULT 0,  -- 월세금(원)
    
    -- 환산가액 (계산 컬럼)
    converted_price DECIMAL(15, 2),          -- 환산가액 = (보증금 + 월세*100) / 면적
    
    -- 건축 및 계약기간
    construction_year INT,                   -- 건축년도
    contract_month VARCHAR(10),              -- 계약월 (예: '상순', '중순', '하순')
    use_type VARCHAR(20),                    -- 전용구분 (예: '거주용', '오피스텔(주거용)')
    contract_start_ym INT,                   -- 계약기간시작 (YYYYMM)
    contract_end_ym INT,                     -- 계약기간끝 (YYYYMM)
    
    -- 메타 정보
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- 복합 유니크 제약조건 (중복 거래 방지)
    CONSTRAINT uq_rtms_transaction UNIQUE (
        building_type, sigungu, dong, building_name, 
        area_m2, floor, contract_year_month, 
        deposit_amount, monthly_rent, contract_type
    )
);

-- 인덱스 생성 (쿼리 성능 최적화)
CREATE INDEX IF NOT EXISTS idx_rtms_building_type ON rtms.transactions_rent(building_type);
CREATE INDEX IF NOT EXISTS idx_rtms_area_range ON rtms.transactions_rent(area_range);
CREATE INDEX IF NOT EXISTS idx_rtms_contract_ym ON rtms.transactions_rent(contract_year_month);
CREATE INDEX IF NOT EXISTS idx_rtms_sigungu ON rtms.transactions_rent(sigungu);
CREATE INDEX IF NOT EXISTS idx_rtms_composite ON rtms.transactions_rent(building_type, area_range, contract_year_month);
CREATE INDEX IF NOT EXISTS idx_rtms_dong ON rtms.transactions_rent(dong) WHERE dong IS NOT NULL;

-- 환산가액 자동 계산 트리거 함수
CREATE OR REPLACE FUNCTION rtms.calculate_converted_price()
RETURNS TRIGGER AS $$
BEGIN
    -- 면적구간 자동 계산
    NEW.area_range := CASE 
        WHEN NEW.area_m2 <= 60 THEN '~60이하'
        WHEN NEW.area_m2 > 60 AND NEW.area_m2 <= 85 THEN '60초과~85이하'
        WHEN NEW.area_m2 > 85 AND NEW.area_m2 <= 102 THEN '85초과~102이하'
        WHEN NEW.area_m2 > 102 AND NEW.area_m2 <= 135 THEN '102초과~135이하'
        ELSE '135초과~'
    END;
    
    -- 환산가액 계산: (전세금 + 월세*100) / 면적
    IF NEW.area_m2 > 0 THEN
        NEW.converted_price := (NEW.deposit_amount + NEW.monthly_rent * 100.0) / NEW.area_m2;
    ELSE
        NEW.converted_price := NULL;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 트리거 생성
DROP TRIGGER IF EXISTS trigger_calculate_converted_price ON rtms.transactions_rent;
CREATE TRIGGER trigger_calculate_converted_price
    BEFORE INSERT OR UPDATE ON rtms.transactions_rent
    FOR EACH ROW
    EXECUTE FUNCTION rtms.calculate_converted_price();

-- ============================================================================
-- 면적구간별 통계 Materialized View (성능 최적화용)
-- ============================================================================

CREATE MATERIALIZED VIEW IF NOT EXISTS rtms.area_statistics_rent AS
SELECT 
    building_type,
    area_range,
    contract_year_month,
    sigungu,
    COUNT(*) as transaction_count,
    ROUND(AVG(converted_price)::numeric, 2) as avg_converted_price,
    ROUND(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY converted_price)::numeric, 2) as median_converted_price,
    ROUND(MIN(converted_price)::numeric, 2) as min_converted_price,
    ROUND(MAX(converted_price)::numeric, 2) as max_converted_price,
    ROUND(AVG(deposit_amount)::numeric, 0) as avg_deposit,
    ROUND(AVG(monthly_rent)::numeric, 0) as avg_monthly_rent,
    ROUND(AVG(area_m2)::numeric, 2) as avg_area
FROM rtms.transactions_rent
GROUP BY building_type, area_range, contract_year_month, sigungu;

-- Materialized View 인덱스
CREATE INDEX IF NOT EXISTS idx_area_stats_composite 
    ON rtms.area_statistics_rent(building_type, area_range, contract_year_month);

-- Materialized View 갱신 함수
CREATE OR REPLACE FUNCTION rtms.refresh_area_statistics_rent()
RETURNS void AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY rtms.area_statistics_rent;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- 유틸리티 뷰 (간편 조회용)
-- ============================================================================

-- 최근 거래 통계 뷰 (최근 6개월)
CREATE OR REPLACE VIEW rtms.recent_statistics_rent AS
SELECT 
    building_type,
    area_range,
    contract_year_month,
    COUNT(*) as transaction_count,
    ROUND(AVG(converted_price)::numeric, 2) as avg_converted_price,
    ROUND(AVG(deposit_amount)::numeric, 0) as avg_deposit,
    ROUND(AVG(monthly_rent)::numeric, 0) as avg_monthly_rent
FROM rtms.transactions_rent
WHERE contract_year_month >= TO_CHAR(CURRENT_DATE - INTERVAL '6 months', 'YYYYMM')::INTEGER
GROUP BY building_type, area_range, contract_year_month
ORDER BY contract_year_month DESC, building_type, area_range;

-- 시군구별 평균 환산가액 뷰
CREATE OR REPLACE VIEW rtms.sigungu_avg_price_rent AS
SELECT 
    sigungu,
    building_type,
    area_range,
    COUNT(*) as transaction_count,
    ROUND(AVG(converted_price)::numeric, 2) as avg_converted_price,
    MAX(contract_year_month) as latest_contract_ym
FROM rtms.transactions_rent
WHERE contract_year_month >= TO_CHAR(CURRENT_DATE - INTERVAL '1 year', 'YYYYMM')::INTEGER
GROUP BY sigungu, building_type, area_range
ORDER BY sigungu, building_type, area_range;

-- ============================================================================
-- 스키마 생성 (가장 먼저 실행)
-- ============================================================================
CREATE SCHEMA IF NOT EXISTS rtms;

-- ============================================================================
-- 주석 추가
-- ============================================================================
COMMENT ON TABLE rtms.transactions_rent IS '국토교통부 실거래가 전월세 원본 데이터';
COMMENT ON COLUMN rtms.transactions_rent.building_type IS '주택유형: 단독다가구, 아파트, 연립다세대, 오피스텔';
COMMENT ON COLUMN rtms.transactions_rent.area_range IS '면적구간: ~60이하, 60초과~85이하, 85초과~102이하, 102초과~135이하, 135초과~';
COMMENT ON COLUMN rtms.transactions_rent.converted_price IS '환산가액 = (보증금 + 월세*100) / 면적 (만원/㎡)';
COMMENT ON MATERIALIZED VIEW rtms.area_statistics_rent IS '면적구간별 통계 집계 (성능 최적화용)';
