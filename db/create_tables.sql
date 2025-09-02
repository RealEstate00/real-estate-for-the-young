-- DB 생성/사용
CREATE DATABASE IF NOT EXISTS SHA_bot
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;
USE SHA_bot;

-- Sources (platform metadata)
CREATE TABLE IF NOT EXISTS sources (
  source_id INT AUTO_INCREMENT PRIMARY KEY,
  platform VARCHAR(40) NOT NULL UNIQUE,
  base_url TEXT,
  category VARCHAR(20)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Regions (standardized city/district)
CREATE TABLE IF NOT EXISTS regions (
  region_id INT AUTO_INCREMENT PRIMARY KEY,
  city VARCHAR(40) NOT NULL,
  district VARCHAR(40) NOT NULL,
  UNIQUE KEY uk_city_district (city, district)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Crawl run logs
CREATE TABLE IF NOT EXISTS crawl_runs (
  run_id BIGINT AUTO_INCREMENT PRIMARY KEY,
  started_at DATETIME NOT NULL,
  finished_at DATETIME,
  pages_fetched INT DEFAULT 0,
  errors INT DEFAULT 0,
  note TEXT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Raw documents (bronze) reference
CREATE TABLE IF NOT EXISTS raw_documents (
  url_hash VARCHAR(64) PRIMARY KEY,
  url TEXT NOT NULL,
  saved_path TEXT,
  content_type VARCHAR(255),
  http_status INT,
  crawl_run_id BIGINT,
  crawled_at DATETIME NOT NULL,
  FOREIGN KEY (crawl_run_id) REFERENCES crawl_runs(run_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Core listings (gold)
CREATE TABLE IF NOT EXISTS listings (
  record_id VARCHAR(64) PRIMARY KEY,
  platform VARCHAR(40) NOT NULL,
  category VARCHAR(20) NOT NULL,
  title TEXT,
  status VARCHAR(40),
  housing_type VARCHAR(40),
  project_name TEXT,
  address_full TEXT,
  city VARCHAR(40),
  district VARCHAR(40),
  subway_lines TEXT,
  deposit_won BIGINT NULL,
  rent_won BIGINT NULL,
  supply_total_units INT NULL,
  public_units INT NULL,
  private_units INT NULL,
  area_m2_min DOUBLE NULL,
  area_m2_max DOUBLE NULL,
  announce_date DATE NULL,
  deadline_date DATE NULL,
  detail_url TEXT,
  list_url TEXT,
  attachments_count INT DEFAULT 0,
  crawled_at DATETIME NOT NULL,
  source_id INT NULL,
  region_id INT NULL,
  location POINT SRID 4326 NULL,
  KEY idx_platform_category (platform, category),
  KEY idx_dates (announce_date, deadline_date),
  KEY idx_region (city, district),
  KEY idx_type (housing_type),
  KEY idx_source (source_id),
  KEY idx_region_id (region_id),
  SPATIAL INDEX idx_location (location),
  CONSTRAINT fk_listings_source FOREIGN KEY (source_id) REFERENCES sources(source_id),
  CONSTRAINT fk_listings_region FOREIGN KEY (region_id) REFERENCES regions(region_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Attachments metadata
CREATE TABLE IF NOT EXISTS attachments (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  record_id VARCHAR(64) NOT NULL,
  file_name TEXT,
  stored_path TEXT,
  mime VARCHAR(255),
  bytes BIGINT,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (record_id) REFERENCES listings(record_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- rtms & landprice

CREATE TABLE IF NOT EXISTS rtms_rent (
  record_id VARCHAR(64) PRIMARY KEY,
  housing_kind VARCHAR(20),
  jw_type VARCHAR(10),
  year SMALLINT,
  quarter TINYINT,
  city VARCHAR(40),
  district VARCHAR(40),
  dong_code VARCHAR(10),
  dong_name VARCHAR(40),
  complex_name TEXT,
  built_year INT NULL,
  jibun TEXT,
  area_m2 DOUBLE,
  monthly_won BIGINT,
  market_price_won BIGINT NULL,
  contract_date DATE,
  contract_division VARCHAR(40),
  deposit_won BIGINT,
  floor INT,
  list_url TEXT,
  crawled_at DATETIME,
  region_id INT NULL,
  KEY idx_region (district, dong_name),
  KEY idx_date (contract_date),
  KEY idx_kind (housing_kind, jw_type),
  FOREIGN KEY (region_id) REFERENCES regions(region_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS land_official_files (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  file_year INT NULL,
  saved_path TEXT,
  file_name TEXT,
  bytes BIGINT,
  source_url TEXT,
  download_js TEXT,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- listings 확장: 출처, 지역, 좌표(지도)
ALTER TABLE listings
  ADD COLUMN source_id INT NULL,
  ADD COLUMN region_id INT NULL,
  ADD COLUMN location POINT NULL SRID 4326,
  ADD KEY idx_source (source_id),
  ADD KEY idx_region_id (region_id),
  ADD SPATIAL INDEX idx_location (location),
  ADD CONSTRAINT fk_listings_source
    FOREIGN KEY (source_id) REFERENCES sources(source_id),
  ADD CONSTRAINT fk_listings_region
    FOREIGN KEY (region_id) REFERENCES regions(region_id);

-- 지하철 노선/역 
CREATE TABLE IF NOT EXISTS subway_lines (
  line_id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(50) UNIQUE
);
CREATE TABLE IF NOT EXISTS listing_subway (
  record_id VARCHAR(64),
  line_id INT,
  PRIMARY KEY(record_id, line_id),
  FOREIGN KEY (record_id) REFERENCES listings(record_id),
  FOREIGN KEY (line_id) REFERENCES subway_lines(line_id)
);

-- 간단한 로그인/즐겨찾기
CREATE TABLE IF NOT EXISTS users (
  user_id BIGINT AUTO_INCREMENT PRIMARY KEY,
  email VARCHAR(255) UNIQUE,
  password_hash VARCHAR(255),
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS favorites (
  user_id BIGINT,
  record_id VARCHAR(64),
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY(user_id, record_id),
  FOREIGN KEY (user_id) REFERENCES users(user_id),
  FOREIGN KEY (record_id) REFERENCES listings(record_id)
);
