# 🏠 Real Estate for the Young

청년을 위한 서울시 주택 정보 검색 및 추천 시스템

## 🚀 빠른 시작

### 1. 환경 설정

```bash
# 의존성 설치 및 환경 설정
python setup.py
```

### 2. API 키 설정

`.env` 파일에서 다음 API 키를 설정하세요:

```bash
GROQ_API_KEY=your_groq_api_key_here  # 필수
OPENAI_API_KEY=your_openai_api_key_here  # 선택사항
```

### 3. 개발 서버 실행

```bash
# 개별 실행 (권장)
python -m backend.services.api.cli    # API 서버만 (http://localhost:8000)
python -m frontend.react.cli          # Frontend만 (http://localhost:3000)
python dev.py                         # API + Frontend 동시 실행

# 또는 pip 설치 후
pip install -e .
api                                   # API 서버만
react                                 # Frontend만
dev                                   # API + Frontend 동시 실행
```

### 4. 접속

- **Frontend**: http://localhost:3000
- **API**: http://localhost:8000
- **API 문서**: http://localhost:8000/docs

## 📋 CLI 명령어

### 데이터베이스 관리

```bash
python cli.py db create    # 테이블 생성
python cli.py db drop      # 테이블 삭제
python cli.py db reset     # 데이터베이스 초기화
python cli.py db list      # 테이블 목록
python cli.py db test      # 연결 테스트
```

### 데이터 로드

```bash
python cli.py load housing  # 주택 데이터 로드
python cli.py load infra    # 공공시설 데이터 로드
python cli.py load rtms     # 실거래 데이터 로드
python cli.py load all      # 모든 데이터 로드
```

## 🏗️ 프로젝트 구조

```
├── backend/                 # 백엔드 API 서버
│   ├── services/
│   │   ├── api/            # FastAPI 라우터
│   │   ├── llm/            # LLM 관련 (LangChain)
│   │   ├── vector_db/      # 벡터 데이터베이스
│   │   └── data_collection/ # 데이터 수집
│   └── data/               # 데이터 저장소
├── frontend/               # 프론트엔드
│   └── react/              # React 프론트엔드
│       ├── src/
│       │   ├── components/ # React 컴포넌트
│       │   └── services/   # API 클라이언트
│       ├── cli/            # React CLI
│       └── package.json
├── backend/services/api/cli/    # API 서버 CLI
├── frontend/react/cli/          # React 개발 서버 CLI
├── dev.py                 # 개발 모드 실행 스크립트
├── setup.py               # 환경 설정 스크립트
└── .env                   # 환경 변수 (생성 필요)
```

## 🤖 AI 기능

### 지원 모델

- **Groq**: Llama 3.3-70b-versatile (기본)
- **OpenAI**: GPT-4o-mini (선택사항)
- **HuggingFace**: 로컬 모델 (선택사항)

### RAG 시스템

- **벡터 검색**: ChromaDB + 한국어 임베딩
- **Agent 모드**: 도구 사용 가능한 AI 어시스턴트
- **하이브리드 모드**: Agent LLM + Response LLM 분리

## 🔧 개발

### 환경 변수

```bash
# LLM 설정
FORCE_LLM_PROVIDER=groq
USE_HYBRID_LLM=False
GROQ_API_KEY=your_key
OPENAI_API_KEY=your_key

# 데이터베이스
PG_HOST=localhost
PG_PORT=5432
PG_USER=postgres
PG_PASSWORD=post1234
PG_DB=rey
```

### API 엔드포인트

- `GET /api/llm/health` - 서비스 상태 확인
- `POST /api/llm/ask` - 질문 답변 (RAG Chain)
- `POST /api/llm/ask-agent` - 질문 답변 (Agent)
- `POST /api/llm/chat` - 대화형 채팅
- `POST /api/llm/clear-memory` - 대화 기록 초기화

## 📝 라이선스

MIT License

## 🤝 기여

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request
