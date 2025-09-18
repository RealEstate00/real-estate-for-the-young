-- 정규화된 주택 데이터 스키마
-- 크롤링된 raw 데이터를 정규화된 다중 테이블 구조로 변환

-- 1. 플랫폼 테이블
CREATE TABLE IF NOT EXISTS platforms (
    id SERIAL PRIMARY KEY,
    code VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    base_url TEXT,
    contact_email VARCHAR(255),
    is_active BOOLEAN DEFAULT true,
    platform_extra JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 2. 주소 테이블
CREATE TABLE IF NOT EXISTS addresses (
    id SERIAL PRIMARY KEY,
    address_raw TEXT NOT NULL,
    address_norm TEXT,
    si_do VARCHAR(50),
    si_gun_gu VARCHAR(50),
    road_name VARCHAR(100),
    zipcode VARCHAR(10),
    lat DECIMAL(10, 8),
    lon DECIMAL(11, 8),
    geo_extra JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 3. 공고 테이블 (notices)
CREATE TABLE IF NOT EXISTS notices (
    id SERIAL PRIMARY KEY,
    platform_id INTEGER REFERENCES platforms(id),
    source VARCHAR(50) NOT NULL,
    source_key VARCHAR(255) NOT NULL,
    title TEXT NOT NULL,
    detail_url TEXT,
    list_url TEXT,
    status VARCHAR(20) DEFAULT 'open',
    posted_at TIMESTAMP WITH TIME ZONE,
    last_modified TIMESTAMP WITH TIME ZONE,
    apply_start_at TIMESTAMP WITH TIME ZONE,
    apply_end_at TIMESTAMP WITH TIME ZONE,
    address_raw TEXT,
    address_id INTEGER REFERENCES addresses(id),
    deposit_min INTEGER,
    deposit_max INTEGER,
    rent_min INTEGER,
    rent_max INTEGER,
    area_min_m2 DECIMAL(8, 2),
    area_max_m2 DECIMAL(8, 2),
    floor_min INTEGER,
    floor_max INTEGER,
    description_raw TEXT,
    notice_extra JSONB,
    has_images BOOLEAN DEFAULT false,
    has_floorplan BOOLEAN DEFAULT false,
    has_documents BOOLEAN DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    search_tsv TSVECTOR
);

-- 4. 유닛 테이블 (units)
CREATE TABLE IF NOT EXISTS units (
    id SERIAL PRIMARY KEY,
    notice_id INTEGER REFERENCES notices(id),
    unit_code VARCHAR(100),
    unit_type VARCHAR(50),
    tenure VARCHAR(20),
    deposit INTEGER,
    rent INTEGER,
    maintenance_fee INTEGER,
    area_m2 DECIMAL(8, 2),
    room_count INTEGER,
    bathroom_count INTEGER,
    floor INTEGER,
    direction VARCHAR(20),
    occupancy_available_at TIMESTAMP WITH TIME ZONE,
    unit_extra JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 5. 유닛 특징 테이블 (unit_features)
CREATE TABLE IF NOT EXISTS unit_features (
    id SERIAL PRIMARY KEY,
    unit_id INTEGER REFERENCES units(id),
    feature VARCHAR(100) NOT NULL,
    value TEXT
);

-- 6. 공고 태그 테이블 (notice_tags)
CREATE TABLE IF NOT EXISTS notice_tags (
    id SERIAL PRIMARY KEY,
    notice_id INTEGER REFERENCES notices(id),
    tag VARCHAR(100) NOT NULL
);

-- 7. 사용자 이벤트 테이블 (user_events)
CREATE TABLE IF NOT EXISTS user_events (
    id SERIAL PRIMARY KEY,
    user_id INTEGER,
    notice_id INTEGER REFERENCES notices(id),
    unit_id INTEGER REFERENCES units(id),
    event_type VARCHAR(50) NOT NULL,
    event_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    context JSONB
);

-- 인덱스 생성
CREATE INDEX IF NOT EXISTS idx_notices_platform_id ON notices(platform_id);
CREATE INDEX IF NOT EXISTS idx_notices_address_id ON notices(address_id);
CREATE INDEX IF NOT EXISTS idx_notices_source_key ON notices(source, source_key);
CREATE INDEX IF NOT EXISTS idx_notices_posted_at ON notices(posted_at);
CREATE INDEX IF NOT EXISTS idx_notices_search_tsv ON notices USING GIN(search_tsv);

CREATE INDEX IF NOT EXISTS idx_units_notice_id ON units(notice_id);
CREATE INDEX IF NOT EXISTS idx_units_unit_type ON units(unit_type);

CREATE INDEX IF NOT EXISTS idx_unit_features_unit_id ON unit_features(unit_id);
CREATE INDEX IF NOT EXISTS idx_notice_tags_notice_id ON notice_tags(notice_id);

CREATE INDEX IF NOT EXISTS idx_user_events_user_id ON user_events(user_id);
CREATE INDEX IF NOT EXISTS idx_user_events_notice_id ON user_events(notice_id);
CREATE INDEX IF NOT EXISTS idx_user_events_unit_id ON user_events(unit_id);
CREATE INDEX IF NOT EXISTS idx_user_events_event_at ON user_events(event_at);

-- 플랫폼 데이터 삽입
INSERT INTO platforms (code, name, base_url, is_active) VALUES
('sohouse', '서울시 사회주택', 'https://soco.seoul.go.kr', true),
('cohouse', '서울시 공동체주택', 'https://soco.seoul.go.kr', true),
('youth', '청년안심주택', 'https://youth.seoul.go.kr', true),
('sh', 'SH공사', 'https://www.sh.co.kr', true),
('lh', 'LH공사', 'https://www.lh.or.kr', true)
ON CONFLICT (code) DO NOTHING;
