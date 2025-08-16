# 🗄️ DBeaver를 통한 서울시 사회주택 데이터베이스 관리 가이드

## 📋 목차
1. [데이터베이스 구조 개요](#데이터베이스-구조-개요)
2. [DBeaver 연결 설정](#dbeaver-연결-설정)
3. [테이블 구조 설명](#테이블-구조-설명)
4. [유용한 SQL 쿼리](#유용한-sql-쿼리)
5. [데이터 분석 예시](#데이터-분석-예시)

## 🏗️ 데이터베이스 구조 개요

### 📊 ERD (Entity Relationship Diagram)
```
housing (주택 기본정보)
├── business_info (사업자 정보) [1:1]
├── floor_plan_images (평면도 이미지) [1:N]
├── occupancy_status (입주현황) [1:N]  
├── transportation (교통정보) [1:N]
├── facilities (편의시설) [1:N]
└── crawling_logs (크롤링 로그) [1:N]
```

### 🎯 정규화 수준
- **제3정규형(3NF)** 준수
- **외래키 제약조건** 설정
- **인덱스 최적화** 완료

## 🔌 DBeaver 연결 설정

### 1. SQLite 연결 (기본)
```
연결 타입: SQLite
데이터베이스 파일: crolling_/seoul_housing.db
드라이버: SQLite JDBC
```

### 2. PostgreSQL 연결 (운영환경)
```
호스트: localhost
포트: 5432
데이터베이스: seoul_housing
사용자명: your_username
비밀번호: your_password
```

### 3. MySQL 연결 (대안)
```
호스트: localhost
포트: 3306
데이터베이스: seoul_housing
사용자명: root
비밀번호: your_password
```

## 📋 테이블 구조 설명

### 1. `housing` (주택 기본정보) - 메인 테이블
| 컬럼명 | 타입 | 설명 | 예시 |
|--------|------|------|------|
| id | INTEGER | 기본키 | 1 |
| house_name | TEXT | 주택명 | 오늘공동체주택 |
| address | TEXT | 주소 | 서울 도봉구 도봉로191길 80 |
| target_residents | TEXT | 입주대상 | 제한없음 |
| housing_type | TEXT | 주거형태 | 다세대주택 |
| area_info | TEXT | 면적정보 | 전용 655.42m² / 공용 237.24m² |
| total_residents | TEXT | 총 주거인원 | 총 14명 / 총 6호 / 총 6실 |

### 2. `business_info` (사업자 정보)
| 컬럼명 | 타입 | 설명 | 예시 |
|--------|------|------|------|
| housing_id | INTEGER | 외래키 | 1 |
| company_name | TEXT | 상호 | 주택협동조합 오늘공동체 |
| ceo_name | TEXT | 대표자 | 선주리 |
| phone | TEXT | 대표전화 | 010-3595-8114 |
| email | TEXT | 이메일 | example@email.com |

### 3. `occupancy_status` (입주현황)
| 컬럼명 | 타입 | 설명 | 예시 |
|--------|------|------|------|
| housing_id | INTEGER | 외래키 | 1 |
| room_name | TEXT | 방이름 | 101호 |
| area | TEXT | 면적 | 28.49m² |
| deposit | REAL | 보증금 | 50000000 |
| monthly_rent | REAL | 월임대료 | 320000 |
| management_fee | REAL | 관리비 | 0 |
| capacity | INTEGER | 수용인원 | 1 |
| is_available | BOOLEAN | 입주가능여부 | 1 |

### 4. `transportation` (교통정보)
| 컬럼명 | 타입 | 설명 | 예시 |
|--------|------|------|------|
| housing_id | INTEGER | 외래키 | 1 |
| transport_type | TEXT | 교통수단 | subway, bus |
| line_info | TEXT | 노선정보 | 1호선, 7호선 |
| station_name | TEXT | 역명 | 도봉산역 |

### 5. `floor_plan_images` (평면도 이미지)
| 컬럼명 | 타입 | 설명 | 예시 |
|--------|------|------|------|
| housing_id | INTEGER | 외래키 | 1 |
| image_url | TEXT | 이미지 URL | /cohome/cmmn/file/... |
| alt_text | TEXT | 이미지 설명 | 오늘공동체주택_평면도_1 |
| image_order | INTEGER | 순서 | 1 |

## 🔍 유용한 SQL 쿼리

### 1. 기본 조회 쿼리
```sql
-- 모든 주택 정보 조회
SELECT h.house_name, h.address, h.housing_type, b.company_name, b.phone
FROM housing h
LEFT JOIN business_info b ON h.id = b.housing_id;

-- 입주 가능한 방 정보
SELECT h.house_name, o.room_name, o.area, o.deposit, o.monthly_rent
FROM housing h
JOIN occupancy_status o ON h.id = o.housing_id
WHERE o.is_available = 1
ORDER BY o.monthly_rent;
```

### 2. 통계 분석 쿼리
```sql
-- 주택별 총 정보 요약
SELECT 
    h.house_name,
    COUNT(DISTINCT i.id) as 평면도_수,
    COUNT(DISTINCT o.id) as 총_방수,
    COUNT(CASE WHEN o.is_available = 1 THEN 1 END) as 입주가능_방수,
    AVG(o.monthly_rent) as 평균_월세,
    COUNT(DISTINCT t.id) as 교통옵션_수
FROM housing h
LEFT JOIN floor_plan_images i ON h.id = i.housing_id
LEFT JOIN occupancy_status o ON h.id = o.housing_id  
LEFT JOIN transportation t ON h.id = t.housing_id
GROUP BY h.id, h.house_name;

-- 보증금 범위별 방 분포
SELECT 
    CASE 
        WHEN deposit < 30000000 THEN '3천만원 미만'
        WHEN deposit < 50000000 THEN '3천-5천만원'
        WHEN deposit < 100000000 THEN '5천-1억원'
        ELSE '1억원 이상'
    END as 보증금_범위,
    COUNT(*) as 방_수,
    AVG(monthly_rent) as 평균_월세
FROM occupancy_status
WHERE deposit > 0
GROUP BY 보증금_범위
ORDER BY MIN(deposit);
```

### 3. 교통 접근성 분석
```sql
-- 교통 접근성이 좋은 주택 (지하철 + 버스 모두 있는 곳)
SELECT h.house_name, h.address,
       GROUP_CONCAT(CASE WHEN t.transport_type = 'subway' THEN t.line_info END) as 지하철,
       GROUP_CONCAT(CASE WHEN t.transport_type = 'bus' THEN t.line_info END) as 버스
FROM housing h
JOIN transportation t ON h.id = t.housing_id
GROUP BY h.id, h.house_name, h.address
HAVING COUNT(DISTINCT t.transport_type) >= 2;

-- 지하철 노선별 주택 분포
SELECT t.line_info as 지하철노선, COUNT(DISTINCT h.id) as 주택수
FROM transportation t
JOIN housing h ON t.housing_id = h.id
WHERE t.transport_type = 'subway'
GROUP BY t.line_info
ORDER BY 주택수 DESC;
```

### 4. 데이터 품질 검증
```sql
-- 데이터 완성도 체크
SELECT 
    '주택 기본정보' as 테이블,
    COUNT(*) as 총_레코드,
    SUM(CASE WHEN house_name IS NOT NULL AND house_name != '' THEN 1 ELSE 0 END) as 주택명_완성,
    SUM(CASE WHEN address IS NOT NULL AND address != '' THEN 1 ELSE 0 END) as 주소_완성
FROM housing

UNION ALL

SELECT 
    '사업자 정보',
    COUNT(*),
    SUM(CASE WHEN company_name IS NOT NULL AND company_name != '' THEN 1 ELSE 0 END),
    SUM(CASE WHEN phone IS NOT NULL AND phone != '' THEN 1 ELSE 0 END)
FROM business_info;

-- 중복 데이터 체크
SELECT house_name, address, COUNT(*) as 중복수
FROM housing
GROUP BY house_name, address
HAVING COUNT(*) > 1;
```

## 📊 데이터 분석 예시

### 1. 대시보드용 KPI 쿼리
```sql
-- 핵심 지표 한 번에 조회
SELECT 
    (SELECT COUNT(*) FROM housing) as 총_주택수,
    (SELECT COUNT(*) FROM occupancy_status WHERE is_available = 1) as 입주가능_방수,
    (SELECT AVG(monthly_rent) FROM occupancy_status WHERE monthly_rent > 0) as 평균_월세,
    (SELECT COUNT(DISTINCT housing_id) FROM transportation WHERE transport_type = 'subway') as 지하철_접근_주택수;
```

### 2. 월세 분석
```sql
-- 면적대비 월세 효율성 분석
SELECT 
    h.house_name,
    o.room_name,
    o.area,
    o.monthly_rent,
    CAST(SUBSTR(o.area, 1, INSTR(o.area, 'm²')-1) AS REAL) as 면적_숫자,
    ROUND(o.monthly_rent / CAST(SUBSTR(o.area, 1, INSTR(o.area, 'm²')-1) AS REAL), 0) as 평방미터당_월세
FROM housing h
JOIN occupancy_status o ON h.id = o.housing_id
WHERE o.monthly_rent > 0 
  AND o.area LIKE '%m²%'
ORDER BY 평방미터당_월세;
```

### 3. 크롤링 성과 분석
```sql
-- 크롤링 성공률 및 데이터 수집 현황
SELECT 
    status as 상태,
    COUNT(*) as 건수,
    AVG(images_collected) as 평균_이미지수,
    AVG(rooms_collected) as 평균_방수,
    AVG(transport_collected) as 평균_교통정보수
FROM crawling_logs
GROUP BY status;
```

## 🎯 DBeaver 활용 팁

### 1. 데이터 시각화
- **차트 생성**: 쿼리 결과 → 우클릭 → "View Chart"
- **피벗 테이블**: 집계 데이터를 피벗 형태로 표시
- **히트맵**: 월세/보증금 분포를 색상으로 표현

### 2. 데이터 내보내기
```sql
-- CSV 내보내기용 완전한 데이터셋
SELECT 
    h.house_name as 주택명,
    h.address as 주소,
    h.housing_type as 주거형태,
    b.company_name as 운영사,
    b.phone as 연락처,
    o.room_name as 방이름,
    o.area as 면적,
    o.deposit as 보증금,
    o.monthly_rent as 월세,
    GROUP_CONCAT(DISTINCT t.line_info) as 교통정보
FROM housing h
LEFT JOIN business_info b ON h.id = b.housing_id
LEFT JOIN occupancy_status o ON h.id = o.housing_id
LEFT JOIN transportation t ON h.id = t.housing_id
GROUP BY h.id, o.id
ORDER BY h.house_name, o.room_name;
```

### 3. 정기 모니터링 쿼리
```sql
-- 매일 실행할 데이터 품질 체크
SELECT 
    'Data Quality Report - ' || DATE('now') as 보고서,
    (SELECT COUNT(*) FROM housing) as 총_주택,
    (SELECT COUNT(*) FROM occupancy_status WHERE is_available = 1) as 입주가능_방,
    (SELECT COUNT(*) FROM floor_plan_images) as 총_이미지,
    (SELECT MAX(crawl_date) FROM crawling_logs) as 최근_크롤링;
```

## 🚀 고급 활용

### 1. 트리거 설정 (자동 업데이트)
```sql
-- 주택 정보 변경시 업데이트 시간 자동 갱신
CREATE TRIGGER update_housing_timestamp 
    AFTER UPDATE ON housing
BEGIN
    UPDATE housing SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;
```

### 2. 인덱스 성능 모니터링
```sql
-- 쿼리 성능 분석
EXPLAIN QUERY PLAN 
SELECT h.house_name, COUNT(o.id) as room_count
FROM housing h
LEFT JOIN occupancy_status o ON h.id = o.housing_id
GROUP BY h.id;
```

---

> **💡 팁**: DBeaver의 "SQL Script" 기능을 사용해 자주 사용하는 쿼리들을 저장하고 관리하세요!
> 
> **📞 문의**: 데이터베이스 관련 문제가 있을 때는 `crawling_logs` 테이블을 먼저 확인해보세요.
