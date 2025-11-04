"""
대화 관리 API 라우터
- 대화 목록 조회
- 대화 생성
- 대화 상세 조회 (메시지 포함)
- 대화 삭제
- 메시지 추가
"""
from typing import List
from fastapi import APIRouter, HTTPException, status, Depends, Query
from sqlalchemy import text
from backend.services.db.common.db_utils import get_engine
from backend.services.api.schemas.auth import (
    UserResponse, ConversationCreate, ConversationUpdate,
    ConversationResponse, ConversationWithMessages,
    ConversationListResponse, MessageCreate, MessageResponse,
    ChatMessageRequest, ChatMessageResponse
)
from backend.services.api.utils.dependencies import get_current_user
from backend.services.api.routers.llm import chat as llm_chat, ChatRequest, ChatMessage
from backend.services.rag.rag_system import RAGSystem
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/conversations", tags=["Conversations"])


# ==================== 대화 관리 ====================

@router.get("", response_model=ConversationListResponse)
async def get_conversations(
    current_user: UserResponse = Depends(get_current_user),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100)
):
    """
    현재 사용자의 대화 목록 조회

    - **skip**: 건너뛸 개수 (페이지네이션)
    - **limit**: 가져올 개수 (최대 100개)

    Returns:
        ConversationListResponse: 대화 목록 및 총 개수
    """
    engine = get_engine()

    with engine.connect() as conn:
        # 총 대화 개수
        total = conn.execute(
            text("SELECT COUNT(*) FROM auth.conversations WHERE user_id = :user_id"),
            {"user_id": current_user.id}
        ).scalar()

        # 대화 목록 (최신순)
        results = conn.execute(
            text("""
                SELECT id, user_id, title, created_at, updated_at
                FROM auth.conversations
                WHERE user_id = :user_id
                ORDER BY updated_at DESC
                LIMIT :limit OFFSET :skip
            """),
            {"user_id": current_user.id, "limit": limit, "skip": skip}
        ).fetchall()

        conversations = [
            ConversationResponse(
                id=row[0],
                user_id=row[1],
                title=row[2],
                created_at=row[3],
                updated_at=row[4]
            )
            for row in results
        ]

        return ConversationListResponse(
            conversations=conversations,
            total=total
        )


@router.post("", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
async def create_conversation(
    conversation_data: ConversationCreate,
    current_user: UserResponse = Depends(get_current_user)
):
    """
    새 대화 생성

    - **title**: 대화 제목

    Returns:
        ConversationResponse: 생성된 대화 정보
    """
    engine = get_engine()

    with engine.begin() as conn:
        result = conn.execute(
            text("""
                INSERT INTO auth.conversations (user_id, title)
                VALUES (:user_id, :title)
                RETURNING id, user_id, title, created_at, updated_at
            """),
            {"user_id": current_user.id, "title": conversation_data.title}
        ).fetchone()

    logger.info(f"New conversation created: {result[0]} by user {current_user.id}")

    return ConversationResponse(
        id=result[0],
        user_id=result[1],
        title=result[2],
        created_at=result[3],
        updated_at=result[4]
    )


@router.get("/{conversation_id}", response_model=ConversationWithMessages)
async def get_conversation(
    conversation_id: int,
    current_user: UserResponse = Depends(get_current_user)
):
    """
    대화 상세 조회 (메시지 포함)

    Args:
        conversation_id: 대화 ID

    Returns:
        ConversationWithMessages: 대화 정보 및 메시지 목록
    """
    engine = get_engine()

    with engine.connect() as conn:
        # 대화 조회
        conv_result = conn.execute(
            text("""
                SELECT id, user_id, title, created_at, updated_at
                FROM auth.conversations
                WHERE id = :conversation_id
            """),
            {"conversation_id": conversation_id}
        ).fetchone()

        if not conv_result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found"
            )

        # 권한 체크
        if conv_result[1] != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to access this conversation"
            )

        # 메시지 조회 (시간순)
        msg_results = conn.execute(
            text("""
                SELECT id, conversation_id, role, content, created_at
                FROM auth.messages
                WHERE conversation_id = :conversation_id
                ORDER BY created_at ASC
            """),
            {"conversation_id": conversation_id}
        ).fetchall()

        messages = [
            MessageResponse(
                id=row[0],
                conversation_id=row[1],
                role=row[2],
                content=row[3],
                created_at=row[4]
            )
            for row in msg_results
        ]

        return ConversationWithMessages(
            id=conv_result[0],
            user_id=conv_result[1],
            title=conv_result[2],
            created_at=conv_result[3],
            updated_at=conv_result[4],
            messages=messages
        )


@router.patch("/{conversation_id}", response_model=ConversationResponse)
async def update_conversation(
    conversation_id: int,
    update_data: ConversationUpdate,
    current_user: UserResponse = Depends(get_current_user)
):
    """
    대화 제목 수정

    Args:
        conversation_id: 대화 ID
        update_data: 수정할 데이터

    Returns:
        ConversationResponse: 수정된 대화 정보
    """
    engine = get_engine()

    with engine.begin() as conn:
        # 대화 존재 및 권한 체크
        conv_result = conn.execute(
            text("SELECT user_id FROM auth.conversations WHERE id = :conversation_id"),
            {"conversation_id": conversation_id}
        ).fetchone()

        if not conv_result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found"
            )

        if conv_result[0] != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to update this conversation"
            )

        # 제목 수정
        if update_data.title:
            result = conn.execute(
                text("""
                    UPDATE auth.conversations
                    SET title = :title
                    WHERE id = :conversation_id
                    RETURNING id, user_id, title, created_at, updated_at
                """),
                {"conversation_id": conversation_id, "title": update_data.title}
            ).fetchone()

            return ConversationResponse(
                id=result[0],
                user_id=result[1],
                title=result[2],
                created_at=result[3],
                updated_at=result[4]
            )


@router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(
    conversation_id: int,
    current_user: UserResponse = Depends(get_current_user)
):
    """
    대화 삭제 (메시지도 함께 삭제됨)

    Args:
        conversation_id: 대화 ID
    """
    engine = get_engine()

    with engine.begin() as conn:
        # 대화 존재 및 권한 체크
        conv_result = conn.execute(
            text("SELECT user_id FROM auth.conversations WHERE id = :conversation_id"),
            {"conversation_id": conversation_id}
        ).fetchone()

        if not conv_result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found"
            )

        if conv_result[0] != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to delete this conversation"
            )

        # 대화 삭제 (CASCADE로 메시지도 자동 삭제)
        conn.execute(
            text("DELETE FROM auth.conversations WHERE id = :conversation_id"),
            {"conversation_id": conversation_id}
        )

    logger.info(f"Conversation deleted: {conversation_id} by user {current_user.id}")


# ==================== 메시지 관리 ====================

@router.post("/{conversation_id}/messages", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
async def add_message(
    conversation_id: int,
    message_data: MessageCreate,
    current_user: UserResponse = Depends(get_current_user)
):
    """
    대화에 메시지 추가

    Args:
        conversation_id: 대화 ID
        message_data: 메시지 데이터

    Returns:
        MessageResponse: 생성된 메시지
    """
    engine = get_engine()

    with engine.begin() as conn:
        # 대화 존재 및 권한 체크
        conv_result = conn.execute(
            text("SELECT user_id FROM auth.conversations WHERE id = :conversation_id"),
            {"conversation_id": conversation_id}
        ).fetchone()

        if not conv_result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversation not found"
            )

        if conv_result[0] != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to add message to this conversation"
            )

        # 메시지 추가
        result = conn.execute(
            text("""
                INSERT INTO auth.messages (conversation_id, role, content)
                VALUES (:conversation_id, :role, :content)
                RETURNING id, conversation_id, role, content, created_at
            """),
            {
                "conversation_id": conversation_id,
                "role": message_data.role,
                "content": message_data.content
            }
        ).fetchone()

    return MessageResponse(
        id=result[0],
        conversation_id=result[1],
        role=result[2],
        content=result[3],
        created_at=result[4]
    )


# ==================== 채팅 (LLM 연동) ====================

@router.post("/chat", response_model=ChatMessageResponse)
async def chat_with_save(
    chat_request: ChatMessageRequest,
    current_user: UserResponse = Depends(get_current_user)
):
    """
    채팅 메시지 전송 및 대화 저장

    - **conversation_id**: 기존 대화 ID (None이면 새 대화 생성)
    - **message**: 사용자 메시지
    - **model_type**: 모델 타입 (기본: ollama)

    Returns:
        ChatMessageResponse: 사용자 메시지 및 AI 응답
    """
    from backend.services.rag.rag_system import get_rag_system

    engine = get_engine()
    conversation_id = chat_request.conversation_id

    # 1. 대화 ID가 없으면 새 대화 생성
    if conversation_id is None:
        with engine.begin() as conn:
            result = conn.execute(
                text("""
                    INSERT INTO auth.conversations (user_id, title)
                    VALUES (:user_id, :title)
                    RETURNING id
                """),
                {
                    "user_id": current_user.id,
                    "title": chat_request.message[:50]  # 임시 제목 (나중에 LLM 응답으로 업데이트)
                }
            ).fetchone()
            conversation_id = result[0]
    else:
        # 대화 권한 체크
        with engine.connect() as conn:
            conv_result = conn.execute(
                text("SELECT user_id FROM auth.conversations WHERE id = :conversation_id"),
                {"conversation_id": conversation_id}
            ).fetchone()

            if not conv_result:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Conversation not found"
                )

            if conv_result[0] != current_user.id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Not authorized to access this conversation"
                )

    # 2. 기존 메시지 불러오기
    with engine.connect() as conn:
        msg_results = conn.execute(
            text("""
                SELECT role, content
                FROM auth.messages
                WHERE conversation_id = :conversation_id
                ORDER BY created_at ASC
            """),
            {"conversation_id": conversation_id}
        ).fetchall()

        chat_history = [
            ChatMessage(role=row[0], content=row[1])
            for row in msg_results
        ]

    # 3. 사용자 메시지 추가
    chat_history.append(ChatMessage(role="user", content=chat_request.message))

    # 4. LLM 호출
    rag_system = get_rag_system()
    llm_request = ChatRequest(messages=chat_history, model_type=chat_request.model_type)
    llm_response = await llm_chat(llm_request, rag_system)

    # 5. 메시지 저장 (사용자 + AI)
    with engine.begin() as conn:
        # 사용자 메시지 저장
        user_msg = conn.execute(
            text("""
                INSERT INTO auth.messages (conversation_id, role, content)
                VALUES (:conversation_id, 'user', :content)
                RETURNING id, conversation_id, role, content, created_at
            """),
            {"conversation_id": conversation_id, "content": chat_request.message}
        ).fetchone()

        # AI 응답 저장
        assistant_msg = conn.execute(
            text("""
                INSERT INTO auth.messages (conversation_id, role, content)
                VALUES (:conversation_id, 'assistant', :content)
                RETURNING id, conversation_id, role, content, created_at
            """),
            {"conversation_id": conversation_id, "content": llm_response.message}
        ).fetchone()

        # 첫 번째 AI 답변인 경우 대화 제목 업데이트 (이전 메시지가 없고, LLM이 제목을 생성한 경우)
        # len(msg_results) == 0: DB에 저장된 이전 메시지가 없음 = 첫 대화 시작
        if llm_response.title and len(msg_results) == 0:
            conn.execute(
                text("UPDATE auth.conversations SET title = :title WHERE id = :conversation_id"),
                {"conversation_id": conversation_id, "title": llm_response.title}
            )
            logger.info(f"✅ 첫 번째 AI 답변 기반 제목 생성 및 DB 저장: '{llm_response.title}' ({len(llm_response.title)}자)")

    # 첫 번째 AI 답변인 경우에만 제목 반환 (이전 메시지가 없고, LLM이 생성한 제목)
    # len(msg_results) == 0: 첫 사용자 질문 + 첫 AI 답변 = 첫 대화 시작
    response_title = None
    if len(msg_results) == 0 and llm_response.title:
        response_title = llm_response.title
        logger.info(f"✅ 첫 번째 AI 답변 기반 제목 반환: '{response_title}' ({len(response_title)}자)")
    
    return ChatMessageResponse(
        conversation_id=conversation_id,
        user_message=MessageResponse(
            id=user_msg[0],
            conversation_id=user_msg[1],
            role=user_msg[2],
            content=user_msg[3],
            created_at=user_msg[4]
        ),
        assistant_message=MessageResponse(
            id=assistant_msg[0],
            conversation_id=assistant_msg[1],
            role=assistant_msg[2],
            content=assistant_msg[3],
            created_at=assistant_msg[4]
        ),
        sources=llm_response.sources,
        title=response_title
    )
