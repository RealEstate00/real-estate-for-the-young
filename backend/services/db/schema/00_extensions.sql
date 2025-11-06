-- =====================================================================
-- PostgreSQL Extensions
-- =====================================================================
-- pgvector extension for vector similarity search
CREATE EXTENSION IF NOT EXISTS vector;

-- 기타 필요한 extension들
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
