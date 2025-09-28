-- PostgreSQL 스키마 구조 설계
-- 논리적 그룹핑을 통한 명확한 데이터베이스 구조

-- ===========================================
-- 1. 스키마 생성
-- ===========================================

-- 주택 관련 스키마
CREATE SCHEMA IF NOT EXISTS housing;

-- 공공시설 관련 스키마  
CREATE SCHEMA IF NOT EXISTS infra;

-- RTMS 관련 스키마 (실거래가)
CREATE SCHEMA IF NOT EXISTS rtms;

-- ===========================================
-- 2. 스키마별 테이블 구조
-- ===========================================

-- HOUSING 스키마 (주택 관련)
-- - notices (공고) - platform, building_type, unit_type 컬럼 포함
-- - units (유닛)
-- - addresses (주소)
-- - attachments (첨부파일: 이미지, 평면도, 공고서 등)
-- - unit_features (유닛 특징)
-- - notice_tags (공고 태그)

-- INFRA 스키마 (공공시설 관련)
-- - public_facilities (공공시설)
-- - facility_categories (시설 카테고리)
-- - subway_stations (지하철역)
-- - housing_facility_distances (주택-시설 거리)

-- RTMS 스키마 (실거래가 관련)
-- - transaction_data (실거래 데이터)
-- - price_trends (가격 동향)
-- - market_analysis (시장 분석)

-- ===========================================
-- 3. 스키마 간 FK 참조 예시
-- ===========================================

-- housing.notices가 housing.addresses 참조
-- housing.units가 housing.notices 참조
-- housing.attachments가 housing.notices 참조
-- housing.notices가 infra.housing_facility_distances와 연결

-- ===========================================
-- 4. 검색 경로 설정
-- ===========================================

-- 기본 검색 경로 설정 (스키마 명시 없이 사용 가능)
ALTER DATABASE rey SET search_path TO housing, infra, rtms;
