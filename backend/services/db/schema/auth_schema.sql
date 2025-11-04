-- =====================================================================
-- Auth Schema (사용자 인증 및 대화 관리)
-- =====================================================================

-- 1. auth 스키마 생성
CREATE SCHEMA IF NOT EXISTS auth;

-- 스키마 경로 설정 (다른 스키마 파일들과 일관성 유지)
SET search_path TO auth, public;

-- 2. Users 테이블
DROP TABLE IF EXISTS auth.users CASCADE;
CREATE TABLE auth.users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    username VARCHAR(100) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,
    last_login TIMESTAMPTZ,
    full_name VARCHAR(200),
    is_active BOOLEAN DEFAULT TRUE,
    is_staff BOOLEAN DEFAULT FALSE,
    is_superuser BOOLEAN DEFAULT FALSE,
    is_verified BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    CONSTRAINT ck_email_format CHECK (email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$')
);

-- 이메일과 username에 인덱스 추가 (검색 성능 향상)
CREATE INDEX idx_users_email ON auth.users(email);
CREATE INDEX idx_users_username ON auth.users(username);
CREATE INDEX idx_users_created_at ON auth.users(created_at DESC);

-- 3. Conversations 테이블
DROP TABLE IF EXISTS auth.conversations CASCADE;
CREATE TABLE auth.conversations (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    title VARCHAR(255) NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    CONSTRAINT ck_title_not_empty CHECK (char_length(title) > 0)
);

-- user_id와 updated_at에 인덱스 추가 (사용자별 대화 목록 조회 최적화)
CREATE INDEX idx_conversations_user_id ON auth.conversations(user_id);
CREATE INDEX idx_conversations_updated_at ON auth.conversations(updated_at DESC);
CREATE INDEX idx_conversations_user_updated ON auth.conversations(user_id, updated_at DESC);

-- 4. Messages 테이블
DROP TABLE IF EXISTS auth.messages CASCADE;
CREATE TABLE auth.messages (
    id SERIAL PRIMARY KEY,
    conversation_id INTEGER NOT NULL REFERENCES auth.conversations(id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now(),
    CONSTRAINT ck_content_not_empty CHECK (char_length(content) > 0)
);

-- conversation_id와 created_at에 인덱스 추가 (대화 메시지 조회 최적화)
CREATE INDEX idx_messages_conversation_id ON auth.messages(conversation_id);
CREATE INDEX idx_messages_created_at ON auth.messages(created_at);
CREATE INDEX idx_messages_conversation_created ON auth.messages(conversation_id, created_at);

-- 5. Updated_at 자동 업데이트 트리거 함수
CREATE OR REPLACE FUNCTION auth.update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Users 테이블에 트리거 적용
DROP TRIGGER IF EXISTS update_users_updated_at ON auth.users;
CREATE TRIGGER update_users_updated_at
    BEFORE UPDATE ON auth.users
    FOR EACH ROW
    EXECUTE FUNCTION auth.update_updated_at_column();

-- Conversations 테이블에 트리거 적용
DROP TRIGGER IF EXISTS update_conversations_updated_at ON auth.conversations;
CREATE TRIGGER update_conversations_updated_at
    BEFORE UPDATE ON auth.conversations
    FOR EACH ROW
    EXECUTE FUNCTION auth.update_updated_at_column();

-- 6. Messages 추가 시 Conversation의 updated_at 자동 업데이트 트리거
CREATE OR REPLACE FUNCTION auth.update_conversation_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE auth.conversations
    SET updated_at = now()
    WHERE id = NEW.conversation_id;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS update_conversation_on_message ON auth.messages;
CREATE TRIGGER update_conversation_on_message
    AFTER INSERT ON auth.messages
    FOR EACH ROW
    EXECUTE FUNCTION auth.update_conversation_timestamp();

-- 7. 코멘트 추가 (테이블 설명)
COMMENT ON TABLE auth.users IS '사용자 정보 테이블';
COMMENT ON TABLE auth.conversations IS '사용자별 대화 목록 테이블';
COMMENT ON TABLE auth.messages IS '대화의 개별 메시지 테이블';

COMMENT ON COLUMN auth.users.email IS '사용자 이메일 (로그인 ID)';
COMMENT ON COLUMN auth.users.password IS 'bcrypt로 해싱된 비밀번호';
COMMENT ON COLUMN auth.users.is_active IS '계정 활성화 여부';
COMMENT ON COLUMN auth.users.is_verified IS '이메일 인증 여부';

COMMENT ON COLUMN auth.conversations.title IS '대화 제목 (첫 질문 기반 자동 생성)';
COMMENT ON COLUMN auth.messages.role IS '메시지 역할 (user, assistant, system)';
COMMENT ON COLUMN auth.messages.content IS '메시지 내용';
