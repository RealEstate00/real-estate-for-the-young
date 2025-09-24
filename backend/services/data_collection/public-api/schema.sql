-- 서울 열린데이터광장 API 데이터를 위한 DB 스키마
-- infra 스키마에 테이블들을 생성

-- 어린이집 테이블
CREATE TABLE IF NOT EXISTS infra.childcare (
    id SERIAL PRIMARY KEY,
    source VARCHAR(50) NOT NULL,
    source_key VARCHAR(100) NOT NULL,
    name VARCHAR(200) NOT NULL,
    type VARCHAR(50),
    status VARCHAR(50),
    address_raw TEXT,
    address_norm TEXT,
    zipcode VARCHAR(10),
    phone VARCHAR(20),
    fax VARCHAR(20),
    homepage VARCHAR(200),
    room_count INTEGER,
    room_size DECIMAL(10,2),
    capacity INTEGER,
    child_count INTEGER,
    lat DECIMAL(10,8),
    lon DECIMAL(11,8),
    si_do VARCHAR(50),
    si_gun_gu VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(source, source_key)
);

-- 학교 테이블 (어린이학교, NEIS학교, 대학 통합)
CREATE TABLE IF NOT EXISTS infra.schools (
    id SERIAL PRIMARY KEY,
    source VARCHAR(50) NOT NULL,
    source_key VARCHAR(100) NOT NULL,
    name VARCHAR(200) NOT NULL,
    type VARCHAR(50),
    level VARCHAR(50),
    address_raw TEXT,
    address_norm TEXT,
    phone VARCHAR(20),
    homepage VARCHAR(200),
    lat DECIMAL(10,8),
    lon DECIMAL(11,8),
    si_do VARCHAR(50),
    si_gun_gu VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(source, source_key)
);

-- 지하철역 테이블
CREATE TABLE IF NOT EXISTS infra.subway_stations (
    id SERIAL PRIMARY KEY,
    source VARCHAR(50) NOT NULL,
    source_key VARCHAR(100) NOT NULL,
    name VARCHAR(100) NOT NULL,
    name_eng VARCHAR(100),
    name_chn VARCHAR(100),
    name_jpn VARCHAR(100),
    line_num VARCHAR(20),
    fr_code VARCHAR(20),
    si_do VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(source, source_key)
);

-- 공원 테이블
CREATE TABLE IF NOT EXISTS infra.parks (
    id SERIAL PRIMARY KEY,
    source VARCHAR(50) NOT NULL,
    source_key VARCHAR(100) NOT NULL,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    area DECIMAL(15,2),
    open_date VARCHAR(50),
    main_equipment TEXT,
    main_plants TEXT,
    guidance TEXT,
    visit_road TEXT,
    use_refer TEXT,
    address_raw TEXT,
    address_norm TEXT,
    phone VARCHAR(20),
    lat DECIMAL(10,8),
    lon DECIMAL(11,8),
    si_do VARCHAR(50),
    si_gun_gu VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(source, source_key)
);

-- 약국 테이블
CREATE TABLE IF NOT EXISTS infra.pharmacies (
    id SERIAL PRIMARY KEY,
    source VARCHAR(50) NOT NULL,
    source_key VARCHAR(100) NOT NULL,
    name VARCHAR(200) NOT NULL,
    type VARCHAR(50),
    address_raw TEXT,
    address_norm TEXT,
    phone VARCHAR(20),
    lat DECIMAL(10,8),
    lon DECIMAL(11,8),
    si_do VARCHAR(50),
    si_gun_gu VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(source, source_key)
);

-- 인덱스 생성
CREATE INDEX IF NOT EXISTS idx_childcare_location ON infra.childcare(lat, lon);
CREATE INDEX IF NOT EXISTS idx_childcare_gu ON infra.childcare(si_gun_gu);
CREATE INDEX IF NOT EXISTS idx_childcare_type ON infra.childcare(type);

CREATE INDEX IF NOT EXISTS idx_schools_location ON infra.schools(lat, lon);
CREATE INDEX IF NOT EXISTS idx_schools_gu ON infra.schools(si_gun_gu);
CREATE INDEX IF NOT EXISTS idx_schools_type ON infra.schools(type);

CREATE INDEX IF NOT EXISTS idx_subway_line ON infra.subway_stations(line_num);
CREATE INDEX IF NOT EXISTS idx_subway_fr_code ON infra.subway_stations(fr_code);

CREATE INDEX IF NOT EXISTS idx_parks_location ON infra.parks(lat, lon);
CREATE INDEX IF NOT EXISTS idx_parks_gu ON infra.parks(si_gun_gu);

CREATE INDEX IF NOT EXISTS idx_pharmacies_location ON infra.pharmacies(lat, lon);
CREATE INDEX IF NOT EXISTS idx_pharmacies_gu ON infra.pharmacies(si_gun_gu);

-- 업데이트 트리거 함수
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- 업데이트 트리거 생성
CREATE TRIGGER update_childcare_updated_at BEFORE UPDATE ON infra.childcare
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_schools_updated_at BEFORE UPDATE ON infra.schools
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_subway_stations_updated_at BEFORE UPDATE ON infra.subway_stations
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_parks_updated_at BEFORE UPDATE ON infra.parks
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_pharmacies_updated_at BEFORE UPDATE ON infra.pharmacies
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();





