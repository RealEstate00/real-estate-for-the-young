-- 공공시설 및 편의시설 테이블 스키마
-- 주택과의 거리 계산 및 시설 안내를 위한 테이블들

-- Set schema context
SET search_path TO infra, housing, rtms, public;

-- 1) 공공시설 카테고리
CREATE TABLE IF NOT EXISTS infra.facility_categories (
    id          SERIAL PRIMARY KEY,
    code        TEXT UNIQUE NOT NULL,          -- 'hospital', 'school', 'park', 'mart' 등
    name        TEXT NOT NULL,                 -- '병원', '학교', '공원', '마트' 등
    description TEXT,
    icon_url    TEXT,                          -- 아이콘 URL
    created_at  TIMESTAMPTZ DEFAULT now()
);

-- 2) 공공시설 정보
CREATE TABLE IF NOT EXISTS infra.public_facilities (
    id              BIGSERIAL PRIMARY KEY,
    category_id     INTEGER NOT NULL REFERENCES infra.facility_categories(id),
    name            TEXT NOT NULL,                 -- 시설명
    address_raw     TEXT,                          -- 원문 주소
    address_id      BIGINT REFERENCES housing.addresses(id), -- 정규화된 주소 FK
    lat             DOUBLE PRECISION,              -- 위도
    lon             DOUBLE PRECISION,              -- 경도
    phone           TEXT,                          -- 전화번호
    website         TEXT,                          -- 웹사이트
    operating_hours TEXT,                          -- 운영시간
    is_24h          BOOLEAN DEFAULT FALSE,         -- 24시간 운영 여부
    is_emergency    BOOLEAN DEFAULT FALSE,         -- 응급실 여부 (병원의 경우)
    capacity        INTEGER,                       -- 수용인원 (학교, 어린이집 등)
    grade_level     TEXT,                          -- 학년 (학교의 경우)
    facility_extra  JSONB DEFAULT '{}'::jsonb,     -- 시설별 추가 정보
    data_source     TEXT NOT NULL,                 -- 'localdata', 'openseoul', 'manual'
    last_updated    TIMESTAMPTZ DEFAULT now(),
    created_at      TIMESTAMPTZ DEFAULT now()
);

-- 3) 지하철역 정보 (교통편)
CREATE TABLE IF NOT EXISTS infra.subway_stations (
    id              BIGSERIAL PRIMARY KEY,
    station_name    TEXT NOT NULL,                 -- 역명
    line_name       TEXT NOT NULL,                 -- 노선명 (1호선, 2호선 등)
    station_code    TEXT,                          -- 역 코드
    address_raw     TEXT,                          -- 원문 주소
    address_id      BIGINT REFERENCES housing.addresses(id),
    lat             DOUBLE PRECISION,
    lon             DOUBLE PRECISION,
    exit_count      INTEGER,                       -- 출구 수
    is_transfer     BOOLEAN DEFAULT FALSE,         -- 환승역 여부
    transfer_lines  TEXT[],                        -- 환승 가능 노선들
    station_extra   JSONB DEFAULT '{}'::jsonb,
    last_updated    TIMESTAMPTZ DEFAULT now(),
    created_at      TIMESTAMPTZ DEFAULT now()
);

-- 4) 주택-시설 거리 정보 (캐시용)
CREATE TABLE IF NOT EXISTS infra.housing_facility_distances (
    id              BIGSERIAL PRIMARY KEY,
    notice_id       BIGINT NOT NULL REFERENCES housing.notices(id),
    facility_id     BIGINT NOT NULL REFERENCES infra.public_facilities(id),
    distance_m      INTEGER,                       -- 거리 (미터)
    walking_time_m  INTEGER,                       -- 도보 시간 (분)
    driving_time_m  INTEGER,                       -- 자동차 시간 (분)
    created_at      TIMESTAMPTZ DEFAULT now(),
    UNIQUE(notice_id, facility_id)
);

-- 인덱스 생성
CREATE INDEX IF NOT EXISTS idx_public_facilities_category ON infra.public_facilities(category_id);
CREATE INDEX IF NOT EXISTS idx_public_facilities_location ON infra.public_facilities(lat, lon);
CREATE INDEX IF NOT EXISTS idx_public_facilities_name ON infra.public_facilities(name);
CREATE INDEX IF NOT EXISTS idx_subway_stations_line ON infra.subway_stations(line_name);
CREATE INDEX IF NOT EXISTS idx_subway_stations_location ON infra.subway_stations(lat, lon);
CREATE INDEX IF NOT EXISTS idx_housing_facility_distances_notice ON infra.housing_facility_distances(notice_id);
CREATE INDEX IF NOT EXISTS idx_housing_facility_distances_facility ON infra.housing_facility_distances(facility_id);

-- 시설 카테고리 기본 데이터 삽입
INSERT INTO infra.facility_categories (code, name, description) VALUES
('hospital', '병원', '의료시설'),
('school', '학교', '교육시설'),
('kindergarten', '어린이집', '보육시설'),
('park', '공원', '휴양시설'),
('mart', '마트', '쇼핑시설'),
('convenience', '편의점', '편의시설'),
('pharmacy', '약국', '의료보조시설'),
('subway', '지하철역', '교통시설'),
('bus', '버스정류소', '교통시설'),
('gym', '체육시설', '운동시설')
ON CONFLICT (code) DO NOTHING;

