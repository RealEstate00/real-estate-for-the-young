"""
인증 관련 유틸리티 함수
- 비밀번호 해싱 (bcrypt)
- JWT 토큰 생성 및 검증
"""
import os
from datetime import datetime, timedelta
from typing import Optional
from passlib.context import CryptContext
from jose import JWTError, jwt
from fastapi import HTTPException, status

# 비밀번호 해싱 컨텍스트
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT 설정
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "10080"))  # 기본 7일


def hash_password(password: str) -> str:
    """
    비밀번호를 bcrypt로 해싱

    Args:
        password: 평문 비밀번호

    Returns:
        해싱된 비밀번호
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    비밀번호 검증

    Args:
        plain_password: 평문 비밀번호
        hashed_password: 해싱된 비밀번호

    Returns:
        일치 여부
    """
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    JWT 액세스 토큰 생성

    Args:
        data: 토큰에 포함할 데이터 (user_id, email 등)
        expires_delta: 만료 시간 (기본값: ACCESS_TOKEN_EXPIRE_MINUTES)

    Returns:
        JWT 토큰
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

    return encoded_jwt


def decode_access_token(token: str) -> dict:
    """
    JWT 액세스 토큰 디코딩 및 검증

    Args:
        token: JWT 토큰

    Returns:
        토큰 페이로드 (user_id, email 등)

    Raises:
        HTTPException: 토큰이 유효하지 않거나 만료된 경우
    """
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
