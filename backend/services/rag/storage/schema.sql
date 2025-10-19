-- ============================================================================
-- RAG Vector Store Schema (pgvector)
-- 임베딩 모델별로 벡터를 저장하고 비교할 수 있는 구조
-- ============================================================================

-- pgvector 확장 활성화
CREATE EXTENSION IF NOT EXISTS vector;

-- vector_db 스키마 생성
CREATE SCHEMA IF NOT EXISTS vector_db;

-- ============================================================================
-- 1. 임베딩 모델 테이블 (vector_db 스키마)
-- ============================================================================
CREATE TABLE IF NOT EXISTS vector_db.embedding_models (
    id SERIAL PRIMARY KEY,
    model_name VARCHAR(255) UNIQUE NOT NULL,  -- 예: "intfloat/multilingual-e5-small"
    display_name VARCHAR(255) NOT NULL,       -- 예: "E5-Small (Multilingual)"
    dimension INTEGER NOT NULL,               -- 임베딩 차원
    max_seq_length INTEGER NOT NULL,          -- 최대 시퀀스 길이
    pooling_mode VARCHAR(50),                 -- 'mean', 'cls', 'max'
    normalize_embeddings BOOLEAN DEFAULT TRUE,
    notes TEXT,                               -- 모델 설명
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 모델 이름 인덱스
CREATE INDEX IF NOT EXISTS idx_embedding_models_name ON vector_db.embedding_models(model_name);

-- ============================================================================
-- 2. 문서 소스 테이블 (원본 데이터) - vector_db 스키마
-- ============================================================================
CREATE TABLE IF NOT EXISTS vector_db.document_sources (
    id SERIAL PRIMARY KEY,
    source_type VARCHAR(50) NOT NULL,         -- 'housing', 'infra', 'rtms', 'pdf'
    source_id VARCHAR(255),                   -- 원본 데이터의 ID (예: notice_id)
    file_path TEXT,                           -- PDF 경로 등
    metadata JSONB,                           -- 추가 메타데이터
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- 소스 타입 인덱스
CREATE INDEX IF NOT EXISTS idx_document_sources_type ON vector_db.document_sources(source_type);
CREATE INDEX IF NOT EXISTS idx_document_sources_source_id ON vector_db.document_sources(source_id);

-- ============================================================================
-- 3. 문서 청크 테이블 (분할된 텍스트) - vector_db 스키마
-- ============================================================================
CREATE TABLE IF NOT EXISTS vector_db.document_chunks (
    id SERIAL PRIMARY KEY,
    source_id INTEGER REFERENCES vector_db.document_sources(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,             -- 청크 순서
    content TEXT NOT NULL,                    -- 청크 텍스트
    chunk_type VARCHAR(50),                   -- 'text', 'table', 'header' 등
    token_count INTEGER,                      -- 토큰 수
    metadata JSONB,                           -- 추가 메타데이터 (위치, 페이지 등)
    created_at TIMESTAMP DEFAULT NOW(),

    -- 하나의 소스에서 청크 인덱스는 유일
    UNIQUE(source_id, chunk_index)
);

-- 청크 검색 인덱스
CREATE INDEX IF NOT EXISTS idx_document_chunks_source ON vector_db.document_chunks(source_id);
CREATE INDEX IF NOT EXISTS idx_document_chunks_type ON vector_db.document_chunks(chunk_type);

-- 전문 검색 (PostgreSQL FTS) - 한국어 설정이 없으면 기본 설정 사용
CREATE INDEX IF NOT EXISTS idx_document_chunks_content_fts ON vector_db.document_chunks
USING GIN (to_tsvector('simple', content));

-- ============================================================================
-- 4. 벡터 임베딩 테이블 (모델별로 분리) - vector_db 스키마
-- ============================================================================

-- 4.1 E5-Small 임베딩 테이블 (384차원)
CREATE TABLE IF NOT EXISTS vector_db.embeddings_e5_small (
    id SERIAL PRIMARY KEY,
    chunk_id INTEGER REFERENCES vector_db.document_chunks(id) ON DELETE CASCADE,
    embedding vector(384) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(chunk_id)
);

CREATE INDEX IF NOT EXISTS idx_embeddings_e5_small_chunk ON vector_db.embeddings_e5_small(chunk_id);

-- 4.2 KakaoBank DeBERTa 임베딩 테이블 (768차원)
CREATE TABLE IF NOT EXISTS vector_db.embeddings_kakaobank (
    id SERIAL PRIMARY KEY,
    chunk_id INTEGER REFERENCES vector_db.document_chunks(id) ON DELETE CASCADE,
    embedding vector(768) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(chunk_id)
);

CREATE INDEX IF NOT EXISTS idx_embeddings_kakaobank_chunk ON vector_db.embeddings_kakaobank(chunk_id);

-- 4.3 Qwen3 Embedding 임베딩 테이블 (1024차원)
CREATE TABLE IF NOT EXISTS vector_db.embeddings_qwen3 (
    id SERIAL PRIMARY KEY,
    chunk_id INTEGER REFERENCES vector_db.document_chunks(id) ON DELETE CASCADE,
    embedding vector(1024) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(chunk_id)
);

CREATE INDEX IF NOT EXISTS idx_embeddings_qwen3_chunk ON vector_db.embeddings_qwen3(chunk_id);

-- 4.4 EmbeddingGemma 임베딩 테이블 (768차원)
CREATE TABLE IF NOT EXISTS vector_db.embeddings_gemma (
    id SERIAL PRIMARY KEY,
    chunk_id INTEGER REFERENCES vector_db.document_chunks(id) ON DELETE CASCADE,
    embedding vector(768) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(chunk_id)
);

CREATE INDEX IF NOT EXISTS idx_embeddings_gemma_chunk ON vector_db.embeddings_gemma(chunk_id);


-- ============================================================================
-- 5. 벡터 유사도 검색 인덱스 (HNSW - 모델별로 생성)
-- ============================================================================
-- HNSW 인덱스: IVFFlat보다 빠르고 정확함
-- lists 파라미터 대신 m, ef_construction 파라미터 사용

-- 5.1 E5-Small HNSW 인덱스
CREATE INDEX IF NOT EXISTS idx_embeddings_e5_small_hnsw
ON vector_db.embeddings_e5_small
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- 5.2 KakaoBank HNSW 인덱스
CREATE INDEX IF NOT EXISTS idx_embeddings_kakaobank_hnsw
ON vector_db.embeddings_kakaobank
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- 5.3 Qwen3 HNSW 인덱스
CREATE INDEX IF NOT EXISTS idx_embeddings_qwen3_hnsw
ON vector_db.embeddings_qwen3
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- 5.4 Gemma HNSW 인덱스
CREATE INDEX IF NOT EXISTS idx_embeddings_gemma_hnsw
ON vector_db.embeddings_gemma
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- 인덱스 없이 사용

-- ============================================================================
-- 6. 검색 로그 테이블 (모델 성능 비교용) - vector_db 스키마
-- ============================================================================
CREATE TABLE IF NOT EXISTS vector_db.search_logs (
    id SERIAL PRIMARY KEY,
    model_id INTEGER REFERENCES vector_db.embedding_models(id),
    query TEXT NOT NULL,                      -- 검색 쿼리
    query_embedding vector,                   -- 쿼리 임베딩
    top_k INTEGER DEFAULT 5,                  -- 검색 개수
    search_time_ms NUMERIC(10, 2),            -- 검색 시간 (밀리초)
    results JSONB,                            -- 검색 결과 (chunk_ids, similarities)
    avg_similarity NUMERIC(5, 4),             -- 평균 유사도
    created_at TIMESTAMP DEFAULT NOW()
);

-- 검색 로그 인덱스
CREATE INDEX IF NOT EXISTS idx_search_logs_model ON vector_db.search_logs(model_id);
CREATE INDEX IF NOT EXISTS idx_search_logs_created ON vector_db.search_logs(created_at);

-- ============================================================================
-- 7. 모델 성능 메트릭 테이블 - vector_db 스키마
-- ============================================================================
CREATE TABLE IF NOT EXISTS vector_db.model_metrics (
    id SERIAL PRIMARY KEY,
    model_id INTEGER REFERENCES vector_db.embedding_models(id) ON DELETE CASCADE,
    metric_date DATE DEFAULT CURRENT_DATE,

    -- 성능 지표
    total_searches INTEGER DEFAULT 0,
    avg_search_time_ms NUMERIC(10, 2),
    avg_top1_similarity NUMERIC(5, 4),
    avg_top3_similarity NUMERIC(5, 4),
    avg_top5_similarity NUMERIC(5, 4),

    -- 메타정보
    total_embeddings INTEGER,                 -- 저장된 임베딩 수
    storage_size_mb NUMERIC(10, 2),           -- 저장 공간

    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    -- 날짜별로 유일
    UNIQUE(model_id, metric_date)
);

-- ============================================================================
-- 8. 유틸리티 함수들
-- ============================================================================

-- 8.1 코사인 유사도 함수
CREATE OR REPLACE FUNCTION cosine_similarity(a vector, b vector)
RETURNS NUMERIC AS $$
    SELECT 1 - (a <=> b);  -- pgvector의 코사인 거리를 유사도로 변환
$$ LANGUAGE SQL IMMUTABLE STRICT;

-- 8.2 벡터 검색 함수 (모델별 테이블에서 검색)
CREATE OR REPLACE FUNCTION search_similar_chunks(
    query_embedding vector,
    model_name_param VARCHAR,
    top_k_param INTEGER DEFAULT 5,
    min_similarity NUMERIC DEFAULT 0.0
)
RETURNS TABLE (
    chunk_id INTEGER,
    content TEXT,
    similarity NUMERIC,
    metadata JSONB
) AS $$
BEGIN
    -- 모델별로 적절한 테이블에서 검색
    CASE model_name_param
        WHEN 'intfloat/multilingual-e5-small' THEN
            RETURN QUERY
            SELECT dc.id, dc.content,
                   cosine_similarity(e.embedding, query_embedding) as sim,
                   dc.metadata
            FROM vector_db.embeddings_e5_small e
            JOIN vector_db.document_chunks dc ON e.chunk_id = dc.id
            WHERE cosine_similarity(e.embedding, query_embedding) >= min_similarity
            ORDER BY e.embedding <=> query_embedding
            LIMIT top_k_param;

        WHEN 'kakaobank/kf-deberta-base' THEN
            RETURN QUERY
            SELECT dc.id, dc.content,
                   cosine_similarity(e.embedding, query_embedding) as sim,
                   dc.metadata
            FROM vector_db.embeddings_kakaobank e
            JOIN vector_db.document_chunks dc ON e.chunk_id = dc.id
            WHERE cosine_similarity(e.embedding, query_embedding) >= min_similarity
            ORDER BY e.embedding <=> query_embedding
            LIMIT top_k_param;

        WHEN 'Qwen/Qwen3-Embedding-0.6B' THEN
            RETURN QUERY
            SELECT dc.id, dc.content,
                   cosine_similarity(e.embedding, query_embedding) as sim,
                   dc.metadata
            FROM vector_db.embeddings_qwen3 e
            JOIN vector_db.document_chunks dc ON e.chunk_id = dc.id
            WHERE cosine_similarity(e.embedding, query_embedding) >= min_similarity
            ORDER BY e.embedding <=> query_embedding
            LIMIT top_k_param;

        WHEN 'google/embeddinggemma-300m' THEN
            RETURN QUERY
            SELECT dc.id, dc.content,
                   cosine_similarity(e.embedding, query_embedding) as sim,
                   dc.metadata
            FROM vector_db.embeddings_gemma e
            JOIN vector_db.document_chunks dc ON e.chunk_id = dc.id
            WHERE cosine_similarity(e.embedding, query_embedding) >= min_similarity
            ORDER BY e.embedding <=> query_embedding
            LIMIT top_k_param;


        ELSE
            RAISE EXCEPTION 'Unknown model: %', model_name_param;
    END CASE;
END;
$$ LANGUAGE plpgsql;

-- 8.4 타임스탬프 자동 업데이트 트리거 함수
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 트리거 생성 (조건부)
DO $$
BEGIN
    -- embedding_models 트리거
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'update_embedding_models_updated_at') THEN
        CREATE TRIGGER update_embedding_models_updated_at
            BEFORE UPDATE ON vector_db.embedding_models
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
    END IF;

    -- document_sources 트리거
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'update_document_sources_updated_at') THEN
        CREATE TRIGGER update_document_sources_updated_at
            BEFORE UPDATE ON vector_db.document_sources
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
    END IF;

    -- model_metrics 트리거
    IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'update_model_metrics_updated_at') THEN
        CREATE TRIGGER update_model_metrics_updated_at
            BEFORE UPDATE ON vector_db.model_metrics
            FOR EACH ROW
            EXECUTE FUNCTION update_updated_at_column();
    END IF;
END $$;

-- ============================================================================
-- 9. 초기 데이터 삽입 (5가지 모델)
-- ============================================================================

INSERT INTO vector_db.embedding_models (model_name, display_name, dimension, max_seq_length, pooling_mode, notes)
VALUES
    ('intfloat/multilingual-e5-small', 'E5-Small (Multilingual)', 384, 512, 'mean', '경량 모델, 빠른 추론 속도, 다국어 지원'),
    ('kakaobank/kf-deberta-base', 'KakaoBank DeBERTa', 768, 512, 'mean', '한국어 금융 데이터 특화, 높은 한국어 이해도'),
    ('Qwen/Qwen3-Embedding-0.6B', 'Qwen3 Embedding 0.6B', 1024, 32768, 'last_token', '대규모 모델, 긴 문맥 처리 가능, 고품질 임베딩'),
    ('google/embeddinggemma-300m', 'EmbeddingGemma 300M', 768, 2048, 'mean', 'Google Gemma 기반, 균형잡힌 성능'),
ON CONFLICT (model_name) DO UPDATE SET
    display_name = EXCLUDED.display_name,
    dimension = EXCLUDED.dimension,
    max_seq_length = EXCLUDED.max_seq_length,
    pooling_mode = EXCLUDED.pooling_mode,
    notes = EXCLUDED.notes,
    updated_at = NOW();

-- ============================================================================
-- 10. 유용한 쿼리 예시 (주석)
-- ============================================================================

/*
-- 10.1 모델별 임베딩 개수 확인
SELECT
    em.display_name,
    COUNT(ce.id) as embedding_count,
    em.dimension
FROM vector_db.embedding_models em
LEFT JOIN chunk_embeddings ce ON em.id = ce.model_id
GROUP BY em.id, em.display_name, em.dimension
ORDER BY embedding_count DESC;

-- 10.2 특정 모델로 유사도 검색
SELECT * FROM search_similar_chunks(
    '[0.1, 0.2, ..., 0.3]'::vector,  -- 쿼리 임베딩
    'intfloat/multilingual-e5-small',
    5,     -- top_k
    0.5    -- min_similarity
);

-- 10.3 모델별 평균 검색 시간 비교
SELECT
    em.display_name,
    AVG(sl.search_time_ms) as avg_time_ms,
    AVG(sl.avg_similarity) as avg_similarity,
    COUNT(sl.id) as total_searches
FROM vector_db.search_logs sl
JOIN vector_db.embedding_models em ON sl.model_id = em.id
WHERE sl.created_at >= NOW() - INTERVAL '7 days'
GROUP BY em.id, em.display_name
ORDER BY avg_similarity DESC;

-- 10.4 특정 소스의 모든 청크와 임베딩 조회
SELECT
    dc.id as chunk_id,
    dc.content,
    em.display_name as model_name,
    ce.embedding
FROM vector_db.document_chunks dc
JOIN vector_db.chunk_embeddings ce ON dc.id = ce.chunk_id
JOIN vector_db.embedding_models em ON ce.model_id = em.id
WHERE dc.source_id = 1
ORDER BY dc.chunk_index, em.id;

-- 10.5 벡터 인덱스 생성 (모든 모델)
SELECT create_vector_index_for_model(model_name, 100)
FROM embedding_models;

-- 10.6 저장 공간 확인
SELECT
    em.display_name,
    pg_size_pretty(pg_total_relation_size('chunk_embeddings')) as total_size,
    COUNT(ce.id) as embedding_count
FROM vector_db.embedding_models em
LEFT JOIN chunk_embeddings ce ON em.id = ce.model_id
GROUP BY em.id, em.display_name;
*/
