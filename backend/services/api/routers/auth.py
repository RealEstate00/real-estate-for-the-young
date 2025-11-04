"""
인증 관련 API 라우터
- 회원가입
- 로그인
- 사용자 정보 조회
"""
from fastapi import APIRouter, HTTPException, status, Depends
from sqlalchemy import text
from backend.services.db.common.db_utils import get_engine
from backend.services.api.schemas.auth import (
    UserCreate, UserLogin, UserResponse, TokenResponse
)
from backend.services.api.utils.auth import (
    hash_password, verify_password, create_access_token
)
from backend.services.api.utils.dependencies import get_current_user
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserCreate):
    """
    회원가입

    - **email**: 이메일 주소 (로그인 ID)
    - **username**: 사용자명 (3-100자, 영숫자, -, _만 허용)
    - **password**: 비밀번호 (최소 8자)
    - **full_name**: 전체 이름 (선택)

    Returns:
        TokenResponse: JWT 토큰 및 사용자 정보
    """
    engine = get_engine()

    # 1. 이메일 중복 체크
    with engine.connect() as conn:
        existing_email = conn.execute(
            text("SELECT id FROM auth.users WHERE email = :email"),
            {"email": user_data.email}
        ).fetchone()

        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )

        # 2. 사용자명 중복 체크
        existing_username = conn.execute(
            text("SELECT id FROM auth.users WHERE username = :username"),
            {"username": user_data.username}
        ).fetchone()

        if existing_username:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already taken"
            )

    # 3. 비밀번호 해싱
    hashed_password = hash_password(user_data.password)

    # 4. 사용자 생성
    with engine.begin() as conn:
        result = conn.execute(
            text("""
                INSERT INTO auth.users (email, username, password_hash, full_name)
                VALUES (:email, :username, :password_hash, :full_name)
                RETURNING id, email, username, full_name, is_active, is_verified, created_at, last_login_at
            """),
            {
                "email": user_data.email,
                "username": user_data.username,
                "password_hash": hashed_password,
                "full_name": user_data.full_name
            }
        ).fetchone()

    user = UserResponse(
        id=result[0],
        email=result[1],
        username=result[2],
        full_name=result[3],
        is_active=result[4],
        is_verified=result[5],
        created_at=result[6],
        last_login_at=result[7]
    )

    # 5. JWT 토큰 생성
    access_token = create_access_token(
        data={"user_id": user.id, "email": user.email}
    )

    logger.info(f"New user registered: {user.email}")

    return TokenResponse(
        access_token=access_token,
        user=user
    )


@router.post("/login", response_model=TokenResponse)
async def login(credentials: UserLogin):
    """
    로그인

    - **email**: 이메일 주소
    - **password**: 비밀번호

    Returns:
        TokenResponse: JWT 토큰 및 사용자 정보
    """
    engine = get_engine()

    # 1. 사용자 조회
    with engine.connect() as conn:
        result = conn.execute(
            text("""
                SELECT id, email, username, password_hash, full_name,
                       is_active, is_verified, created_at, last_login_at
                FROM auth.users
                WHERE email = :email
            """),
            {"email": credentials.email}
        ).fetchone()

        if not result:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password"
            )

    # 2. 비밀번호 검증
    if not verify_password(credentials.password, result[3]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )

    # 3. 계정 활성화 체크
    if not result[5]:  # is_active
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive"
        )

    user = UserResponse(
        id=result[0],
        email=result[1],
        username=result[2],
        full_name=result[4],
        is_active=result[5],
        is_verified=result[6],
        created_at=result[7],
        last_login_at=result[8]
    )

    # 4. 마지막 로그인 시간 업데이트
    with engine.begin() as conn:
        conn.execute(
            text("UPDATE auth.users SET last_login_at = now() WHERE id = :user_id"),
            {"user_id": user.id}
        )

    # 5. JWT 토큰 생성
    access_token = create_access_token(
        data={"user_id": user.id, "email": user.email}
    )

    logger.info(f"User logged in: {user.email}")

    return TokenResponse(
        access_token=access_token,
        user=user
    )


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: UserResponse = Depends(get_current_user)):
    """
    현재 로그인한 사용자 정보 조회

    Returns:
        UserResponse: 사용자 정보
    """
    return current_user


@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user_by_id(user_id: int):
    """
    특정 사용자 정보 조회 (공개 정보만)

    Args:
        user_id: 사용자 ID

    Returns:
        UserResponse: 사용자 정보
    """
    engine = get_engine()

    with engine.connect() as conn:
        result = conn.execute(
            text("""
                SELECT id, email, username, full_name, is_active, is_verified, created_at, last_login_at
                FROM auth.users
                WHERE id = :user_id
            """),
            {"user_id": user_id}
        ).fetchone()

        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
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
