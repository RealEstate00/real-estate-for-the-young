-- ==========================================================
-- Fixed Housing Schema (matches normalized data structure)
-- - Updated column names to match normalized JSON
-- - Fixed FK relationships
-- - Added missing columns
-- ==========================================================

-- Set schema context
SET search_path TO housing, public;

-- 0) code_master (계층적 코드 테이블)
CREATE TABLE IF NOT EXISTS housing.code_master (
    cd VARCHAR(20) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    upper_cd VARCHAR(20),
    
    -- self-reference FK (계층 구조)
    CONSTRAINT fk_code_master_parent
    FOREIGN KEY (upper_cd) REFERENCES housing.code_master (cd)
    ON DELETE RESTRICT
);

-- 1) platforms
DROP TABLE IF EXISTS housing.platforms CASCADE;
CREATE TABLE housing.platforms (
    id SERIAL PRIMARY KEY,
    code VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    url TEXT,  -- Changed from base_url to url
    platform_code VARCHAR(50) REFERENCES housing.code_master(cd),  -- FK to code_master
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- seed (safe on re-run)
INSERT INTO housing.platforms (code, name, url, is_active) VALUES
('sohouse', '서울시 사회주택', 'https://soco.seoul.go.kr/soHouse', true),
('cohouse', '서울시 공동체주택', 'https://soco.seoul.go.kr/coHouse', true),
('youth', '청년안심주택', 'https://soco.seoul.go.kr/youth', true),
('sh', 'SH공사', 'https://www.sh.co.kr', true),
('lh', 'LH공사', 'https://www.lh.or.kr', true)
ON CONFLICT (code) DO NOTHING;

-- 2) addresses
DROP TABLE IF EXISTS housing.addresses CASCADE;
CREATE TABLE housing.addresses (
    id SERIAL PRIMARY KEY,
    address_raw TEXT NOT NULL,
    ctpv_nm VARCHAR(50),  -- 시도명
    sgg_nm VARCHAR(50),   -- 시군구명
    emd_nm VARCHAR(50),   -- 읍면동명
    emd_cd VARCHAR(10) REFERENCES housing.code_master(cd),  -- 읍면동코드 FK
    building_main_no VARCHAR(20),  -- 건물본번
    building_sub_no VARCHAR(20),   -- 건물부번
    building_name  TEXT,  -- 건물명
    road_name_full TEXT,  -- 도로명주소
    jibun_name_full TEXT,  -- 지번주소
    latitude DECIMAL(10, 8),
    longitude DECIMAL(11, 8),
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- 3) notices
DROP TABLE IF EXISTS housing.notices CASCADE;
CREATE TABLE housing.notices (
    id SERIAL PRIMARY KEY,
    platform_id INTEGER NOT NULL REFERENCES housing.platforms(id),
    source_key VARCHAR(255) NOT NULL,  -- Changed from source to source_key
    title TEXT NOT NULL,
    status VARCHAR(50) DEFAULT 'open',
    address_raw TEXT,
    address_id INTEGER REFERENCES housing.addresses(id),
    building_type VARCHAR(100) REFERENCES housing.code_master(cd),  -- FK to code_master
    notice_extra JSONB,  -- Changed from description_raw to notice_extra
    has_images BOOLEAN DEFAULT false,
    has_floorplan BOOLEAN DEFAULT false,
    has_documents BOOLEAN DEFAULT false,
    list_url TEXT,
    detail_url TEXT,
    posted_at TIMESTAMPTZ,
    last_modified TIMESTAMPTZ,
    apply_start_at TIMESTAMPTZ,
    apply_end_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    
    -- Unique constraint
    UNIQUE(platform_id, source_key)
);

-- 4) units
DROP TABLE IF EXISTS housing.units CASCADE;
CREATE TABLE housing.units (
    id SERIAL PRIMARY KEY,
    notice_id INTEGER NOT NULL REFERENCES housing.notices(id),  -- FK to notices table
    unit_code VARCHAR(255),  -- Changed from space_id to unit_code
    unit_type VARCHAR(100),
    deposit INTEGER DEFAULT 0,
    rent INTEGER DEFAULT 0,
    maintenance_fee INTEGER DEFAULT 0,  -- Changed from management_fee
    area_m2 DECIMAL(8, 2),
    floor INTEGER,
    room_number VARCHAR(50),  -- Changed from room_no
    occupancy_available BOOLEAN DEFAULT false,  -- Changed from is_available
    occupancy_available_at TIMESTAMPTZ,  -- Changed from available_at
    capacity INTEGER,  -- Changed from max_occupancy
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- 5) unit_features
DROP TABLE IF EXISTS housing.unit_features CASCADE;
CREATE TABLE housing.unit_features (
    id SERIAL PRIMARY KEY,
    unit_id INTEGER NOT NULL REFERENCES housing.units(id),  -- Fixed FK reference
    room_count INTEGER,
    bathroom_count INTEGER,
    direction VARCHAR(20),
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- 6) notice_tags
DROP TABLE IF EXISTS housing.notice_tags CASCADE;
CREATE TABLE housing.notice_tags (
    id SERIAL PRIMARY KEY,
    notice_id INTEGER NOT NULL REFERENCES housing.notices(id),
    tag TEXT NOT NULL,  -- 전체 태그 내용 (예: "지하철:회기역", "자격요건:서울특별시에 거주하는...")
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    
    -- Unique constraint for (notice_id, tag) combination
    UNIQUE(notice_id, tag)
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_notices_platform_id ON housing.notices(platform_id);
CREATE INDEX IF NOT EXISTS idx_notices_address_id ON housing.notices(address_id);
CREATE INDEX IF NOT EXISTS idx_notices_status ON housing.notices(status);
CREATE INDEX IF NOT EXISTS idx_units_notice_id ON housing.units(notice_id);
CREATE INDEX IF NOT EXISTS idx_unit_features_unit_id ON housing.unit_features(unit_id);
CREATE INDEX IF NOT EXISTS idx_notice_tags_notice_id ON housing.notice_tags(notice_id);

-- Constraints
-- Note: Rent constraint removed due to data quality issues