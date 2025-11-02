# 연결 상태 확인 가이드

## 전체 연결 체인

```
프론트엔드 (localhost:3000)
    ↓ HTTP POST /api/llm/ask-agent
API 서버 (localhost:8000, Docker)
    ↓ 1. 데이터베이스 연결
PostgreSQL (Docker)
    ↓ 2. 검색 + RAG 파이프라인
벡터 검색 → 증강 → 생성
    ↓ 3. LLM 연결
Ollama (host.docker.internal:11434)
```

## 연결 확인 방법

### 1. API 서버 상태 확인

```bash
curl http://localhost:8000/api/llm/health
```

**예상 응답:**

```json
{ "status": "healthy", "service": "LLM API" }
```

### 2. 데이터베이스 연결 확인

```bash
docker exec seoul_housing_api python3 -c "
from backend.services.api.routers.llm import get_rag_system
rag = get_rag_system()
rag.retriever.vector_store.connect()
print('✅ DB 연결 성공')
"
```

### 3. Ollama 연결 확인

```bash
# 로컬에서
curl http://localhost:11434/api/tags

# 컨테이너에서
docker exec seoul_housing_api curl http://host.docker.internal:11434/api/tags
```

### 4. 전체 파이프라인 테스트

```bash
curl -X POST http://localhost:8000/api/llm/ask-agent \
  -H "Content-Type: application/json" \
  -d '{
    "question": "청년 월세 지원금",
    "model_type": "ollama",
    "with_memory": false
  }'
```

### 5. 프론트엔드에서 API 호출 확인

브라우저 개발자 도구 (F12):

- Network 탭에서 `/api/llm/ask-agent` 요청 확인
- Console 탭에서 오류 확인

## 일반적인 오류와 해결

### "Load failed" 오류

1. **API 서버가 실행되지 않음**

   ```bash
   docker-compose -f docker-compose.dev.yml ps api
   docker-compose -f docker-compose.dev.yml restart api
   ```

2. **CORS 오류**

   - `backend/services/api/app.py`의 CORS 설정 확인
   - 개발 환경에서는 `allow_origins=["*"]` 설정됨

3. **네트워크 연결 오류**

   - API URL 확인: `http://localhost:8000`
   - 프론트엔드에서 `llmApi.ts`의 `API_URL` 확인

4. **타임아웃 오류**
   - Ollama 서버 실행 확인
   - 데이터베이스 연결 확인

## 연결 체인별 확인

### ✅ 정상 연결 예시

```bash
# 1. API Health
curl http://localhost:8000/api/llm/health
# → {"status":"healthy","service":"LLM API"}

# 2. 전체 파이프라인
curl -X POST http://localhost:8000/api/llm/ask-agent \
  -H "Content-Type: application/json" \
  -d '{"question": "테스트", "model_type": "ollama"}'
# → {"message": "...", "sources": [...]}
```

### ❌ 오류 예시

```bash
# 연결 실패
curl: (7) Failed to connect to localhost port 8000
# → API 서버가 실행되지 않음

# 500 에러
{"detail": "..."}
# → API 로그 확인 필요

# 타임아웃
{"message": "답변 생성 시간이 초과되었습니다..."}
# → Ollama 서버 확인 필요
```
