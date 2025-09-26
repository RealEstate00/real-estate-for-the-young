-- ==========================================================
-- Normalized Housing Schema (clean, idempotent)
-- - strong FKs/uniques
-- - address normalization friendly (road/jibun + lat/lon)
-- - ready for chat search (tsvector trigger)
-- ==========================================================

-- Set schema context
SET search_path TO housing, public;

-- 1) platforms
CREATE TABLE IF NOT EXISTS housing.platforms (
    id SERIAL PRIMARY KEY,
    code VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    base_url TEXT,
    contact_email VARCHAR(255),
    is_active BOOLEAN DEFAULT true,
    platform_extra JSONB,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- seed (safe on re-run)
INSERT INTO housing.platforms (code, name, base_url, is_active) VALUES
('sohouse', '서울시 사회주택', 'https://soco.seoul.go.kr', true),
('cohouse', '서울시 공동체주택', 'https://soco.seoul.go.kr', true),
('youth', '청년안심주택', 'https://youth.seoul.go.kr', true),
('sh',     'SH공사',       'https://www.sh.co.kr',      true),
('lh',     'LH공사',       'https://www.lh.or.kr',      true)
ON CONFLICT (code) DO NOTHING;

-- 2) addresses
CREATE TABLE IF NOT EXISTS housing.addresses (
    id SERIAL PRIMARY KEY,
    address_raw  TEXT NOT NULL,              -- 원문(지번/자유형)
    ctpv_nm VARCHAR(50),                     -- 시도명
    sgg_nm VARCHAR(50),                      -- 시군구명
    emd_cd VARCHAR(10),                      -- 읍면동코드
    emd_nm VARCHAR(50),                      -- 읍면동명
    road_name_full TEXT,                     -- 도로명주소 전체
    jibun_name_full TEXT,                    -- 지번주소 전체
    main_jibun VARCHAR(20),                  -- 주지번
    sub_jibun VARCHAR(20),                   -- 부지번
    building_name VARCHAR(200),              -- 건물명
    building_main_no VARCHAR(20),            -- 건물주번호
    building_sub_no VARCHAR(20),             -- 건물부번호
    lat DECIMAL(10, 8),                      -- latitude
    lon DECIMAL(11, 8),                      -- longitude
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- dedup/geo indexes
CREATE UNIQUE INDEX IF NOT EXISTS uq_addresses_location
  ON housing.addresses(emd_cd, road_name_full, building_main_no) 
  WHERE emd_cd IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS uq_addresses_raw
  ON housing.addresses(address_raw)
  WHERE address_raw IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_addresses_lat_lon ON housing.addresses(lat, lon);

-- 3) notices
CREATE TABLE IF NOT EXISTS housing.notices (
    id SERIAL PRIMARY KEY,
    platform_id INTEGER REFERENCES housing.platforms(id),
    source VARCHAR(50) NOT NULL,             -- platform code copy or origin label
    source_key VARCHAR(255) NOT NULL,        -- unique per platform/source
    title TEXT NOT NULL,
    detail_url TEXT,
    list_url   TEXT,
    status VARCHAR(20) DEFAULT 'open',
    posted_at      TIMESTAMPTZ,
    last_modified  TIMESTAMPTZ,
    apply_start_at TIMESTAMPTZ,
    apply_end_at   TIMESTAMPTZ,
    address_raw TEXT,
    address_id  INTEGER REFERENCES housing.addresses(id),
    -- rollups for fast filtering
    deposit_min INTEGER,
    deposit_max INTEGER,
    rent_min INTEGER,
    rent_max INTEGER,
    area_min_m2  DECIMAL(8,2),
    area_max_m2  DECIMAL(8,2),
    floor_min INTEGER,
    floor_max INTEGER,
    description_raw TEXT,
    notice_extra JSONB,
    has_images    BOOLEAN DEFAULT false,
    has_floorplan BOOLEAN DEFAULT false,
    has_documents BOOLEAN DEFAULT false,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    search_tsv TSVECTOR
);

-- uniqueness & FKs
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname='uq_notice_platform_source'
  ) THEN
    ALTER TABLE housing.notices
      ADD CONSTRAINT uq_notice_platform_source UNIQUE (source, source_key);
  END IF;
END$$;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname='fk_notices_platform'
  ) THEN
    ALTER TABLE housing.notices
      ADD CONSTRAINT fk_notices_platform
      FOREIGN KEY (platform_id) REFERENCES housing.platforms(id) ON UPDATE CASCADE;
  END IF;
END$$;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname='fk_notices_address'
  ) THEN
    ALTER TABLE housing.notices
      ADD CONSTRAINT fk_notices_address
      FOREIGN KEY (address_id) REFERENCES housing.addresses(id)
      ON UPDATE CASCADE ON DELETE SET NULL;
  END IF;
END$$;

CREATE INDEX IF NOT EXISTS idx_notices_platform_id ON housing.notices(platform_id);
CREATE INDEX IF NOT EXISTS idx_notices_address_id  ON housing.notices(address_id);
CREATE INDEX IF NOT EXISTS idx_notices_posted_at   ON housing.notices(posted_at);
CREATE INDEX IF NOT EXISTS idx_notices_deposit     ON housing.notices (deposit_min, deposit_max);
CREATE INDEX IF NOT EXISTS idx_notices_rent        ON housing.notices (rent_min, rent_max);
CREATE INDEX IF NOT EXISTS idx_notices_area        ON housing.notices (area_min_m2, area_max_m2);

-- 4) units
CREATE TABLE IF NOT EXISTS housing.units (
    id SERIAL PRIMARY KEY,
    notice_id INTEGER REFERENCES housing.notices(id),
    unit_code VARCHAR(100),
    unit_type VARCHAR(50),                    -- 자유 문자열(초기 민첩성); 추후 FK로 승격 가능
    tenure VARCHAR(20),
    deposit INTEGER,
    rent INTEGER,
    maintenance_fee INTEGER,
    area_m2 DECIMAL(8,2),
    room_count INTEGER,
    bathroom_count INTEGER,
    floor INTEGER,
    direction VARCHAR(20),
    occupancy_available_at TIMESTAMPTZ,
    unit_extra JSONB,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname='fk_units_notice'
  ) THEN
    ALTER TABLE housing.units
      ADD CONSTRAINT fk_units_notice
      FOREIGN KEY (notice_id) REFERENCES housing.notices(id) ON DELETE CASCADE;
  END IF;
END$$;

-- monthly sanity (0 = 전세 허용, 그 외는 10만원 이상)
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname='ck_units_rent_reasonable'
  ) THEN
    ALTER TABLE housing.units
      ADD CONSTRAINT ck_units_rent_reasonable
      CHECK (rent IS NULL OR rent = 0 OR rent >= 100000);
  END IF;
END$$;

CREATE INDEX IF NOT EXISTS idx_units_notice_id ON housing.units(notice_id);
CREATE INDEX IF NOT EXISTS idx_units_unit_type ON housing.units(unit_type);

-- 5) unit_features (structured, no free-text tags here)
CREATE TABLE IF NOT EXISTS housing.unit_features (
    id SERIAL PRIMARY KEY,
    unit_id INTEGER REFERENCES housing.units(id) ON DELETE CASCADE,
    feature VARCHAR(100) NOT NULL,
    value   TEXT
);

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname='uq_unit_features'
  ) THEN
    ALTER TABLE housing.unit_features
      ADD CONSTRAINT uq_unit_features UNIQUE (unit_id, feature, value);
  END IF;
END$$;

CREATE INDEX IF NOT EXISTS idx_unit_features_unit_id ON housing.unit_features(unit_id);

-- 6) notice_tags (legacy tags kept but deduped)
CREATE TABLE IF NOT EXISTS housing.notice_tags (
    id SERIAL PRIMARY KEY,
    notice_id INTEGER REFERENCES housing.notices(id) ON DELETE CASCADE,
    tag VARCHAR(100) NOT NULL
);

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint WHERE conname='uq_notice_tags'
  ) THEN
    ALTER TABLE housing.notice_tags
      ADD CONSTRAINT uq_notice_tags UNIQUE (notice_id, tag);
  END IF;
END$$;

CREATE INDEX IF NOT EXISTS idx_notice_tags_notice_id ON housing.notice_tags(notice_id);

-- 7) user_events (optional analytics)
CREATE TABLE IF NOT EXISTS housing.user_events (
    id SERIAL PRIMARY KEY,
    user_id INTEGER,
    notice_id INTEGER REFERENCES housing.notices(id) ON DELETE CASCADE,
    unit_id   INTEGER REFERENCES housing.units(id)   ON DELETE CASCADE,
    event_type VARCHAR(50) NOT NULL,
    event_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    context JSONB
);

CREATE INDEX IF NOT EXISTS idx_user_events_user_id  ON housing.user_events(user_id);
CREATE INDEX IF NOT EXISTS idx_user_events_notice_id ON housing.user_events(notice_id);
CREATE INDEX IF NOT EXISTS idx_user_events_unit_id   ON housing.user_events(unit_id);
CREATE INDEX IF NOT EXISTS idx_user_events_event_at  ON housing.user_events(event_at);

-- 8) full-text search support (simple dict; replace with Korean dict if installed)
CREATE OR REPLACE FUNCTION notices_tsvector_update() RETURNS trigger AS $$
BEGIN
  NEW.search_tsv := to_tsvector('simple',
                      coalesce(NEW.title,'') || ' ' ||
                      coalesce(NEW.description_raw,''));
  RETURN NEW;
END $$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_notices_tsvector ON housing.notices;
CREATE TRIGGER trg_notices_tsvector
BEFORE INSERT OR UPDATE OF title, description_raw ON housing.notices
FOR EACH ROW EXECUTE FUNCTION notices_tsvector_update();

CREATE INDEX IF NOT EXISTS idx_notices_search_tsv ON housing.notices USING GIN(search_tsv);
