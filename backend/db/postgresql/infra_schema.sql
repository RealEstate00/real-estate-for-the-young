-- 공공시설 및 편의시설 테이블 스키마
-- 주택과의 거리 계산 및 시설 안내를 위한 테이블들

-- Set schema context
SET search_path TO infra, housing, rtms, public;

-- 1) 인프라 코드 테이블
CREATE TABLE IF NOT EXISTS infra.infra_code (
    cd        VARCHAR(20)  PRIMARY KEY,  -- 코드 (child, pha, mart 등)
    name      VARCHAR(100) NOT NULL,     -- 코드명 (어린이집, 약국, 마트 등)
    description TEXT,                    -- 설명
    upper_cd  VARCHAR(20),               -- 상위코드 (계층 구조 필요할 때. 없으면 null)
    source    VARCHAR(255)               -- 원본 CSV 파일명
);

-- 2) addresses 법정동 코드 마스터 테이블
CREATE TABLE IF NOT EXISTS infra.addresses (
    id              VARCHAR(10) PRIMARY KEY,       -- 법정동 코드 (emd_cd)
    name            VARCHAR(100) NOT NULL,         -- 법정동명 (예: 서울특별시 강남구 역삼동)
    ctpv_nm         VARCHAR(50),                   -- 시도명
    sgg_nm          VARCHAR(50),                   -- 시군구명
    emd_nm          VARCHAR(50),                   -- 읍면동명
    created_at      TIMESTAMPTZ DEFAULT now()
);

-- 3) 시설 정보
CREATE TABLE IF NOT EXISTS infra.facility_info (
    facility_id   VARCHAR(50) PRIMARY KEY,  -- 시설 고유 ID (예: child0001, pha0001)
    cd         VARCHAR(20) NOT NULL,     -- infra.infra_code.cd 참조 (FK)
    name       VARCHAR(200) NOT NULL,    -- 시설 이름
    address_raw     TEXT,                          -- 원문 주소
    address_id      VARCHAR(10) REFERENCES infra.addresses(id), -- 법정동 코드 FK
    lat             DOUBLE PRECISION,              -- 위도
    lon             DOUBLE PRECISION,              -- 경도
    tel        VARCHAR(50),              -- 전화번호
    website         TEXT,                          -- 웹사이트
    operating_hours TEXT,                          -- 운영시간
    is_24h          BOOLEAN DEFAULT FALSE,         -- 24시간 운영 여부
    is_emergency    BOOLEAN DEFAULT FALSE,         -- 응급실 여부 (병원의 경우)
    capacity        INTEGER,                       -- 수용인원 (학교, 어린이집 등)
    grade_level     TEXT,                          -- 학년 (학교의 경우)
    facility_extra  JSONB DEFAULT '{}'::jsonb,     -- 시설별 추가 정보
    data_source     TEXT NOT NULL,                 -- 'localdata', 'openseoul', 'manual'
    last_updated    TIMESTAMPTZ DEFAULT now(),
    created_at      TIMESTAMPTZ DEFAULT now(),
    CONSTRAINT fk_infra_code FOREIGN KEY (cd) REFERENCES infra.infra_code (cd)
);

-- 4) 지하철역 정보 (교통편)
CREATE TABLE IF NOT EXISTS infra.subway_stations (
    id              BIGSERIAL PRIMARY KEY,
    station_name    TEXT NOT NULL,                 -- 역명
    line_name       TEXT NOT NULL,                 -- 노선명 (1호선, 2호선 등)
    station_code    TEXT,                          -- 역 코드
    address_raw     TEXT,                          -- 원문 주소
    address_id      VARCHAR(10) REFERENCES infra.addresses(id), -- 법정동 코드 FK
    lat             DOUBLE PRECISION,
    lon             DOUBLE PRECISION,
    exit_count      INTEGER,                       -- 출구 수
    is_transfer     BOOLEAN DEFAULT FALSE,         -- 환승역 여부
    transfer_lines  TEXT[],                        -- 환승 가능 노선들
    station_extra   JSONB DEFAULT '{}'::jsonb,
    last_updated    TIMESTAMPTZ DEFAULT now(),
    created_at      TIMESTAMPTZ DEFAULT now()
);

-- 5) 버스정류소 정보 (교통편)
CREATE TABLE IF NOT EXISTS infra.bus_stops (
    id              BIGSERIAL PRIMARY KEY,
    stop_name       TEXT NOT NULL,                 -- 정류소명
    stop_id         TEXT,                          -- 정류소 ID
    address_raw     TEXT,                          -- 원문 주소
    address_id      VARCHAR(10) REFERENCES infra.addresses(id), -- 법정동 코드 FK
    lat             DOUBLE PRECISION,
    lon             DOUBLE PRECISION,
    stop_type       TEXT,                          -- 정류소 유형 (중앙차로, 일반 등)
    node_id         TEXT,                          -- 노드 ID
    created_at      TIMESTAMPTZ DEFAULT now()
);

-- 6) 주택-시설 거리 정보 (캐시용)
CREATE TABLE IF NOT EXISTS infra.housing_facility_distances (
    id              BIGSERIAL PRIMARY KEY,
    notice_id       BIGINT NOT NULL REFERENCES housing.notices(id),
    facility_id     VARCHAR(50) NOT NULL REFERENCES infra.facility_info(facility_id),
    distance_m      INTEGER,                       -- 거리 (미터)
    walking_time_m  INTEGER,                       -- 도보 시간 (분)
    driving_time_m  INTEGER,                       -- 자동차 시간 (분)
    created_at      TIMESTAMPTZ DEFAULT now(),
    UNIQUE(notice_id, facility_id)
);

-- 인덱스 생성
CREATE INDEX IF NOT EXISTS idx_addresses_name ON infra.addresses(name);
CREATE INDEX IF NOT EXISTS idx_addresses_sgg ON infra.addresses(sgg_nm);
CREATE INDEX IF NOT EXISTS idx_addresses_emd ON infra.addresses(emd_nm);
CREATE INDEX IF NOT EXISTS idx_facility_info_cd ON infra.facility_info(cd);
CREATE INDEX IF NOT EXISTS idx_facility_info_location ON infra.facility_info(lat, lon);
CREATE INDEX IF NOT EXISTS idx_facility_info_name ON infra.facility_info(name);
CREATE INDEX IF NOT EXISTS idx_subway_stations_line ON infra.subway_stations(line_name);
CREATE INDEX IF NOT EXISTS idx_subway_stations_location ON infra.subway_stations(lat, lon);
CREATE INDEX IF NOT EXISTS idx_bus_stops_name ON infra.bus_stops(stop_name);
CREATE INDEX IF NOT EXISTS idx_bus_stops_location ON infra.bus_stops(lat, lon);
CREATE INDEX IF NOT EXISTS idx_bus_stops_type ON infra.bus_stops(stop_type);
CREATE INDEX IF NOT EXISTS idx_housing_facility_distances_notice ON infra.housing_facility_distances(notice_id);
CREATE INDEX IF NOT EXISTS idx_housing_facility_distances_facility ON infra.housing_facility_distances(facility_id);

-- 인프라 코드 기본 데이터 삽입
INSERT INTO infra.infra_code (cd, name, description, upper_cd, source) VALUES
('busstop', '버스정류소', '교통시설', null, 'seoul_busStopLocationXyInfo'),
('subway', '지하철역', '교통시설', null, 'seoul_SearchSTNBySubwayLineInfo'),

('child', '어린이집', '보육시설', null, 'seoul_ChildCareInfo'),
('chsch', '유치원', '교육시설', null, 'seoul_childSchoolInfo'),
('sch', '학교', '교육시설', null, 'seoul_neisSchoolInfo'),
('col', '대학교', '교육시설', null, 'seoul_SebcCollegeInfoFokor'),

('pha', '약국', '의료시설', null, 'seoul_TbPharmacyOperateInfo'),
('hos', '병원', '의료시설', null, 'localdata_서울시병원_내과소아과응급의학과'),

('mart', '마트', '편의시설', null, 'localdata_서울시 마트'),
('con', '편의점', '편의시설', null, 'localdata_서울시 편의점'),

('gym', '체육시설', '운동시설', null, 'localdata_서울시 공공체육시설 정보'),
('pk', '공원', '여가시설', null, 'seoul_SearchParkInfoService')
ON CONFLICT (cd) DO NOTHING;

