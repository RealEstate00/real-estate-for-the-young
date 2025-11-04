"""
인증 및 대화 관리 관련 Pydantic 스키마
"""
from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional, List
from datetime import datetime


# ==================== User 관련 스키마 ====================

class UserCreate(BaseModel):
    """회원가입 요청"""
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=100)
    password: str = Field(..., min_length=8, max_length=100)
    full_name: Optional[str] = Field(None, max_length=200)

    @field_validator('username')
    @classmethod
    def username_alphanumeric(cls, v: str) -> str:
        if not v.replace('_', '').replace('-', '').isalnum():
            raise ValueError('Username must contain only alphanumeric characters, hyphens, and underscores')
        return v


class UserLogin(BaseModel):
    """로그인 요청"""
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    """사용자 정보 응답"""
    id: int
    email: str
    username: str
    full_name: Optional[str] = None
    is_active: bool
    is_verified: bool
    created_at: datetime
    last_login_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    """JWT 토큰 응답"""
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class TokenData(BaseModel):
    """JWT 토큰 페이로드"""
    user_id: int
    email: str


# ==================== Message 관련 스키마 ====================

class MessageCreate(BaseModel):
    """메시지 생성 요청"""
    role: str = Field(..., pattern='^(user|assistant|system)$')
    content: str = Field(..., min_length=1)


class MessageResponse(BaseModel):
    """메시지 응답"""
    id: int
    conversation_id: int
    role: str
    content: str
    created_at: datetime

    class Config:
        from_attributes = True


# ==================== Conversation 관련 스키마 ====================

class ConversationCreate(BaseModel):
    """대화 생성 요청"""
    title: str = Field(..., min_length=1, max_length=255)


class ConversationUpdate(BaseModel):
    """대화 업데이트 요청"""
    title: Optional[str] = Field(None, min_length=1, max_length=255)


class ConversationResponse(BaseModel):
    """대화 응답 (메시지 제외)"""
    id: int
    user_id: int
    title: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ConversationWithMessages(ConversationResponse):
    """대화 상세 응답 (메시지 포함)"""
    messages: List[MessageResponse] = []

    class Config:
        from_attributes = True


class ConversationListResponse(BaseModel):
    """대화 목록 응답"""
    conversations: List[ConversationResponse]
    total: int


# ==================== Chat 관련 스키마 (LLM API 연동) ====================

class ChatMessageRequest(BaseModel):
    """채팅 메시지 요청"""
    conversation_id: Optional[int] = None  # 기존 대화 ID (None이면 새 대화 생성)
    message: str = Field(..., min_length=1)
    model_type: str = Field(default="ollama")


class ChatMessageResponse(BaseModel):
    """채팅 메시지 응답"""
    conversation_id: int
    user_message: MessageResponse
    assistant_message: MessageResponse
    sources: Optional[List[dict]] = None
