-- Core ERD for SHA-bot (PostgreSQL). Designed for FK stability and future extension.

-- Optional: dedicated schema
-- CREATE SCHEMA IF NOT EXISTS sha;
-- SET search_path TO sha, public;

-- 0) Enum-like domains
CREATE TYPE attachment_role AS ENUM ('photo', 'floorplan', 'notice', 'form', 'document', 'other');
CREATE TYPE unit_tenure    AS ENUM ('lease', 'jeonse', 'wolse', 'sale', 'other');  -- 전세/월세/분양 등
CREATE TYPE unit_type      AS ENUM ('one_room', 'two_room', 'share', 'apartment', 'villa', 'officetel', 'other');
CREATE TYPE listing_status AS ENUM ('open', 'closed', 'unknown');

-- 1) Platforms
CREATE TABLE IF NOT EXISTS platforms (
    id             SERIAL PRIMARY KEY,
    code           TEXT UNIQUE NOT NULL,          -- 'sohouse', 'cohouse' 등
    name           TEXT NOT NULL,
    base_url       TEXT,
    contact_email  TEXT,
    is_active      BOOLEAN DEFAULT TRUE,
    platform_extra JSONB DEFAULT '{}'::jsonb,     -- 확장 필드 (플랫폼 전용)
    created_at     TIMESTAMPTZ DEFAULT now(),
    updated_at     TIMESTAMPTZ DEFAULT now()
);

-- 2) Notices (공고)
CREATE TABLE IF NOT EXISTS notices (
    id                  BIGSERIAL PRIMARY KEY,
    platform_id         INTEGER NOT NULL REFERENCES platforms(id) ON UPDATE CASCADE,
    source              TEXT NOT NULL,                         -- 'sohouse', 'cohouse', ...
    source_key          TEXT NOT NULL,                         -- 플랫폼 내 고유키(중복방지)
    title               TEXT NOT NULL,
    detail_url          TEXT,
    list_url            TEXT,
    status              listing_status DEFAULT 'unknown',
    posted_at           TIMESTAMPTZ,      -- 공고 게시일
    last_modified       TIMESTAMPTZ,      -- 최종 공고 수정일
    apply_start_at      TIMESTAMPTZ,
    apply_end_at        TIMESTAMPTZ,
    address_raw         TEXT,                                  -- 원문 주소
    address_id          BIGINT,                                -- FK to addresses (optional, 아래 테이블)
    deposit_min         NUMERIC(14,2),
    deposit_max         NUMERIC(14,2),
    rent_min            NUMERIC(14,2),
    rent_max            NUMERIC(14,2),
    area_min_m2         NUMERIC(10,2),
    area_max_m2         NUMERIC(10,2),
    floor_min           INTEGER,
    floor_max           INTEGER,
    description_raw     TEXT,                                  -- 원문 설명
    notice_extra        JSONB DEFAULT '{}'::jsonb,             -- 플랫폼별 추가필드(가변)
    has_images          BOOLEAN DEFAULT FALSE,
    has_floorplan       BOOLEAN DEFAULT FALSE,
    has_documents       BOOLEAN DEFAULT FALSE,
    created_at          TIMESTAMPTZ DEFAULT now(),
    updated_at          TIMESTAMPTZ DEFAULT now(),
    UNIQUE (source, source_key)
);

-- Optional: address normalization table
CREATE TABLE IF NOT EXISTS addresses (
    id              BIGSERIAL PRIMARY KEY,
    address_raw     TEXT NOT NULL,
    address_norm    TEXT,
    si_do           TEXT,
    si_gun_gu       TEXT,
    road_name       TEXT,
    zipcode         TEXT,
    lat             DOUBLE PRECISION,
    lon             DOUBLE PRECISION,
    geo_extra       JSONB DEFAULT '{}'::jsonb,
    created_at      TIMESTAMPTZ DEFAULT now()
);

ALTER TABLE notices
    ADD CONSTRAINT fk_notices_address
    FOREIGN KEY (address_id) REFERENCES addresses(id);

-- 3) Units (공고 하위 세부 공급)
CREATE TABLE IF NOT EXISTS units (
    id                  BIGSERIAL PRIMARY KEY,
    notice_id           BIGINT NOT NULL REFERENCES notices(id) ON DELETE CASCADE,
    unit_code           TEXT,                                -- 공고 내 유닛 구분 코드(있다면)
    unit_type           unit_type DEFAULT 'other',
    tenure              unit_tenure DEFAULT 'other',         -- 전세/월세/등
    deposit             NUMERIC(14,2),
    rent                NUMERIC(14,2),
    maintenance_fee     NUMERIC(14,2),
    area_m2             NUMERIC(10,2),
    room_count          INTEGER,
    bathroom_count      INTEGER,
    floor               INTEGER,
    direction           TEXT,
    occupancy_available_at TIMESTAMPTZ,
    unit_extra          JSONB DEFAULT '{}'::jsonb,           -- 유닛 특화 필드(옵션,가변)
    created_at          TIMESTAMPTZ DEFAULT now(),
    updated_at          TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_units_notice ON units(notice_id);
CREATE INDEX IF NOT EXISTS idx_units_rent ON units(rent);
CREATE INDEX IF NOT EXISTS idx_units_area ON units(area_m2);

-- 4) Attachments (문서/이미지/평면도 등 메타)
CREATE TABLE IF NOT EXISTS attachments (
    id              BIGSERIAL PRIMARY KEY,
    notice_id       BIGINT NOT NULL REFERENCES notices(id) ON DELETE CASCADE,
    role            attachment_role NOT NULL,
    file_name       TEXT,                      -- 로컬 파일명(원본명)
    file_ext        TEXT,
    mime_type       TEXT,
    file_size       BIGINT,
    source_url      TEXT,                      -- 다운로드 원본 URL
    sha256          TEXT,                      -- 파일 해시(중복 방지)
    storage_path    TEXT,                      -- 저장 경로(불변 원칙: RAW는 불변)
    width_px        INTEGER,
    height_px       INTEGER,
    meta_extra      JSONB DEFAULT '{}'::jsonb,
    created_at      TIMESTAMPTZ DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS ux_attachments_notice_hash 
    ON attachments(notice_id, sha256);

-- 5) Images (이미지 전용 메타; 원한다면 attachments와 1:1 매핑)
CREATE TABLE IF NOT EXISTS images (
    id              BIGSERIAL PRIMARY KEY,
    attachment_id   BIGINT NOT NULL UNIQUE REFERENCES attachments(id) ON DELETE CASCADE,
    is_primary      BOOLEAN DEFAULT FALSE,
    caption         TEXT,
    exif            JSONB DEFAULT '{}'::jsonb,
    created_at      TIMESTAMPTZ DEFAULT now()
);

-- 6) Optional tags/features
CREATE TABLE IF NOT EXISTS notice_tags (
    id          BIGSERIAL PRIMARY KEY,
    notice_id   BIGINT NOT NULL REFERENCES notices(id) ON DELETE CASCADE,
    tag         TEXT NOT NULL,
    UNIQUE (notice_id, tag)
);

CREATE TABLE IF NOT EXISTS unit_features (
    id          BIGSERIAL PRIMARY KEY,
    unit_id     BIGINT NOT NULL REFERENCES units(id) ON DELETE CASCADE,
    feature     TEXT NOT NULL,
    value       TEXT,
    UNIQUE (unit_id, feature)
);

-- 7) Ingestion logs (idempotent upsert 추적)
CREATE TABLE IF NOT EXISTS source_ingest_logs (
    id              BIGSERIAL PRIMARY KEY,
    source          TEXT NOT NULL,     -- 'sohouse', 'cohouse'
    source_key      TEXT NOT NULL,
    run_id          TEXT,              -- 크롤러 실행 식별자(날짜+시간)
    op              TEXT NOT NULL,     -- 'INSERT'/'UPDATE'/'SKIP'
    reason          TEXT,
    created_at      TIMESTAMPTZ DEFAULT now()
);

-- 8) Search helpers
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS unaccent;

-- Full-text index on notice title + description
ALTER TABLE notices
    ADD COLUMN IF NOT EXISTS search_tsv tsvector;

CREATE INDEX IF NOT EXISTS idx_notices_tsv ON notices USING GIN (search_tsv);
CREATE INDEX IF NOT EXISTS idx_notices_dates ON notices(apply_start_at, apply_end_at);

-- Trigger to keep tsvector updated
CREATE OR REPLACE FUNCTION notices_tsv_update() RETURNS trigger AS $$
BEGIN
  NEW.search_tsv := to_tsvector('simple', coalesce(unaccent(NEW.title),'') || ' ' || coalesce(unaccent(NEW.description_raw),''));
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_notices_tsv ON notices;
CREATE TRIGGER trg_notices_tsv BEFORE INSERT OR UPDATE ON notices
FOR EACH ROW EXECUTE FUNCTION notices_tsv_update();

-- ===========================================
-- 공공 인프라 데이터 테이블들
-- ===========================================

-- 9) 공공체육시설 정보
CREATE TABLE IF NOT EXISTS public_sports_facilities (
    id              BIGSERIAL PRIMARY KEY,
    facility_name   TEXT NOT NULL,                    -- 시설명
    facility_type   TEXT,                             -- 시설유형
    address         TEXT,                             -- 주소
    lat             DOUBLE PRECISION,                 -- 위도
    lon             DOUBLE PRECISION,                 -- 경도
    phone           TEXT,                             -- 전화번호
    homepage        TEXT,                             -- 홈페이지
    operating_hours TEXT,                             -- 운영시간
    facility_extra  JSONB DEFAULT '{}'::jsonb,        -- 추가 정보
    created_at      TIMESTAMPTZ DEFAULT now(),
    updated_at      TIMESTAMPTZ DEFAULT now()
);

-- 10) 지하철역 정보
CREATE TABLE IF NOT EXISTS subway_stations (
    id              BIGSERIAL PRIMARY KEY,
    station_name    TEXT NOT NULL,                    -- 역명
    line_name       TEXT NOT NULL,                    -- 노선명
    station_code    TEXT,                             -- 역코드
    address         TEXT,                             -- 주소
    lat             DOUBLE PRECISION,                 -- 위도
    lon             DOUBLE PRECISION,                 -- 경도
    station_extra   JSONB DEFAULT '{}'::jsonb,        -- 추가 정보
    created_at      TIMESTAMPTZ DEFAULT now(),
    updated_at      TIMESTAMPTZ DEFAULT now()
);

-- 11) 버스정류소 정보
CREATE TABLE IF NOT EXISTS bus_stops (
    id              BIGSERIAL PRIMARY KEY,
    stop_name       TEXT NOT NULL,                    -- 정류소명
    stop_id         TEXT,                             -- 정류소ID
    address         TEXT,                             -- 주소
    lat             DOUBLE PRECISION,                 -- 위도
    lon             DOUBLE PRECISION,                 -- 경도
    stop_extra      JSONB DEFAULT '{}'::jsonb,        -- 추가 정보
    created_at      TIMESTAMPTZ DEFAULT now(),
    updated_at      TIMESTAMPTZ DEFAULT now()
);

-- 12) 편의점 정보
CREATE TABLE IF NOT EXISTS convenience_stores (
    id              BIGSERIAL PRIMARY KEY,
    store_name      TEXT NOT NULL,                    -- 편의점명
    brand           TEXT,                             -- 브랜드 (CU, GS25, 7-Eleven 등)
    address         TEXT,                             -- 주소
    lat             DOUBLE PRECISION,                 -- 위도
    lon             DOUBLE PRECISION,                 -- 경도
    phone           TEXT,                             -- 전화번호
    operating_hours TEXT,                             -- 운영시간
    store_extra     JSONB DEFAULT '{}'::jsonb,        -- 추가 정보
    created_at      TIMESTAMPTZ DEFAULT now(),
    updated_at      TIMESTAMPTZ DEFAULT now()
);

-- 13) 병원 정보
CREATE TABLE IF NOT EXISTS hospitals (
    id              BIGSERIAL PRIMARY KEY,
    hospital_name   TEXT NOT NULL,                    -- 병원명
    hospital_type   TEXT,                             -- 병원유형 (종합병원, 의원, 치과 등)
    address         TEXT,                             -- 주소
    lat             DOUBLE PRECISION,                 -- 위도
    lon             DOUBLE PRECISION,                 -- 경도
    phone           TEXT,                             -- 전화번호
    homepage        TEXT,                             -- 홈페이지
    operating_hours TEXT,                             -- 운영시간
    hospital_extra  JSONB DEFAULT '{}'::jsonb,        -- 추가 정보
    created_at      TIMESTAMPTZ DEFAULT now(),
    updated_at      TIMESTAMPTZ DEFAULT now()
);

-- 14) 학교 정보
CREATE TABLE IF NOT EXISTS schools (
    id              BIGSERIAL PRIMARY KEY,
    school_name     TEXT NOT NULL,                    -- 학교명
    school_type     TEXT,                             -- 학교유형 (초등학교, 중학교, 고등학교, 대학교)
    address         TEXT,                             -- 주소
    lat             DOUBLE PRECISION,                 -- 위도
    lon             DOUBLE PRECISION,                 -- 경도
    phone           TEXT,                             -- 전화번호
    homepage        TEXT,                             -- 홈페이지
    school_extra    JSONB DEFAULT '{}'::jsonb,        -- 추가 정보
    created_at      TIMESTAMPTZ DEFAULT now(),
    updated_at      TIMESTAMPTZ DEFAULT now()
);

-- 15) 공공 인프라 통합 인덱스
CREATE INDEX IF NOT EXISTS idx_public_sports_lat_lon ON public_sports_facilities(lat, lon);
CREATE INDEX IF NOT EXISTS idx_subway_lat_lon ON subway_stations(lat, lon);
CREATE INDEX IF NOT EXISTS idx_bus_stops_lat_lon ON bus_stops(lat, lon);
CREATE INDEX IF NOT EXISTS idx_convenience_lat_lon ON convenience_stores(lat, lon);
CREATE INDEX IF NOT EXISTS idx_hospitals_lat_lon ON hospitals(lat, lon);
CREATE INDEX IF NOT EXISTS idx_schools_lat_lon ON schools(lat, lon);

-- 16) 공공 인프라 데이터 수집 로그
CREATE TABLE IF NOT EXISTS public_data_ingest_logs (
    id              BIGSERIAL PRIMARY KEY,
    data_source     TEXT NOT NULL,                    -- 데이터 소스 (서울시 공공체육시설, 지하철역 등)
    file_name       TEXT NOT NULL,                    -- 원본 파일명
    record_count    INTEGER,                          -- 처리된 레코드 수
    status          TEXT NOT NULL,                    -- 'SUCCESS', 'FAILED', 'PARTIAL'
    error_message   TEXT,                             -- 에러 메시지
    ingested_at     TIMESTAMPTZ DEFAULT now()
);

-- 17) 주소 정규화를 위한 행정구역 코드 테이블
CREATE TABLE IF NOT EXISTS administrative_districts (
    id              BIGSERIAL PRIMARY KEY,
    district_code   TEXT UNIQUE NOT NULL,             -- 행정구역코드
    district_name   TEXT NOT NULL,                    -- 행정구역명
    si_do           TEXT,                             -- 시도
    si_gun_gu       TEXT,                             -- 시군구
    eup_myeon_dong  TEXT,                             -- 읍면동
    ri              TEXT,                             -- 리
    parent_code     TEXT,                             -- 상위 행정구역코드
    level           INTEGER,                          -- 행정구역 레벨 (1: 시도, 2: 시군구, 3: 읍면동, 4: 리)
    created_at      TIMESTAMPTZ DEFAULT now()
);

-- 18) 추천 시스템을 위한 사용자 및 이벤트 테이블
CREATE TABLE IF NOT EXISTS users (
    id              BIGSERIAL PRIMARY KEY,
    external_user_id TEXT UNIQUE,                     -- 앱 사용자 키(선택)
    created_at      TIMESTAMPTZ DEFAULT now()
);

-- 19) 사용자 프로필
CREATE TABLE IF NOT EXISTS user_profiles (
    user_id         BIGINT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    budget_max      NUMERIC(14,2),
    deposit_max     NUMERIC(14,2),
    area_min_m2     NUMERIC(10,2),
    preferred_unit_types TEXT[],                      -- e.g. {'studio','officetel'}
    preferred_districts TEXT[],                       -- 행정구 선호
    must_have       TEXT[],                           -- 반드시 필요한 특성(엘베, 반려동물 등)
    nice_to_have    TEXT[],                           -- 가점 특성
    commute_poi     JSONB DEFAULT '{}'::jsonb,        -- {'office': {'lat':..,'lon':..,'max_min:45}
    profile_extra   JSONB DEFAULT '{}'::jsonb,
    updated_at      TIMESTAMPTZ DEFAULT now()
);

-- 20) 사용자 이벤트
CREATE TYPE user_event_type AS ENUM ('view','click','save','contact','share','dismiss');

CREATE TABLE IF NOT EXISTS user_events (
    id              BIGSERIAL PRIMARY KEY,
    user_id         BIGINT REFERENCES users(id) ON DELETE CASCADE,
    notice_id       BIGINT REFERENCES notices(id) ON DELETE CASCADE,
    unit_id         BIGINT REFERENCES units(id) ON DELETE SET NULL,
    event_type      user_event_type NOT NULL,
    event_at        TIMESTAMPTZ DEFAULT now(),
    context         JSONB DEFAULT '{}'::jsonb         -- 세션/디바이스/쿼리 등
);

CREATE INDEX IF NOT EXISTS idx_user_events_user ON user_events(user_id, event_at DESC);
CREATE INDEX IF NOT EXISTS idx_user_events_item ON user_events(notice_id, unit_id);

-- 21) 공공 인프라와 주택의 거리 계산을 위한 함수
CREATE OR REPLACE FUNCTION calculate_distance(
    lat1 DOUBLE PRECISION, lon1 DOUBLE PRECISION,
    lat2 DOUBLE PRECISION, lon2 DOUBLE PRECISION
) RETURNS DOUBLE PRECISION AS $$
BEGIN
    RETURN 6371 * acos(
        cos(radians(lat1)) * cos(radians(lat2)) * 
        cos(radians(lon2) - radians(lon1)) + 
        sin(radians(lat1)) * sin(radians(lat2))
    );
END;
$$ LANGUAGE plpgsql;
