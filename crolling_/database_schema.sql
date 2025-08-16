-- =====================================================
-- 서울시 사회주택 데이터베이스 스키마
-- DBeaver용 PostgreSQL/MySQL 호환 구조
-- =====================================================

-- 1. 주택 기본 정보 테이블 (메인 테이블)
CREATE TABLE housing (
    id SERIAL PRIMARY KEY,
    house_name VARCHAR(100) NOT NULL COMMENT '주택명',
    address TEXT NOT NULL COMMENT '주소',
    target_residents VARCHAR(200) COMMENT '입주대상',
    housing_type VARCHAR(50) COMMENT '주거형태',
    area_info TEXT COMMENT '면적 정보',
    total_residents VARCHAR(100) COMMENT '총 주거인원',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- 2. 사업자 정보 테이블
CREATE TABLE business_info (
    id SERIAL PRIMARY KEY,
    housing_id INT NOT NULL,
    company_name VARCHAR(200) COMMENT '상호',
    ceo_name VARCHAR(100) COMMENT '대표자',
    phone VARCHAR(50) COMMENT '대표전화',
    email VARCHAR(100) COMMENT '이메일',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (housing_id) REFERENCES housing(id) ON DELETE CASCADE
);

-- 3. 평면도 이미지 테이블
CREATE TABLE floor_plan_images (
    id SERIAL PRIMARY KEY,
    housing_id INT NOT NULL,
    image_url TEXT NOT NULL COMMENT '이미지 URL',
    alt_text VARCHAR(200) COMMENT '이미지 설명',
    image_order INT DEFAULT 1 COMMENT '이미지 순서',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (housing_id) REFERENCES housing(id) ON DELETE CASCADE
);

-- 4. 입주현황 테이블 (각 호실별 정보)
CREATE TABLE occupancy_status (
    id SERIAL PRIMARY KEY,
    housing_id INT NOT NULL,
    room_name VARCHAR(50) NOT NULL COMMENT '방이름 (101호, 201호 등)',
    occupancy_type VARCHAR(50) COMMENT '입주타입',
    area VARCHAR(50) COMMENT '면적',
    deposit DECIMAL(15,2) COMMENT '보증금 (원)',
    monthly_rent DECIMAL(10,2) COMMENT '월임대료 (원)',
    management_fee DECIMAL(10,2) COMMENT '관리비 (원)',
    floor_number INT COMMENT '층',
    room_number INT COMMENT '호',
    capacity INT COMMENT '수용인원',
    available_date DATE COMMENT '입주가능일',
    is_available BOOLEAN DEFAULT TRUE COMMENT '입주가능여부',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (housing_id) REFERENCES housing(id) ON DELETE CASCADE
);

-- 5. 교통 정보 테이블
CREATE TABLE transportation (
    id SERIAL PRIMARY KEY,
    housing_id INT NOT NULL,
    transport_type ENUM('subway', 'bus') NOT NULL COMMENT '교통수단 유형',
    line_info VARCHAR(200) NOT NULL COMMENT '노선 정보',
    station_name VARCHAR(100) COMMENT '역명/정류장명',
    distance_meters INT COMMENT '거리(미터)',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (housing_id) REFERENCES housing(id) ON DELETE CASCADE
);

-- 6. 편의시설 테이블
CREATE TABLE facilities (
    id SERIAL PRIMARY KEY,
    housing_id INT NOT NULL,
    facility_name VARCHAR(100) NOT NULL COMMENT '시설명',
    facility_type VARCHAR(50) COMMENT '시설 유형',
    distance_meters INT COMMENT '거리(미터)',
    description TEXT COMMENT '시설 설명',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (housing_id) REFERENCES housing(id) ON DELETE CASCADE
);

-- 7. 크롤링 로그 테이블 (데이터 수집 이력 관리)
CREATE TABLE crawling_logs (
    id SERIAL PRIMARY KEY,
    housing_id INT,
    crawl_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status ENUM('success', 'partial', 'failed') NOT NULL,
    images_collected INT DEFAULT 0,
    rooms_collected INT DEFAULT 0,
    transport_collected INT DEFAULT 0,
    facilities_collected INT DEFAULT 0,
    error_message TEXT,
    FOREIGN KEY (housing_id) REFERENCES housing(id) ON DELETE SET NULL
);

-- =====================================================
-- 인덱스 생성 (성능 최적화)
-- =====================================================

-- 주택 검색용 인덱스
CREATE INDEX idx_housing_name ON housing(house_name);
CREATE INDEX idx_housing_address ON housing(address(100));
CREATE INDEX idx_housing_type ON housing(housing_type);

-- 입주현황 검색용 인덱스
CREATE INDEX idx_occupancy_room ON occupancy_status(room_name);
CREATE INDEX idx_occupancy_available ON occupancy_status(is_available);
CREATE INDEX idx_occupancy_deposit ON occupancy_status(deposit);
CREATE INDEX idx_occupancy_rent ON occupancy_status(monthly_rent);

-- 교통정보 검색용 인덱스
CREATE INDEX idx_transport_type ON transportation(transport_type);
CREATE INDEX idx_transport_line ON transportation(line_info);

-- 외래키 성능 인덱스
CREATE INDEX idx_business_housing ON business_info(housing_id);
CREATE INDEX idx_images_housing ON floor_plan_images(housing_id);
CREATE INDEX idx_occupancy_housing ON occupancy_status(housing_id);
CREATE INDEX idx_transport_housing ON transportation(housing_id);
CREATE INDEX idx_facilities_housing ON facilities(housing_id);

-- =====================================================
-- 뷰 생성 (편의성)
-- =====================================================

-- 주택 종합 정보 뷰
CREATE VIEW housing_summary AS
SELECT 
    h.id,
    h.house_name,
    h.address,
    h.housing_type,
    h.target_residents,
    b.company_name,
    b.ceo_name,
    b.phone,
    COUNT(DISTINCT i.id) as total_images,
    COUNT(DISTINCT o.id) as total_rooms,
    COUNT(DISTINCT t.id) as transport_options,
    COUNT(DISTINCT f.id) as facilities_count,
    h.created_at
FROM housing h
LEFT JOIN business_info b ON h.id = b.housing_id
LEFT JOIN floor_plan_images i ON h.id = i.housing_id
LEFT JOIN occupancy_status o ON h.id = o.housing_id
LEFT JOIN transportation t ON h.id = t.housing_id
LEFT JOIN facilities f ON h.id = f.housing_id
GROUP BY h.id, h.house_name, h.address, h.housing_type, h.target_residents, 
         b.company_name, b.ceo_name, b.phone, h.created_at;

-- 입주 가능한 방 정보 뷰
CREATE VIEW available_rooms AS
SELECT 
    h.house_name,
    h.address,
    o.room_name,
    o.area,
    o.deposit,
    o.monthly_rent,
    o.management_fee,
    o.capacity,
    o.available_date,
    b.phone as contact_phone
FROM housing h
JOIN occupancy_status o ON h.id = o.housing_id
LEFT JOIN business_info b ON h.id = b.housing_id
WHERE o.is_available = TRUE
ORDER BY h.house_name, o.room_name;

-- 교통 접근성 뷰
CREATE VIEW transport_accessibility AS
SELECT 
    h.house_name,
    h.address,
    GROUP_CONCAT(CASE WHEN t.transport_type = 'subway' THEN t.line_info END) as subway_lines,
    GROUP_CONCAT(CASE WHEN t.transport_type = 'bus' THEN t.line_info END) as bus_lines
FROM housing h
LEFT JOIN transportation t ON h.id = t.housing_id
GROUP BY h.id, h.house_name, h.address;

-- =====================================================
-- 데이터 입력 예시
-- =====================================================

-- 오늘공동체주택 데이터 입력 예시
INSERT INTO housing (house_name, address, target_residents, housing_type, area_info, total_residents) 
VALUES (
    '오늘공동체주택',
    '서울 도봉구 도봉로191길 80 (도봉동 351-2)',
    '제한없음',
    '다세대주택',
    '전용 655.42m² / 공용 237.24m²',
    '총 14명 / 총 6호 / 총 6실'
);

-- 사업자 정보 입력
INSERT INTO business_info (housing_id, company_name, ceo_name, phone) 
VALUES (1, '주택협동조합 오늘공동체', '선주리', '010-3595-8114');

-- 교통 정보 입력
INSERT INTO transportation (housing_id, transport_type, line_info, station_name) VALUES
(1, 'subway', '1호선', '도봉산역'),
(1, 'subway', '7호선', '도봉산역'),
(1, 'bus', '140, 150, 160', NULL);

-- 입주현황 입력 (예시)
INSERT INTO occupancy_status (housing_id, room_name, occupancy_type, area, deposit, monthly_rent, management_fee, floor_number, room_number, capacity) VALUES
(1, '101호', '기타', '28.49m²', 50000000, 320000, 0, 1, 1, 1),
(1, '201호', '기타', '80.02m²', 50000000, 1230000, 0, 2, 1, 5);
