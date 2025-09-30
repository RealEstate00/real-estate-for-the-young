-- RTMS (Real Transaction Market System) 스키마
-- 실거래가 및 시장 분석 데이터 관리

-- Set schema context
SET search_path TO rtms, housing, infra, public;

-- 1) 실거래 데이터
CREATE TABLE IF NOT EXISTS rtms.transaction_data (
    id              BIGSERIAL PRIMARY KEY,
    transaction_id  TEXT UNIQUE NOT NULL,           -- 거래 고유 ID
    address_raw     TEXT NOT NULL,                  -- 거래 주소
    address_id      VARCHAR(255) REFERENCES housing.addresses(address_ext_id),
    building_name   TEXT,                           -- 건물명
    building_type   TEXT,                           -- 건물 유형 (아파트, 오피스텔 등)
    transaction_type TEXT NOT NULL,                 -- 거래 유형 (매매, 전세, 월세)
    price           BIGINT NOT NULL,                -- 거래 가격 (원)
    deposit         BIGINT,                         -- 보증금 (전세/월세)
    monthly_rent    BIGINT,                         -- 월세 (월세만)
    area_m2         DECIMAL(10,2),                  -- 면적 (제곱미터)
    floor           INTEGER,                        -- 층수
    total_floors    INTEGER,                        -- 총 층수
    room_count      INTEGER,                        -- 방 개수
    bathroom_count  INTEGER,                        -- 화장실 개수
    transaction_date DATE NOT NULL,                 -- 거래일
    contract_date   DATE,                           -- 계약일
    transaction_extra JSONB DEFAULT '{}'::jsonb,    -- 거래별 추가 정보
    data_source     TEXT NOT NULL,                  -- 'rtms', 'openseoul', 'manual'
    last_updated    TIMESTAMPTZ DEFAULT now(),
    created_at      TIMESTAMPTZ DEFAULT now()
);

-- 2) 가격 동향 데이터
CREATE TABLE IF NOT EXISTS rtms.price_trends (
    id              BIGSERIAL PRIMARY KEY,
    address_id      VARCHAR(255) NOT NULL REFERENCES housing.addresses(address_ext_id),
    period_type     TEXT NOT NULL,                  -- 'daily', 'weekly', 'monthly', 'yearly'
    period_start    DATE NOT NULL,                  -- 기간 시작일
    period_end      DATE NOT NULL,                  -- 기간 종료일
    avg_price       BIGINT,                         -- 평균 가격
    min_price       BIGINT,                         -- 최저 가격
    max_price       BIGINT,                         -- 최고 가격
    transaction_count INTEGER,                      -- 거래 건수
    price_change_rate DECIMAL(5,2),                 -- 가격 변동률 (%)
    trend_extra     JSONB DEFAULT '{}'::jsonb,      -- 동향별 추가 정보
    data_source     TEXT NOT NULL,
    last_updated    TIMESTAMPTZ DEFAULT now(),
    created_at      TIMESTAMPTZ DEFAULT now(),
    UNIQUE(address_id, period_type, period_start)
);

-- 3) 시장 분석 데이터
CREATE TABLE IF NOT EXISTS rtms.market_analysis (
    id              BIGSERIAL PRIMARY KEY,
    analysis_type   TEXT NOT NULL,                  -- 'district', 'building_type', 'price_range'
    analysis_target TEXT NOT NULL,                  -- 분석 대상 (구명, 건물유형 등)
    analysis_period TEXT NOT NULL,                  -- 'monthly', 'quarterly', 'yearly'
    analysis_date   DATE NOT NULL,                  -- 분석 기준일
    market_index    DECIMAL(10,2),                  -- 시장 지수
    price_forecast  BIGINT,                         -- 가격 예측
    market_trend    TEXT,                           -- 'rising', 'falling', 'stable'
    confidence_level DECIMAL(5,2),                  -- 신뢰도 (%)
    analysis_extra  JSONB DEFAULT '{}'::jsonb,      -- 분석별 추가 정보
    data_source     TEXT NOT NULL,
    last_updated    TIMESTAMPTZ DEFAULT now(),
    created_at      TIMESTAMPTZ DEFAULT now()
);

-- 4) 주택-실거래가 연결
CREATE TABLE IF NOT EXISTS rtms.housing_transaction_links (
    id              BIGSERIAL PRIMARY KEY,
    notice_id       VARCHAR(255) NOT NULL REFERENCES housing.notices(notice_id),
    transaction_id  BIGINT NOT NULL REFERENCES rtms.transaction_data(id),
    similarity_score DECIMAL(5,2),                  -- 유사도 점수 (0-100)
    link_type       TEXT NOT NULL,                  -- 'exact_match', 'similar', 'nearby'
    link_extra      JSONB DEFAULT '{}'::jsonb,
    created_at      TIMESTAMPTZ DEFAULT now(),
    UNIQUE(notice_id, transaction_id)
);

-- 인덱스 생성
CREATE INDEX IF NOT EXISTS idx_transaction_data_address ON rtms.transaction_data(address_id);
CREATE INDEX IF NOT EXISTS idx_transaction_data_type ON rtms.transaction_data(transaction_type);
CREATE INDEX IF NOT EXISTS idx_transaction_data_date ON rtms.transaction_data(transaction_date);
CREATE INDEX IF NOT EXISTS idx_transaction_data_price ON rtms.transaction_data(price);
CREATE INDEX IF NOT EXISTS idx_transaction_data_building ON rtms.transaction_data(building_type);

CREATE INDEX IF NOT EXISTS idx_price_trends_address ON rtms.price_trends(address_id);
CREATE INDEX IF NOT EXISTS idx_price_trends_period ON rtms.price_trends(period_type, period_start);
CREATE INDEX IF NOT EXISTS idx_price_trends_date ON rtms.price_trends(period_start);

CREATE INDEX IF NOT EXISTS idx_market_analysis_type ON rtms.market_analysis(analysis_type);
CREATE INDEX IF NOT EXISTS idx_market_analysis_target ON rtms.market_analysis(analysis_target);
CREATE INDEX IF NOT EXISTS idx_market_analysis_date ON rtms.market_analysis(analysis_date);

CREATE INDEX IF NOT EXISTS idx_housing_transaction_links_notice ON rtms.housing_transaction_links(notice_id);
CREATE INDEX IF NOT EXISTS idx_housing_transaction_links_transaction ON rtms.housing_transaction_links(transaction_id);

-- 거래 유형 기본 데이터 삽입
INSERT INTO rtms.transaction_data (transaction_id, address_raw, transaction_type, price, transaction_date, data_source) VALUES
('DUMMY_SALE', '더미매매', 'sale', 0, CURRENT_DATE, 'system'),
('DUMMY_JEONSE', '더미전세', 'jeonse', 0, CURRENT_DATE, 'system'),
('DUMMY_MONTHLY', '더미월세', 'monthly', 0, CURRENT_DATE, 'system')
ON CONFLICT (transaction_id) DO NOTHING;