-- ========================================
-- ⚠️ 나중에 확장할 기능 - PostGIS 기반 주택-인프라 공간 쿼리 뷰
-- ========================================
-- 이 SQL 파일은 Multi-Agent 시스템이 잘 작동하는 것을 확인한 후,
-- Infra Agent 추가 시 사용할 예정입니다.
--
-- 목적: 주택별 반경 500m 내 인프라 정보를 미리 계산하여 뷰로 제공
-- 사용처: Multi-Agent 추천 시스템의 Infra Agent

SET search_path TO infra, housing, public;

-- ========================================
-- 1. PostGIS 확장 설치 (필요 시)
-- ========================================
CREATE EXTENSION IF NOT EXISTS postgis;

-- ========================================
-- 2. Geometry 컬럼 추가 (기존 테이블에 없을 경우)
-- ========================================

-- housing.addresses에 geometry 컬럼 추가
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'housing' 
        AND table_name = 'addresses' 
        AND column_name = 'geometry'
    ) THEN
        ALTER TABLE housing.addresses 
        ADD COLUMN geometry GEOMETRY(POINT, 4326);
        
        -- 기존 lat/lon 데이터로 geometry 생성
        UPDATE housing.addresses 
        SET geometry = ST_SetSRID(ST_MakePoint(longitude, latitude), 4326)
        WHERE latitude IS NOT NULL AND longitude IS NOT NULL;
        
        -- 인덱스 생성 (공간 쿼리 성능 향상)
        CREATE INDEX IF NOT EXISTS idx_addresses_geometry 
        ON housing.addresses USING GIST(geometry);
        
        RAISE NOTICE 'Added geometry column to housing.addresses';
    END IF;
END $$;

-- infra.facility_info에 geometry 컬럼 추가
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'infra' 
        AND table_name = 'facility_info' 
        AND column_name = 'geometry'
    ) THEN
        ALTER TABLE infra.facility_info 
        ADD COLUMN geometry GEOMETRY(POINT, 4326);
        
        -- 기존 lat/lon 데이터로 geometry 생성
        UPDATE infra.facility_info 
        SET geometry = ST_SetSRID(ST_MakePoint(lon, lat), 4326)
        WHERE lat IS NOT NULL AND lon IS NOT NULL;
        
        -- 인덱스 생성
        CREATE INDEX IF NOT EXISTS idx_facility_info_geometry 
        ON infra.facility_info USING GIST(geometry);
        
        RAISE NOTICE 'Added geometry column to infra.facility_info';
    END IF;
END $$;

-- infra.transport_points에 geometry 컬럼 추가
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_schema = 'infra' 
        AND table_name = 'transport_points' 
        AND column_name = 'geometry'
    ) THEN
        ALTER TABLE infra.transport_points 
        ADD COLUMN geometry GEOMETRY(POINT, 4326);
        
        -- 기존 lat/lon 데이터로 geometry 생성
        UPDATE infra.transport_points 
        SET geometry = ST_SetSRID(ST_MakePoint(lon, lat), 4326)
        WHERE lat IS NOT NULL AND lon IS NOT NULL;
        
        -- 인덱스 생성
        CREATE INDEX IF NOT EXISTS idx_transport_points_geometry 
        ON infra.transport_points USING GIST(geometry);
        
        RAISE NOTICE 'Added geometry column to infra.transport_points';
    END IF;
END $$;

-- ========================================
-- 3. housing_facility_distances 테이블 채우기
-- ========================================
-- 대학교(col): 반경 1km, 그 외 인프라: 반경 500m 기준으로 거리 계산

-- 기존 데이터 삭제 (재계산 시)
TRUNCATE TABLE infra.housing_facility_distances;

-- 주택-인프라 거리 계산 및 저장
INSERT INTO infra.housing_facility_distances (notice_id, facility_id, distance_m)
SELECT DISTINCT
    n.notice_id,
    fi.facility_id,
    ROUND(ST_Distance(
        ST_Transform(a.geometry, 3857),  -- Web Mercator (미터 단위)
        ST_Transform(fi.geometry, 3857)
    )::numeric, 0)::INTEGER AS distance_m
FROM housing.notices n
INNER JOIN housing.addresses a ON n.address_id = a.id
CROSS JOIN infra.facility_info fi
WHERE a.geometry IS NOT NULL
  AND fi.geometry IS NOT NULL
  AND (
    -- 대학교(col)는 반경 1km
    (fi.cd = 'col' AND ST_DWithin(
        ST_Transform(a.geometry, 3857),
        ST_Transform(fi.geometry, 3857),
        1000  -- 1km
    ))
    OR
    -- 그 외 인프라는 반경 500m
    (fi.cd != 'col' AND ST_DWithin(
        ST_Transform(a.geometry, 3857),
        ST_Transform(fi.geometry, 3857),
        500  -- 500m
    ))
  )
ON CONFLICT (notice_id, facility_id) DO UPDATE
SET distance_m = EXCLUDED.distance_m;

-- 인덱스 확인 (이미 infra_schema.sql에 있을 수 있음)
CREATE INDEX IF NOT EXISTS idx_housing_facility_distances_notice 
ON infra.housing_facility_distances(notice_id);
CREATE INDEX IF NOT EXISTS idx_housing_facility_distances_facility 
ON infra.housing_facility_distances(facility_id);
CREATE INDEX IF NOT EXISTS idx_housing_facility_distances_distance 
ON infra.housing_facility_distances(distance_m);

-- ========================================
-- 4. 주택별 반경 500m 내 인프라 요약 뷰 (JSONB 형태)
-- ========================================

-- 기존 뷰 삭제 (재생성 시)
DROP VIEW IF EXISTS infra.v_housing_infra_500m_summary CASCADE;

CREATE VIEW infra.v_housing_infra_500m_summary AS
WITH housing_points AS (
    -- 주택 위치 (geometry 컬럼 사용)
    SELECT 
        n.notice_id,
        n.title,
        a.geometry AS housing_point,
        a.latitude,
        a.longitude
    FROM housing.notices n
    INNER JOIN housing.addresses a ON n.address_id = a.id
    WHERE a.geometry IS NOT NULL
),
facility_names AS (
    -- 반경 500m 내 공공시설 이름들 (카테고리별로 콤마 구분)
    -- 주의: 대학교는 housing_facility_distances에 1km까지 저장되지만, 뷰에서는 500m만 표시
    SELECT 
        hp.notice_id,
        fi.cd AS facility_type,
        STRING_AGG(fi.name, ', ' ORDER BY hfd.distance_m) AS facility_names
    FROM housing_points hp
    INNER JOIN infra.housing_facility_distances hfd ON hp.notice_id = hfd.notice_id
    INNER JOIN infra.facility_info fi ON hfd.facility_id = fi.facility_id
    WHERE hfd.distance_m <= 500  -- 반경 500m 내 (대학교 포함)
    GROUP BY hp.notice_id, fi.cd
),
transport_counts AS (
    -- 반경 500m 내 교통시설 개수 (지하철/버스별)
    SELECT 
        hp.notice_id,
        tp.transport_type,
        COUNT(*) AS count,
        MIN(ST_Distance(
            ST_Transform(hp.housing_point, 3857),
            ST_Transform(tp.geometry, 3857)
        )) AS min_distance_m,
        -- 지하철역만 추가 정보
        COUNT(CASE WHEN tp.transport_type = 'subway' AND tp.is_transfer THEN 1 END) AS transfer_station_count
    FROM housing_points hp
    CROSS JOIN LATERAL (
        SELECT 
            tp.id,
            tp.transport_type,
            tp.geometry,
            tp.is_transfer
        FROM infra.transport_points tp
        WHERE tp.geometry IS NOT NULL
        AND ST_DWithin(
            ST_Transform(hp.housing_point, 3857),
            ST_Transform(tp.geometry, 3857),
            500
        )
    ) tp
    GROUP BY hp.notice_id, tp.transport_type
),
infra_jsonb AS (
    -- 시설 타입별로 JSONB 생성
    SELECT 
        hp.notice_id,
        jsonb_object_agg(
            CASE fn.facility_type
                WHEN 'child' THEN '어린이집'
                WHEN 'chsch' THEN '유치원'
                WHEN 'sch' THEN '학교'
                WHEN 'col' THEN '대학교'
                WHEN 'pha' THEN '약국'
                WHEN 'hos' THEN '병원'
                WHEN 'mt' THEN '마트'
                WHEN 'con' THEN '편의점'
                WHEN 'gym' THEN '체육시설'
                WHEN 'park' THEN '공원'
                ELSE fn.facility_type
            END,
            fn.facility_names
        ) FILTER (WHERE fn.facility_type IS NOT NULL) AS facilities_jsonb
    FROM housing_points hp
    LEFT JOIN facility_names fn ON hp.notice_id = fn.notice_id
    GROUP BY hp.notice_id
)
SELECT 
    hp.notice_id,
    hp.title,
    hp.latitude,
    hp.longitude,
    
    -- 공공시설 요약 (JSONB 형태: {어린이집: "하늘빛어린이집", 학교: "은성중학교, 광안고등학교", ...})
    COALESCE(ij.facilities_jsonb, '{}'::jsonb) AS facilities_500m,
    
    -- 교통시설 요약
    COALESCE(SUM(CASE WHEN tc.transport_type = 'subway' THEN tc.count ELSE 0 END), 0) AS subway_stations_500m,
    COALESCE(SUM(CASE WHEN tc.transport_type = 'bus' THEN tc.count ELSE 0 END), 0) AS bus_stops_500m,
    COALESCE(SUM(CASE WHEN tc.transport_type = 'subway' THEN tc.min_distance_m ELSE NULL END), NULL) AS nearest_subway_distance_m,
    COALESCE(SUM(CASE WHEN tc.transport_type = 'bus' THEN tc.min_distance_m ELSE NULL END), NULL) AS nearest_bus_distance_m,
    COALESCE(SUM(CASE WHEN tc.transport_type = 'subway' THEN tc.transfer_station_count ELSE 0 END), 0) AS transfer_stations_500m,
    
    -- 종합 점수 (간단한 점수 계산)
    -- 인프라 점수 = (지하철역 개수 * 10) + (버스정류소 개수 * 1) + (공공시설 개수 * 2)
    (
        COALESCE(SUM(CASE WHEN tc.transport_type = 'subway' THEN tc.count ELSE 0 END), 0) * 10 +
        COALESCE(SUM(CASE WHEN tc.transport_type = 'bus' THEN tc.count ELSE 0 END), 0) * 1 +
        COALESCE((SELECT COUNT(*) FROM infra.housing_facility_distances hfd 
                  WHERE hfd.notice_id = hp.notice_id AND hfd.distance_m <= 500), 0) * 2
    ) AS infra_score
    
FROM housing_points hp
LEFT JOIN infra_jsonb ij ON hp.notice_id = ij.notice_id
LEFT JOIN transport_counts tc ON hp.notice_id = tc.notice_id
GROUP BY hp.notice_id, hp.title, hp.latitude, hp.longitude, ij.facilities_jsonb;

-- 뷰 설명 추가
COMMENT ON VIEW infra.v_housing_infra_500m_summary IS 
'주택별 반경 500m 내 인프라 요약 정보
- facilities_500m: 카테고리별 공공시설 이름 (JSONB 형태)
  예: {"어린이집": "하늘빛어린이집", "대학교": "한성대학교", "학교": "은성중학교, 광안고등학교"}
- subway_stations_500m: 지하철역 개수
- bus_stops_500m: 버스정류소 개수
- nearest_subway_distance_m: 가장 가까운 지하철역 거리 (미터)
- nearest_bus_distance_m: 가장 가까운 버스정류소 거리 (미터)
- transfer_stations_500m: 환승역 개수
- infra_score: 종합 인프라 점수';

-- ========================================
-- 5. 상세 인프라 정보 뷰 (선택적)
-- ========================================

DROP VIEW IF EXISTS infra.v_housing_infra_500m_detail CASCADE;

CREATE VIEW infra.v_housing_infra_500m_detail AS
SELECT 
    n.notice_id,
    n.title,
    a.latitude AS housing_lat,
    a.longitude AS housing_lon,
    
    -- 공공시설 상세
    fi.facility_id,
    fi.cd AS facility_type,
    fi.name AS facility_name,
    ROUND(ST_Distance(
        ST_Transform(a.geometry, 3857),
        ST_Transform(fi.geometry, 3857)
    )::numeric, 0) AS distance_m
    
FROM housing.notices n
INNER JOIN housing.addresses a ON n.address_id = a.id
CROSS JOIN LATERAL (
    SELECT 
        fi.facility_id,
        fi.cd,
        fi.name,
        fi.geometry
    FROM infra.facility_info fi
    WHERE fi.geometry IS NOT NULL
    AND ST_DWithin(
        ST_Transform(a.geometry, 3857),
        ST_Transform(fi.geometry, 3857),
        500
    )
) fi
WHERE a.geometry IS NOT NULL

UNION ALL

SELECT 
    n.notice_id,
    n.title,
    a.latitude AS housing_lat,
    a.longitude AS housing_lon,
    
    -- 교통시설 상세
    tp.id AS facility_id,
    tp.transport_type AS facility_type,
    COALESCE(tp.name, '') AS facility_name,
    ROUND(ST_Distance(
        ST_Transform(a.geometry, 3857),
        ST_Transform(tp.geometry, 3857)
    )::numeric, 0) AS distance_m
    
FROM housing.notices n
INNER JOIN housing.addresses a ON n.address_id = a.id
CROSS JOIN LATERAL (
    SELECT 
        tp.id,
        tp.transport_type,
        tp.name,
        tp.geometry
    FROM infra.transport_points tp
    WHERE tp.geometry IS NOT NULL
    AND ST_DWithin(
        ST_Transform(a.geometry, 3857),
        ST_Transform(tp.geometry, 3857),
        500
    )
) tp
WHERE a.geometry IS NOT NULL;

COMMENT ON VIEW infra.v_housing_infra_500m_detail IS 
'주택별 반경 500m 내 인프라 상세 정보 (각 시설별 행)
- facility_type: 시설 유형 (child, sch, hos, subway, bus 등)
- distance_m: 주택부터 시설까지 거리 (미터)';

-- ========================================
-- 6. 인덱스 최적화 (성능 향상)
-- ========================================

-- notices-addresses 조인 성능 향상
CREATE INDEX IF NOT EXISTS idx_notices_address_id 
ON housing.notices(address_id) 
WHERE address_id IS NOT NULL;

-- 공간 쿼리 성능을 위한 인덱스는 이미 위에서 생성됨

-- ========================================
-- 7. 사용 예시 쿼리
-- ========================================

/*
-- 요약 정보 조회 (JSONB 형태)
SELECT 
    notice_id,
    title,
    facilities_500m,
    facilities_500m->>'어린이집' AS child_care_names,
    facilities_500m->>'학교' AS school_names,
    facilities_500m->>'대학교' AS university_names,
    subway_stations_500m,
    bus_stops_500m,
    nearest_subway_distance_m,
    infra_score
FROM infra.v_housing_infra_500m_summary
WHERE notice_id = 'some_notice_id';

-- 인프라 점수 상위 주택 조회
SELECT 
    notice_id,
    title,
    facilities_500m,
    infra_score,
    subway_stations_500m,
    bus_stops_500m
FROM infra.v_housing_infra_500m_summary
ORDER BY infra_score DESC
LIMIT 10;

-- housing_facility_distances 테이블 조회
SELECT 
    hfd.notice_id,
    n.title,
    fi.name AS facility_name,
    ic.name AS facility_type_name,
    hfd.distance_m
FROM infra.housing_facility_distances hfd
INNER JOIN housing.notices n ON hfd.notice_id = n.notice_id
INNER JOIN infra.facility_info fi ON hfd.facility_id = fi.facility_id
INNER JOIN infra.infra_code ic ON fi.cd = ic.cd
WHERE hfd.notice_id = 'some_notice_id'
ORDER BY hfd.distance_m
LIMIT 20;
*/

