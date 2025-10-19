-- ============================================================================
-- 기존 housing 스키마의 벡터 테이블을 vector_db 스키마로 이동
-- ============================================================================

-- 1. vector_db 스키마 생성
CREATE SCHEMA IF NOT EXISTS vector_db;

-- 2. 기존 테이블들을 vector_db 스키마로 이동
-- (테이블 이름이 같으므로 ALTER SCHEMA 사용)

-- 임베딩 모델 테이블 이동
ALTER TABLE housing.embedding_models SET SCHEMA vector_db;

-- 문서 소스 테이블 이동
ALTER TABLE housing.document_sources SET SCHEMA vector_db;

-- 문서 청크 테이블 이동
ALTER TABLE housing.document_chunks SET SCHEMA vector_db;

-- 청크 임베딩 테이블 이동
ALTER TABLE housing.chunk_embeddings SET SCHEMA vector_db;

-- 검색 로그 테이블 이동 (존재하는 경우)
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'housing' AND table_name = 'search_logs') THEN
        ALTER TABLE housing.search_logs SET SCHEMA vector_db;
    END IF;
END $$;

-- 모델 메트릭 테이블 이동 (존재하는 경우)
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'housing' AND table_name = 'model_metrics') THEN
        ALTER TABLE housing.model_metrics SET SCHEMA vector_db;
    END IF;
END $$;

-- 3. 인덱스들 재생성 (스키마 변경으로 인해 인덱스가 사라질 수 있음)

-- 임베딩 모델 인덱스
CREATE INDEX IF NOT EXISTS idx_embedding_models_name ON vector_db.embedding_models(model_name);

-- 문서 소스 인덱스
CREATE INDEX IF NOT EXISTS idx_document_sources_type ON vector_db.document_sources(source_type);
CREATE INDEX IF NOT EXISTS idx_document_sources_source_id ON vector_db.document_sources(source_id);

-- 문서 청크 인덱스
CREATE INDEX IF NOT EXISTS idx_document_chunks_source ON vector_db.document_chunks(source_id);
CREATE INDEX IF NOT EXISTS idx_document_chunks_type ON vector_db.document_chunks(chunk_type);
CREATE INDEX IF NOT EXISTS idx_document_chunks_content_fts ON vector_db.document_chunks
USING GIN (to_tsvector('simple', content));

-- 청크 임베딩 인덱스
CREATE INDEX IF NOT EXISTS idx_chunk_embeddings_chunk ON vector_db.chunk_embeddings(chunk_id);
CREATE INDEX IF NOT EXISTS idx_chunk_embeddings_model ON vector_db.chunk_embeddings(model_id);

-- 4. 벡터 인덱스 재생성 (E5-Small 모델용)
-- 기존 모델 ID 확인
DO $$
DECLARE
    model_id_var INTEGER;
BEGIN
    SELECT id INTO model_id_var
    FROM vector_db.embedding_models
    WHERE model_name = 'intfloat/multilingual-e5-small';
    
    IF model_id_var IS NOT NULL THEN
        EXECUTE format(
            'CREATE INDEX IF NOT EXISTS idx_embeddings_%s_cosine ON vector_db.chunk_embeddings
             USING ivfflat (embedding vector_cosine_ops)
             WHERE model_id = %s
             WITH (lists = 100)',
            model_id_var,
            model_id_var
        );
        RAISE NOTICE 'Created vector index for model ID: %', model_id_var;
    END IF;
END $$;

-- 5. 확인 쿼리
SELECT 
    'Migration completed successfully' as status,
    (SELECT COUNT(*) FROM vector_db.embedding_models) as models_count,
    (SELECT COUNT(*) FROM vector_db.document_sources) as sources_count,
    (SELECT COUNT(*) FROM vector_db.document_chunks) as chunks_count,
    (SELECT COUNT(*) FROM vector_db.chunk_embeddings) as embeddings_count;
