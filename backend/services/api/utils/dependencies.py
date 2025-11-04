"""
FastAPI 의존성 (Dependency) 함수들
- JWT 토큰 검증 및 현재 사용자 가져오기
"""
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import text
from backend.services.db.common.db_utils import get_engine
from backend.services.api.utils.auth import decode_access_token
from backend.services.api.schemas.auth import UserResponse

# HTTP Bearer 토큰 스키마
security = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> UserResponse:
    """
    JWT 토큰에서 현재 사용자 정보 가져오기

    Args:
        credentials: HTTP Authorization 헤더의 Bearer 토큰

    Returns:
        UserResponse: 현재 로그인한 사용자 정보

    Raises:
        HTTPException: 토큰이 유효하지 않거나 사용자를 찾을 수 없는 경우
    """
    token = credentials.credentials
    payload = decode_access_token(token)

    user_id = payload.get("user_id")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 데이터베이스에서 사용자 조회
    engine = get_engine()
    with engine.connect() as conn:
        result = conn.execute(
            text("""
                SELECT id, email, username, full_name, is_active, is_verified,
                       created_at, last_login_at
                FROM auth.users
                WHERE id = :user_id
            """),
            {"user_id": user_id}
        ).fetchone()

        if not result:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # 사용자가 비활성화된 경우
        if not result[4]:  # is_active
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is inactive"
            )

        return UserResponse(
            id=result[0],
            email=result[1],
            username=result[2],
            full_name=result[3],
            is_active=result[4],
            is_verified=result[5],
            created_at=result[6],
            last_login_at=result[7]
        )


def get_current_active_user(
    current_user: UserResponse = Depends(get_current_user)
) -> UserResponse:
    """
    활성화된 사용자만 허용

    Args:
        current_user: 현재 사용자

    Returns:
        UserResponse: 활성화된 사용자

    Raises:
        HTTPException: 사용자가 비활성화된 경우
    """
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user"
        )
    return current_user


def get_optional_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False))
) -> Optional[UserResponse]:
    """
    선택적으로 현재 사용자 가져오기 (토큰이 없어도 에러 발생 안 함)

    Args:
        credentials: HTTP Authorization 헤더의 Bearer 토큰 (선택적)

    Returns:
        Optional[UserResponse]: 로그인한 경우 사용자 정보, 아니면 None
    """
    if credentials is None:
        return None

    try:
        return get_current_user(credentials)
    except HTTPException:
        return None
