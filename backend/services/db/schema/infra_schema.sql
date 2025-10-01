-- ========================================
-- 인프라 DB 스키마 정의 (교통 통합 버전)
-- ========================================

-- 스키마 설정
SET search_path TO infra, housing, rtms, public;

-- 1) 인프라 코드 테이블
CREATE TABLE IF NOT EXISTS infra.infra_code (
    cd          VARCHAR(20) PRIMARY KEY,     -- 코드 (child, pha, mart, transport 등)
    name        VARCHAR(100) NOT NULL,       -- 코드명
    description TEXT,                         -- 설명
    upper_cd    VARCHAR(20),                 -- 상위 코드 (없으면 NULL)
    source      VARCHAR(255)                 -- 원본 CSV 파일명
);

-- 2) 주소 마스터 (법정동 코드)
CREATE TABLE IF NOT EXISTS infra.addresses (
    id          VARCHAR(10) PRIMARY KEY,     -- 법정동 코드 (emd_cd)
    name        VARCHAR(100) NOT NULL,       -- 전체 행정동명
    ctpv_nm     VARCHAR(50),                 -- 시도명
    sgg_nm      VARCHAR(50),                 -- 시군구명
    emd_nm      VARCHAR(50),                 -- 읍면동명
    created_at  TIMESTAMPTZ DEFAULT now()
);

-- 3) 시설 정보
CREATE TABLE IF NOT EXISTS infra.facility_info (
    facility_id     VARCHAR(50) PRIMARY KEY,         -- 시설 고유 ID (예: child0001, pha0001)
    cd              VARCHAR(20) NOT NULL,            -- infra.infra_code.cd 참조 (FK)
    name            VARCHAR(200) NOT NULL,           -- 시설 이름
    address_raw     TEXT,                            -- 원문 주소
    address_id      VARCHAR(10) REFERENCES infra.addresses(id), -- 법정동 코드 FK
    lat             DOUBLE PRECISION,                -- 위도
    lon             DOUBLE PRECISION,                -- 경도
    tel             VARCHAR(50),
    website         TEXT,
    operating_hours TEXT,
    is_24h          BOOLEAN DEFAULT FALSE,
    is_emergency    BOOLEAN DEFAULT FALSE,
    capacity        INTEGER,                         -- 수용 인원 (학교/어린이집 등)
    grade_level     TEXT,                            -- 학년 (학교의 경우)
    facility_extra  JSONB DEFAULT '{}'::jsonb,       -- 시설별 추가 정보
    data_source     TEXT NOT NULL,                   -- 수집 출처
    last_updated    TIMESTAMPTZ DEFAULT now(),
    created_at      TIMESTAMPTZ DEFAULT now(),
    CONSTRAINT fk_infra_code FOREIGN KEY (cd) REFERENCES infra.infra_code (cd)
);

-- 4) 교통 정보 (지하철 + 버스 통합)
CREATE TABLE IF NOT EXISTS infra.transport_points (
    id              VARCHAR(10) PRIMARY KEY,        -- sub001, bus001, ...
    transport_type  TEXT NOT NULL,                   -- 'subway' or 'bus'
    name            TEXT NOT NULL,                   -- 역명 / 정류소명
    official_code    TEXT,                            -- 역 코드 / 정류소 ID
    line_name       TEXT,                            -- 지하철 노선명 (지하철 전용)
    stop_type       TEXT,                            -- 정류소 유형 (버스 전용: 중앙차로, 일반 등)
    is_transfer     BOOLEAN DEFAULT false,           -- 환승역 여부 (지하철 전용)
    lat             DOUBLE PRECISION NOT NULL,
    lon             DOUBLE PRECISION NOT NULL,
    extra_info      JSONB DEFAULT '{}'::jsonb,
    created_at      TIMESTAMPTZ DEFAULT now()
);

-- 5) 주택-시설 거리 캐시
CREATE TABLE IF NOT EXISTS infra.housing_facility_distances (
    id              BIGSERIAL PRIMARY KEY,
    notice_id       VARCHAR(255) NOT NULL REFERENCES housing.notices(notice_id),
    facility_id     VARCHAR(50) NOT NULL REFERENCES infra.facility_info(facility_id),
    distance_m      INTEGER,
    walking_time_m  INTEGER,
    driving_time_m  INTEGER,
    created_at      TIMESTAMPTZ DEFAULT now(),
    UNIQUE(notice_id, facility_id)
);

-- ========================================
-- 인덱스 설정
-- ========================================

-- 주소
CREATE INDEX IF NOT EXISTS idx_addresses_name ON infra.addresses(name);
CREATE INDEX IF NOT EXISTS idx_addresses_sgg ON infra.addresses(sgg_nm);
CREATE INDEX IF NOT EXISTS idx_addresses_emd ON infra.addresses(emd_nm);

-- 시설
CREATE INDEX IF NOT EXISTS idx_facility_info_cd ON infra.facility_info(cd);
CREATE INDEX IF NOT EXISTS idx_facility_info_name ON infra.facility_info(name);
CREATE INDEX IF NOT EXISTS idx_facility_info_lat ON infra.facility_info(lat);
CREATE INDEX IF NOT EXISTS idx_facility_info_lon ON infra.facility_info(lon);

-- 교통 (통합)
CREATE INDEX IF NOT EXISTS idx_transport_points_type ON infra.transport_points(transport_type);
CREATE INDEX IF NOT EXISTS idx_transport_points_name ON infra.transport_points(name);
CREATE INDEX IF NOT EXISTS idx_transport_points_lat ON infra.transport_points(lat);
CREATE INDEX IF NOT EXISTS idx_transport_points_lon ON infra.transport_points(lon);

-- 거리 캐시
CREATE INDEX IF NOT EXISTS idx_housing_facility_distances_notice ON infra.housing_facility_distances(notice_id);
CREATE INDEX IF NOT EXISTS idx_housing_facility_distances_facility ON infra.housing_facility_distances(facility_id);

-- 교통 시설 인덱스
CREATE INDEX IF NOT EXISTS idx_transport_points_type ON infra.transport_points(transport_type);
CREATE INDEX IF NOT EXISTS idx_transport_points_transfer ON infra.transport_points(is_transfer);

-- ========================================
-- 기본 코드 데이터 삽입
-- ========================================
INSERT INTO infra.infra_code (cd, name, description, upper_cd, source) VALUES
('transport', '교통시설', '지하철/버스 통합', null, 'seoul_transport_points'),
('sub01', '지하철', '지하철 세부 역', 'transport', 'seoul_transport_points'),
('bus01', '버스', '버스 세부 정류소', 'transport', 'seoul_transport_points'),
('child', '어린이집', '보육시설', null, 'seoul_ChildCareInfo'),
('chsch', '유치원', '교육시설', null, 'seoul_childSchoolInfo'),
('sch', '학교', '교육시설', null, 'seoul_neisSchoolInfo'),
('col', '대학교', '교육시설', null, 'seoul_SebcCollegeInfoFokor'),
('pha', '약국', '의료시설', null, 'seoul_TbPharmacyOperateInfo'),
('hos', '병원', '의료시설', null, 'localdata_서울시병원_내과소아과응급의학과'),
('mt', '마트', '편의시설', null, 'localdata_서울시 마트'),
('con', '편의점', '편의시설', null, 'localdata_서울시 편의점'),
('gym', '체육시설', '운동시설', null, 'localdata_서울시 공공체육시설 정보'),
('park', '공원', '여가시설', null, 'seoul_SearchParkInfoService')
ON CONFLICT (cd) DO NOTHING;
