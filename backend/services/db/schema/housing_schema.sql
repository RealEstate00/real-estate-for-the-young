-- =====================================================================
-- Housing Schema (Natural-key First, dependency-safe)
-- =====================================================================
CREATE SCHEMA IF NOT EXISTS housing;
SET search_path TO housing, public;

-- 0) DROP views if any
DROP VIEW IF EXISTS housing.v_building_type_stats CASCADE;
DROP VIEW IF EXISTS housing.v_address_stats CASCADE;
DROP VIEW IF EXISTS housing.v_platform_stats CASCADE;
DROP VIEW IF EXISTS housing.v_notices_with_stats CASCADE;
DROP VIEW IF EXISTS housing.v_units_with_calculations CASCADE;

-- 1) MASTER / LOOKUP
DROP TABLE IF EXISTS housing.code_master CASCADE;
CREATE TABLE housing.code_master (
    cd          VARCHAR(50) PRIMARY KEY,
    name        VARCHAR(100) NOT NULL,
    description TEXT,
    upper_cd    VARCHAR(50),
    CONSTRAINT fk_code_master_parent
      FOREIGN KEY (upper_cd) REFERENCES housing.code_master(cd)
      ON DELETE RESTRICT
);

-- 2) PLATFORMS
DROP TABLE IF EXISTS housing.platforms CASCADE;
CREATE TABLE housing.platforms (
    code           VARCHAR(50) PRIMARY KEY,
    name           VARCHAR(100) NOT NULL,
    url            TEXT,
    platform_code  VARCHAR(50) REFERENCES housing.code_master(cd),
    is_active      BOOLEAN DEFAULT TRUE,
    created_at     TIMESTAMPTZ DEFAULT now(),
    updated_at     TIMESTAMPTZ DEFAULT now(),
    CONSTRAINT ck_platforms_code_format CHECK (code ~ '^[a-z_]+$')
);

-- 3) ADDRESSES  (SERIAL PK + 외부 안정키 UNIQUE)
DROP TABLE IF EXISTS housing.addresses CASCADE;
CREATE TABLE housing.addresses (
    id               SERIAL PRIMARY KEY,
    address_ext_id   VARCHAR(255) NOT NULL UNIQUE,
    address_raw      TEXT NOT NULL,
    ctpv_nm          VARCHAR(50),
    sgg_nm           VARCHAR(50),
    emd_nm           VARCHAR(50),
    emd_cd           VARCHAR(20) REFERENCES housing.code_master(cd),
    building_main_no VARCHAR(20),
    building_sub_no  VARCHAR(20),
    building_name    TEXT,
    road_name_full   TEXT,
    jibun_name_full  TEXT,
    latitude         DECIMAL(10, 8),
    longitude        DECIMAL(11, 8),
    created_at       TIMESTAMPTZ DEFAULT now(),
    updated_at       TIMESTAMPTZ DEFAULT now(),
    CONSTRAINT ck_addresses_latitude  CHECK (latitude  IS NULL OR (latitude  BETWEEN -90  AND 90)),
    CONSTRAINT ck_addresses_longitude CHECK (longitude IS NULL OR (longitude BETWEEN -180 AND 180))
);
CREATE INDEX IF NOT EXISTS idx_addresses_ext ON housing.addresses(address_ext_id);

-- 4) NOTICES
DROP TABLE IF EXISTS housing.notices CASCADE;
CREATE TABLE housing.notices (
    notice_id       VARCHAR(255) PRIMARY KEY,
    platform_code   VARCHAR(50) NOT NULL REFERENCES housing.platforms(code),
    title           TEXT NOT NULL,
    status          VARCHAR(50) DEFAULT 'open',
    address_raw     TEXT,
    address_id      INTEGER REFERENCES housing.addresses(id) ON DELETE SET NULL,
    building_type   VARCHAR(50) REFERENCES housing.code_master(cd),
    notice_extra    JSONB DEFAULT '{}'::jsonb,
    has_images      BOOLEAN DEFAULT FALSE,
    has_floorplan   BOOLEAN DEFAULT FALSE,
    has_documents   BOOLEAN DEFAULT FALSE,
    list_url        TEXT,
    detail_url      TEXT,
    posted_at       TIMESTAMPTZ,
    last_modified   TIMESTAMPTZ,
    apply_start_at  TIMESTAMPTZ,
    apply_end_at    TIMESTAMPTZ,
    created_at      TIMESTAMPTZ DEFAULT now(),
    updated_at      TIMESTAMPTZ DEFAULT now(),
    CONSTRAINT ck_notices_status CHECK (status IN ('open','closed','suspended','draft')),
    CONSTRAINT ck_notices_dates  CHECK (apply_start_at IS NULL OR apply_end_at IS NULL OR apply_start_at <= apply_end_at)
);
CREATE INDEX IF NOT EXISTS idx_notices_platform      ON housing.notices(platform_code);
CREATE INDEX IF NOT EXISTS idx_notices_building_type ON housing.notices(building_type);

-- 5) UNITS
DROP TABLE IF EXISTS housing.units CASCADE;
CREATE TABLE housing.units (
    unit_id             VARCHAR(255) PRIMARY KEY,
    notice_id           VARCHAR(255) NOT NULL REFERENCES housing.notices(notice_id) ON DELETE CASCADE,
    unit_type           VARCHAR(50),
    deposit             NUMERIC,
    rent                NUMERIC,
    maintenance_fee     NUMERIC,
    area_m2             NUMERIC,
    floor               VARCHAR(20),
    room_number         VARCHAR(50),
    occupancy_available BOOLEAN,
    occupancy_available_at TIMESTAMPTZ,
    capacity            INTEGER,
    created_at          TIMESTAMPTZ DEFAULT now(),
    updated_at          TIMESTAMPTZ DEFAULT now()
);

-- 6) UNIT FEATURES (1:1 units)
DROP TABLE IF EXISTS housing.unit_features CASCADE;
CREATE TABLE housing.unit_features (
    id              SERIAL PRIMARY KEY,
    unit_id         VARCHAR(255) NOT NULL REFERENCES housing.units(unit_id) ON DELETE CASCADE,
    room_count      INTEGER,
    bathroom_count  INTEGER,
    direction       VARCHAR(20),
    created_at      TIMESTAMPTZ DEFAULT now(),
    updated_at      TIMESTAMPTZ DEFAULT now(),
    CONSTRAINT uk_unit_features_unit_id UNIQUE (unit_id),
    CONSTRAINT ck_unit_features_room_count     CHECK (room_count     IS NULL OR room_count     BETWEEN 0 AND 10),
    CONSTRAINT ck_unit_features_bathroom_count CHECK (bathroom_count IS NULL OR bathroom_count BETWEEN 0 AND 5)
);

-- 7) NOTICE TAGS
DROP TABLE IF EXISTS housing.notice_tags CASCADE;
CREATE TABLE housing.notice_tags (
    id          SERIAL PRIMARY KEY,
    notice_id   VARCHAR(255) NOT NULL REFERENCES housing.notices(notice_id) ON DELETE CASCADE,
    tag_type    VARCHAR(50) NOT NULL REFERENCES housing.code_master(cd) ON DELETE RESTRICT,
    tag_value   TEXT NOT NULL,
    created_at  TIMESTAMPTZ DEFAULT now(),
    updated_at  TIMESTAMPTZ DEFAULT now(),
    UNIQUE (notice_id, tag_type, tag_value)
);
CREATE INDEX IF NOT EXISTS idx_notice_tags_notice ON housing.notice_tags(notice_id);
CREATE INDEX IF NOT EXISTS idx_notice_tags_type ON housing.notice_tags(tag_type);
