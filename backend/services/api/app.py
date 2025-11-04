from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
from typing import List

# Import routers
from backend.services.api.routers.llm import router as llm_router
from backend.services.api.routers.streaming import router as streaming_router
from backend.services.api.routers.auth import router as auth_router
from backend.services.api.routers.conversation import router as conversation_router

app = FastAPI(
    title="Real Estate for the Young API",
    description="청년을 위한 주택 안내 API",
    version="0.1.0"
)

# CORS middleware

# 개발 환경에서는 모든 origin 허용, 프로덕션에서는 특정 origin만 허용
cors_origins_env = os.getenv("CORS_ORIGINS", "")
is_development = os.getenv("ENV", "development") == "development"

if is_development:
    # 개발 환경: 모든 origin 허용 (allow_credentials는 False로)
    allowed_origins = ["*"]
    allow_credentials = False
else:
    # 프로덕션: 환경 변수로 지정된 origin만 허용
    if cors_origins_env:
        allowed_origins = [origin.strip() for origin in cors_origins_env.split(",")]
    else:
        allowed_origins = ["http://localhost:3000"]
    allow_credentials = True

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(auth_router)  # 인증 라우터 추가
app.include_router(conversation_router)  # 대화 관리 라우터 추가
app.include_router(llm_router)  # LLM 라우터 추가
app.include_router(streaming_router)  # 스트리밍 라우터 추가

@app.get("/")
async def root():
    return {
        "message": "Real Estate for the Young API",
        "docs": "/docs"
    }