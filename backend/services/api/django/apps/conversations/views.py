"""
Conversation and Message views
"""
from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from .models import Conversation, Message
from .serializers import (
    ConversationSerializer, ConversationDetailSerializer,
    MessageSerializer, ChatRequestSerializer, ChatResponseSerializer
)
import logging

logger = logging.getLogger(__name__)


class ConversationViewSet(viewsets.ModelViewSet):
    """
    Conversation CRUD operations

    list: GET /api/conversations/
    create: POST /api/conversations/
    retrieve: GET /api/conversations/{id}/
    update: PUT/PATCH /api/conversations/{id}/
    destroy: DELETE /api/conversations/{id}/
    """
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """Only return user's own conversations"""
        return Conversation.objects.filter(user=self.request.user)

    def get_serializer_class(self):
        """Use detail serializer for retrieve action"""
        if self.action == 'retrieve':
            return ConversationDetailSerializer
        return ConversationSerializer

    def perform_create(self, serializer):
        """Set user automatically"""
        serializer.save(user=self.request.user)

    @action(detail=True, methods=['post'])
    def add_message(self, request, pk=None):
        """
        Add a message to conversation

        POST /api/conversations/{id}/add_message/
        """
        conversation = self.get_object()
        serializer = MessageSerializer(data=request.data)

        if serializer.is_valid():
            serializer.save(conversation=conversation)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def chat_view(request):
    """
    Chat with LLM and save to database

    POST /api/conversations/chat/

    Request:
    {
        "conversation_id": 1 (optional, null for new conversation),
        "message": "User message text",
        "model_type": "ollama" (optional)
    }

    Response:
    {
        "conversation_id": 1,
        "user_message": {...},
        "assistant_message": {...},
        "sources": [...]
    }
    """
    serializer = ChatRequestSerializer(data=request.data)

    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    conversation_id = serializer.validated_data.get('conversation_id')
    user_message_text = serializer.validated_data['message']
    model_type = serializer.validated_data.get('model_type', 'ollama')

    # 1. Get or create conversation
    if conversation_id:
        conversation = get_object_or_404(
            Conversation,
            id=conversation_id,
            user=request.user
        )
    else:
        # Create new conversation with temporary title
        conversation = Conversation.objects.create(
            user=request.user,
            title=user_message_text[:50]
        )

    # 2. Get existing messages for context
    existing_messages = Message.objects.filter(
        conversation=conversation
    ).order_by('created_at')

    chat_history = [
        {'role': msg.role, 'content': msg.content}
        for msg in existing_messages
    ]

    # Add current user message
    chat_history.append({'role': 'user', 'content': user_message_text})

    # 3. Call LLM (import from FastAPI code)
    try:
        from backend.services.api.routers.llm import (
            get_rag_system, chat as llm_chat,
            ChatRequest, ChatMessage
        )

        rag_system = get_rag_system()
        llm_request = ChatRequest(
            messages=[ChatMessage(**msg) for msg in chat_history],
            model_type=model_type
        )

        # This is a synchronous call - need to handle asyncio
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        llm_response = loop.run_until_complete(llm_chat(llm_request, rag_system))
        loop.close()

    except Exception as e:
        logger.error(f"LLM call failed: {e}")
        return Response(
            {'detail': f'LLM call failed: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

    # 4. Save messages
    user_msg = Message.objects.create(
        conversation=conversation,
        role='user',
        content=user_message_text
    )

    assistant_msg = Message.objects.create(
        conversation=conversation,
        role='assistant',
        content=llm_response.message
    )

    # 5. Update conversation title if first message
    generated_title = None
    if not conversation_id and llm_response.title:
        conversation.title = llm_response.title
        conversation.save(update_fields=['title'])
        generated_title = llm_response.title

    # 6. Return response
    response_data = {
        'conversation_id': conversation.id,
        'user_message': MessageSerializer(user_msg).data,
        'assistant_message': MessageSerializer(assistant_msg).data,
        'sources': llm_response.sources,
        'title': generated_title  # Include title in response for first message
    }

    return Response(response_data, status=status.HTTP_200_OK)
