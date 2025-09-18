-- 단순화된 ID 구조를 위한 스키마 개선안
-- 기존 schema.sql을 기반으로 ID 구조를 단순화

-- ===========================================
-- 핵심 ID 구조 단순화
-- ===========================================

-- 1) 플랫폼 테이블 (변경 없음)
CREATE TABLE IF NOT EXISTS platforms (
    id             SERIAL PRIMARY KEY,
    code           TEXT UNIQUE NOT NULL,          -- 'sohouse', 'cohouse' 등
    name           TEXT NOT NULL,
    base_url       TEXT,
    contact_email  TEXT,
    is_active      BOOLEAN DEFAULT TRUE,
    platform_extra JSONB DEFAULT '{}'::jsonb,
    created_at     TIMESTAMPTZ DEFAULT now(),
    updated_at     TIMESTAMPTZ DEFAULT now()
);

-- 2) 공고 테이블 (ID 구조 단순화)
CREATE TABLE IF NOT EXISTS notices (
    id                  BIGSERIAL PRIMARY KEY,                    -- DB 내부 ID
    platform_id         INTEGER NOT NULL REFERENCES platforms(id) ON UPDATE CASCADE,
    
    -- 크롤러 ID (단일화)
    crawler_id          TEXT NOT NULL,                           -- 크롤러에서 생성한 고유 ID (기존 record_id 역할)
    
    -- 플랫폼 식별자
    platform_key        TEXT NOT NULL,                           -- 플랫폼 내 고유키 (기존 source_key)
    
    -- 공고 정보
    title               TEXT NOT NULL,
    detail_url          TEXT,
    list_url            TEXT,
    status              listing_status DEFAULT 'unknown',
    posted_at           TIMESTAMPTZ,
    last_modified       TIMESTAMPTZ,
    apply_start_at      TIMESTAMPTZ,
    apply_end_at        TIMESTAMPTZ,
    
    -- 주소 정보
    address_raw         TEXT,
    address_id          BIGINT,
    
    -- 가격 정보 (공고 레벨)
    deposit_min         NUMERIC(14,2),
    deposit_max         NUMERIC(14,2),
    rent_min            NUMERIC(14,2),
    rent_max            NUMERIC(14,2),
    area_min_m2         NUMERIC(10,2),
    area_max_m2         NUMERIC(10,2),
    
    -- 메타데이터
    description_raw     TEXT,
    notice_extra        JSONB DEFAULT '{}'::jsonb,
    has_images          BOOLEAN DEFAULT FALSE,
    has_floorplan       BOOLEAN DEFAULT FALSE,
    has_documents       BOOLEAN DEFAULT FALSE,
    
    -- 크롤링 메타데이터
    crawled_at          TIMESTAMPTZ DEFAULT now(),
    created_at          TIMESTAMPTZ DEFAULT now(),
    updated_at          TIMESTAMPTZ DEFAULT now(),
    
    -- 제약조건
    UNIQUE (platform_id, platform_key),                          -- 플랫폼 내 고유성
    UNIQUE (crawler_id)                                          -- 크롤러 ID 고유성
);

-- 3) 유닛 테이블 (ID 구조 단순화)
CREATE TABLE IF NOT EXISTS units (
    id                  BIGSERIAL PRIMARY KEY,                    -- DB 내부 ID
    notice_id           BIGINT NOT NULL REFERENCES notices(id) ON DELETE CASCADE,
    
    -- 크롤러 ID (단일화)
    crawler_id          TEXT NOT NULL,                           -- 크롤러에서 생성한 고유 ID
    
    -- 물리적 공간 식별자
    space_id            TEXT,                                    -- 물리적 입주공간 ID (기존 occupancy_id 역할)
    
    -- 유닛 정보
    unit_code           TEXT,                                    -- 공고 내 유닛 구분 코드
    unit_type           unit_type DEFAULT 'other',
    tenure              unit_tenure DEFAULT 'other',
    
    -- 가격 정보
    deposit             NUMERIC(14,2),
    rent                NUMERIC(14,2),
    maintenance_fee     NUMERIC(14,2),
    
    -- 공간 정보
    area_m2             NUMERIC(10,2),
    room_count          INTEGER,
    bathroom_count      INTEGER,
    floor               INTEGER,
    direction           TEXT,
    
    -- 입주 정보
    occupancy_available_at TIMESTAMPTZ,
    
    -- 메타데이터
    unit_extra          JSONB DEFAULT '{}'::jsonb,
    created_at          TIMESTAMPTZ DEFAULT now(),
    updated_at          TIMESTAMPTZ DEFAULT now(),
    
    -- 제약조건
    UNIQUE (crawler_id),                                         -- 크롤러 ID 고유성
    UNIQUE (space_id)                                            -- 물리적 공간 ID 고유성 (NULL 허용)
);

-- 4) 첨부파일 테이블 (ID 구조 단순화)
CREATE TABLE IF NOT EXISTS attachments (
    id              BIGSERIAL PRIMARY KEY,                        -- DB 내부 ID
    notice_id       BIGINT NOT NULL REFERENCES notices(id) ON DELETE CASCADE,
    unit_id         BIGINT REFERENCES units(id) ON DELETE CASCADE, -- NULL 허용
    
    -- 크롤러 ID (단일화)
    crawler_id      TEXT NOT NULL,                               -- 크롤러에서 생성한 고유 ID
    
    -- 파일 정보
    role            attachment_role NOT NULL,
    file_name       TEXT,
    file_ext        TEXT,
    mime_type       TEXT,
    file_size       BIGINT,
    source_url      TEXT,
    sha256          TEXT,
    storage_path    TEXT,
    width_px        INTEGER,
    height_px       INTEGER,
    
    -- 메타데이터
    meta_extra      JSONB DEFAULT '{}'::jsonb,
    created_at      TIMESTAMPTZ DEFAULT now(),
    
    -- 제약조건
    UNIQUE (crawler_id),                                         -- 크롤러 ID 고유성
    UNIQUE (notice_id, sha256)                                   -- 공고 내 파일 중복 방지
);

-- 5) 이미지 테이블 (ID 구조 단순화)
CREATE TABLE IF NOT EXISTS images (
    id              BIGSERIAL PRIMARY KEY,                        -- DB 내부 ID
    attachment_id   BIGINT NOT NULL UNIQUE REFERENCES attachments(id) ON DELETE CASCADE,
    
    -- 크롤러 ID (단일화)
    crawler_id      TEXT NOT NULL,                               -- 크롤러에서 생성한 고유 ID
    
    -- 이미지 정보
    is_primary      BOOLEAN DEFAULT FALSE,
    caption         TEXT,
    exif            JSONB DEFAULT '{}'::jsonb,
    created_at      TIMESTAMPTZ DEFAULT now(),
    
    -- 제약조건
    UNIQUE (crawler_id)                                          -- 크롤러 ID 고유성
);

-- ===========================================
-- 인덱스 최적화
-- ===========================================

-- 크롤러 ID 기반 인덱스 (빠른 조회)
CREATE INDEX IF NOT EXISTS idx_notices_crawler_id ON notices(crawler_id);
CREATE INDEX IF NOT EXISTS idx_units_crawler_id ON units(crawler_id);
CREATE INDEX IF NOT EXISTS idx_attachments_crawler_id ON attachments(crawler_id);
CREATE INDEX IF NOT EXISTS idx_images_crawler_id ON images(crawler_id);

-- 물리적 공간 ID 기반 인덱스 (중복 제거용)
CREATE INDEX IF NOT EXISTS idx_units_space_id ON units(space_id) WHERE space_id IS NOT NULL;

-- 플랫폼 키 기반 인덱스 (플랫폼 내 중복 방지)
CREATE INDEX IF NOT EXISTS idx_notices_platform_key ON notices(platform_id, platform_key);

-- ===========================================
-- 크롤러 ID 생성 함수
-- ===========================================

-- 크롤러 ID 생성 함수 (안정적이고 고유한 ID)
CREATE OR REPLACE FUNCTION generate_crawler_id(
    platform_code TEXT,
    platform_key TEXT,
    object_type TEXT DEFAULT 'notice',
    object_index INTEGER DEFAULT 0
) RETURNS TEXT AS $$
BEGIN
    -- 안정적인 크롤러 ID 생성
    -- 형식: {platform_code}_{object_type}_{hash}_{index}
    RETURN platform_code || '_' || object_type || '_' || 
           encode(digest(platform_code || '|' || platform_key || '|' || object_type, 'sha256'), 'hex')[:8] ||
           CASE WHEN object_index > 0 THEN '_' || object_index::TEXT ELSE '' END;
END;
$$ LANGUAGE plpgsql;

-- 물리적 공간 ID 생성 함수
CREATE OR REPLACE FUNCTION generate_space_id(
    address TEXT,
    floor TEXT,
    room_number TEXT,
    building_name TEXT DEFAULT ''
) RETURNS TEXT AS $$
BEGIN
    -- 물리적 공간 ID 생성 (주소+층+호수 기반)
    RETURN 'space_' || 
           encode(digest(
               COALESCE(address, '') || '|' || 
               COALESCE(floor, '') || '|' || 
               COALESCE(room_number, '') || '|' || 
               COALESCE(building_name, ''), 
               'sha256'
           ), 'hex')[:12];
END;
$$ LANGUAGE plpgsql;
