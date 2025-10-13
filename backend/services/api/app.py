from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import routers
from backend.services.api.routers.llm import router as llm_router

app = FastAPI(
    title="Real Estate for the Young API",
    description="청년을 위한 부동산 정보 API",
    version="0.1.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # React 개발 서버
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(llm_router)  # LLM 라우터 추가

@app.get("/")
async def root():
    return {
        "message": "Real Estate for the Young API",
        "docs": "/docs"
    }