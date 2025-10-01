-- ============================================================================
-- Real Estate for the Young - Database Schema
-- ============================================================================

-- ============================================================================
-- RTMS (Real Transaction Management System) Schema
-- 국토교통부 실거래가 데이터
-- ============================================================================

-- 스키마 생성 (가장 먼저 실행)
CREATE SCHEMA IF NOT EXISTS rtms;

-- ============================================================================
-- 기존 객체 삭제 (스키마 변경 시) -- 스키마 변경 필요 없어지면 주석처리하거나 삭제
-- ============================================================================
DROP VIEW IF EXISTS rtms.recent_statistics_rent CASCADE;
DROP VIEW IF EXISTS rtms.sigungudong_avg_price_rent CASCADE;
DROP MATERIALIZED VIEW IF EXISTS rtms.statistics_rent CASCADE;
DROP MATERIALIZED VIEW IF EXISTS rtms.area_statistics_rent CASCADE;
DROP TABLE IF EXISTS rtms.code_building_type CASCADE;
DROP TABLE IF EXISTS rtms.code_area_range CASCADE;
DROP TABLE IF EXISTS rtms.code_table CASCADE;
DROP TRIGGER IF EXISTS trigger_calculate_converted_price ON rtms.transactions_rent;
DROP FUNCTION IF EXISTS rtms.calculate_converted_price();
DROP FUNCTION IF EXISTS rtms.refresh_statistics_rent();
DROP FUNCTION IF EXISTS rtms.refresh_area_statistics_rent();

-- ============================================================================
-- 실거래가 - 전월세 - 원본 데이터 테이블 (통합)
-- ============================================================================
CREATE TABLE IF NOT EXISTS rtms.transactions_rent (
    id BIGSERIAL PRIMARY KEY,
    
    -- 주택 유형 및 위치 정보
    building_type VARCHAR(20) NOT NULL,      -- '단독다가구', '아파트', '연립다세대', '오피스텔'
    sigungudong VARCHAR(150) NOT NULL,       -- 시군구+법정동 (예: '서울특별시 강남구 대치동')
    emd_code VARCHAR(10),                    -- 법정동 코드 10자리
    road_address VARCHAR(200),               -- 도로명 주소
    building_name VARCHAR(200),              -- 아파트명/건물명 (단독다가구는 NULL)
    
    -- 면적 및 층 정보
    area_type VARCHAR(20) NOT NULL,         -- 면적 유형 ('전용면적', '계약면적')
    area_m2 DECIMAL(10, 2) NOT NULL,         -- 면적(㎡)
    area_range VARCHAR(20),                  -- 면적구간 ('~60', '60~85', '85~102', '102~135', '135~')
    floor INT,                               -- 층 (단독다가구는 NULL)
    
    -- 계약 정보
    contract_type VARCHAR(10) NOT NULL,      -- 계약구분 ('전세', '월세')
    contract_year_month INT NOT NULL,        -- 계약년월 (YYYYMM)
    contract_status VARCHAR(10),             -- 계약상태 ('신규', '갱신')
    contract_start_ym INT,                   -- 계약기간시작 (YYYYMM)
    contract_end_ym INT,                     -- 계약기간끝 (YYYYMM)
    deposit_amount BIGINT NOT NULL,          -- 보증금(원)
    monthly_rent BIGINT NOT NULL DEFAULT 0,  -- 월세금(원)
    
    -- 환산가액 (계산 컬럼)
    converted_price DECIMAL(15, 2),          -- 환산가액 = (보증금 + 월세*100) / 면적
    
    -- 건축년도
    construction_year INT,                   -- 건축년도
    
    
    -- 메타 정보
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 인덱스 생성 (쿼리 성능 최적화)
CREATE INDEX IF NOT EXISTS idx_rtms_building_type ON rtms.transactions_rent(building_type);
CREATE INDEX IF NOT EXISTS idx_rtms_area_range ON rtms.transactions_rent(area_range);
CREATE INDEX IF NOT EXISTS idx_rtms_contract_ym ON rtms.transactions_rent(contract_year_month);
CREATE INDEX IF NOT EXISTS idx_rtms_sigungudong ON rtms.transactions_rent(sigungudong);
CREATE INDEX IF NOT EXISTS idx_rtms_emd_code ON rtms.transactions_rent(emd_code) WHERE emd_code IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_rtms_composite ON rtms.transactions_rent(building_type, area_range, contract_year_month);

-- 환산가액 자동 계산 트리거 함수 (JSONL에 값이 없을 때만 계산)
CREATE OR REPLACE FUNCTION rtms.calculate_converted_price()
RETURNS TRIGGER AS $$
BEGIN
    -- 면적구간 자동 계산 (NULL인 경우에만)
    IF NEW.area_range IS NULL THEN
        NEW.area_range := CASE 
            WHEN NEW.area_m2 <= 60 THEN '~60이하'
            WHEN NEW.area_m2 > 60 AND NEW.area_m2 <= 85 THEN '60초과~85이하'
            WHEN NEW.area_m2 > 85 AND NEW.area_m2 <= 102 THEN '85초과~102이하'
            WHEN NEW.area_m2 > 102 AND NEW.area_m2 <= 135 THEN '102초과~135이하'
            ELSE '135초과~'
        END;
    END IF;
    
    -- 환산가액 계산 (NULL인 경우에만)
    -- 환산가액 = (보증금 + 월세*100) / 면적 (원/㎡)
    IF NEW.converted_price IS NULL THEN
        IF NEW.area_m2 > 0 THEN
            NEW.converted_price := ((NEW.deposit_amount) + (NEW.monthly_rent) * 100.0) / NEW.area_m2;
        ELSE
            NEW.converted_price := NULL;
        END IF;
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
-- 테이블 주석
-- ============================================================================
COMMENT ON TABLE rtms.transactions_rent IS '국토교통부 실거래가 전월세 원본 데이터';
COMMENT ON COLUMN rtms.transactions_rent.building_type IS '주택유형: 단독다가구, 아파트, 연립다세대, 오피스텔';
COMMENT ON COLUMN rtms.transactions_rent.sigungudong IS '시군구+법정동 전체 주소';
COMMENT ON COLUMN rtms.transactions_rent.emd_code IS '법정동 코드 10자리';
COMMENT ON COLUMN rtms.transactions_rent.area_range IS '면적구간: ~60이하, 60초과~85이하, 85초과~102이하, 102초과~135이하, 135초과~';
COMMENT ON COLUMN rtms.transactions_rent.converted_price IS '환산가액 = (보증금 + 월세*100) / 면적 (원/㎡)';

-- ============================================================================
-- 코드 테이블 (통합)
-- ============================================================================
CREATE TABLE IF NOT EXISTS rtms.code_table (
    code VARCHAR(10) PRIMARY KEY,
    name_kr VARCHAR(50) NOT NULL,
    name_en VARCHAR(50),
    code_type VARCHAR(20) NOT NULL,            -- 코드 타입: 'building_type', 'area_range'
    description TEXT,
    display_order INT NOT NULL,
    
    -- 주택유형 전용 필드
    rtms_value VARCHAR(50),                    -- RTMS 원본값 (transactions_rent 조인 키)
    housing_code VARCHAR(10),                  -- Housing 코드 (housing.notices 조인 키)
    
    -- 면적구간 전용 필드
    min_area DECIMAL(5, 2),                    -- 최소 면적 (㎡)
    max_area DECIMAL(5, 2),                    -- 최대 면적 (㎡, NULL=무제한)
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 데이터 삽입: 주택유형 (5개)
INSERT INTO rtms.code_table (code, name_kr, name_en, code_type, rtms_value, housing_code, display_order) VALUES
    ('bt_01', '단독다가구', 'Single/Multi House', 'building_type', '단독다가구', 'bt_01', 1),
    ('bt_05', '아파트', 'Apartment', 'building_type', '아파트', 'bt_05', 2),
    ('bt_02', '다세대주택', 'Multi-household', 'building_type', '연립다세대', 'bt_02', 3),
    ('bt_03', '연립주택', 'Row house', 'building_type', '연립다세대', 'bt_03', 4),
    ('bt_06', '오피스텔', 'Officetel', 'building_type', '오피스텔', 'bt_06', 5);

-- 데이터 삽입: 면적구간 (5개)
INSERT INTO rtms.code_table (code, name_kr, code_type, rtms_value, min_area, max_area, display_order) VALUES
    ('R1', '60㎡ 이하', 'area_range', '~60이하', 0, 60, 1),
    ('R2', '60~85㎡', 'area_range', '60초과~85이하', 60.01, 85, 2),
    ('R3', '85~102㎡', 'area_range', '85초과~102이하', 85.01, 102, 3),
    ('R4', '102~135㎡', 'area_range', '102초과~135이하', 102.01, 135, 4),
    ('R5', '135㎡ 초과', 'area_range', '135초과~', 135.01, NULL, 5);

-- 인덱스 생성
CREATE INDEX IF NOT EXISTS idx_code_table_type ON rtms.code_table(code_type);
CREATE INDEX IF NOT EXISTS idx_code_table_rtms_value ON rtms.code_table(rtms_value) WHERE rtms_value IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_code_table_housing_code ON rtms.code_table(housing_code) WHERE housing_code IS NOT NULL;

-- 테이블 주석
COMMENT ON TABLE rtms.code_table IS 'RTMS 통합 코드 테이블: 주택유형, 면적구간 등';
COMMENT ON COLUMN rtms.code_table.code IS '코드 값 (PK)';
COMMENT ON COLUMN rtms.code_table.code_type IS '코드 타입: building_type, area_range';
COMMENT ON COLUMN rtms.code_table.rtms_value IS 'RTMS 원본값 (transactions_rent와 조인 시 사용)';
COMMENT ON COLUMN rtms.code_table.housing_code IS 'Housing 매핑 코드 (housing.notices와 조인 시 사용)';
COMMENT ON COLUMN rtms.code_table.min_area IS '최소 면적 (㎡, area_range 전용)';
COMMENT ON COLUMN rtms.code_table.max_area IS '최대 면적 (㎡, area_range 전용, NULL=무제한)';

-- ============================================================================
-- MATERIALIZED VIEW: 주택유형/지역/면적구간별 평균 환산가액
-- ============================================================================
-- 프론트엔드에서 빠른 조회를 위해 미리 집계된 통계 데이터
-- 하우징 데이터와의 조인을 위해 emd_code 기준으로 집계
CREATE MATERIALIZED VIEW IF NOT EXISTS rtms.statistics_rent AS
SELECT 
    building_type,
    emd_code,
    MIN(sigungudong) AS sigungudong,                    -- 표시용 (emd_code당 동일한 값)
    area_range,
    COUNT(*) AS transaction_count,                      -- 거래 건수 (통계 신뢰도)
    ROUND(AVG(converted_price), 2) AS avg_converted_price,  -- 평균 환산가액 (원/㎡)
    MIN(contract_year_month) AS period_start_ym,        -- 통계 시작 연월 (YYYYMM)
    MAX(contract_year_month) AS period_end_ym           -- 통계 종료 연월 (YYYYMM)
FROM 
    rtms.transactions_rent
WHERE 
    converted_price IS NOT NULL
    AND area_range IS NOT NULL
    AND emd_code IS NOT NULL                            -- 법정동 코드 필수
    AND contract_year_month >= 202301                   -- 2023년 1월 이후 데이터만
GROUP BY 
    building_type,
    emd_code,
    area_range;

-- 인덱스 생성 (조회 성능 최적화)
CREATE INDEX IF NOT EXISTS idx_stats_emd_code ON rtms.statistics_rent(emd_code);
CREATE INDEX IF NOT EXISTS idx_stats_building_type ON rtms.statistics_rent(building_type);
CREATE INDEX IF NOT EXISTS idx_stats_area_range ON rtms.statistics_rent(area_range);
CREATE INDEX IF NOT EXISTS idx_stats_composite ON rtms.statistics_rent(building_type, emd_code, area_range);

-- MATERIALIZED VIEW 갱신 함수
CREATE OR REPLACE FUNCTION rtms.refresh_statistics_rent()
RETURNS void AS $$
BEGIN
    REFRESH MATERIALIZED VIEW rtms.statistics_rent;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- VIEW 주석
-- ============================================================================
COMMENT ON MATERIALIZED VIEW rtms.statistics_rent IS '주택유형/지역/면적구간별 평균 환산가액 통계 (프론트엔드 빠른 조회용)';
COMMENT ON COLUMN rtms.statistics_rent.transaction_count IS '해당 조건의 거래 건수 (통계 신뢰도 지표)';
COMMENT ON COLUMN rtms.statistics_rent.avg_converted_price IS '평균 환산가액 (원/㎡)';
COMMENT ON COLUMN rtms.statistics_rent.period_start_ym IS '통계 시작 연월 (YYYYMM)';
COMMENT ON COLUMN rtms.statistics_rent.period_end_ym IS '통계 종료 연월 (YYYYMM)';