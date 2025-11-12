"""
LLM Integration Views
"""
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
import asyncio
import logging

logger = logging.getLogger(__name__)


@api_view(['GET'])
@permission_classes([AllowAny])
def health_view(request):
    """
    Health check endpoint

    GET /api/llm/health
    """
    return Response({'status': 'ok'}, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([AllowAny])
def chat_view(request):
    """
    Chat with LLM (RAG system)

    POST /api/llm/chat

    Request:
    {
        "messages": [{"role": "user", "content": "..."}],
        "model_type": "ollama"
    }

    Response:
    {
        "message": "...",
        "sources": [...],
        "title": "..."
    }
    """
    try:
        # Import FastAPI dependencies
        from backend.services.api.routers.llm import (
            get_rag_system, chat as llm_chat,
            ChatRequest, ChatMessage as FastAPIChatMessage
        )

        # Parse request data
        messages_data = request.data.get('messages', [])
        model_type = request.data.get('model_type', 'ollama')

        if not messages_data:
            return Response(
                {'detail': 'messages field is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Convert to FastAPI format
        chat_messages = [
            FastAPIChatMessage(role=msg['role'], content=msg['content'])
            for msg in messages_data
        ]

        # Create request
        rag_system = get_rag_system()
        llm_request = ChatRequest(messages=chat_messages, model_type=model_type)

        # Call FastAPI function (async)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            llm_response = loop.run_until_complete(llm_chat(llm_request, rag_system))
        finally:
            loop.close()

        # Return response
        response_data = {
            'message': llm_response.message,
            'sources': llm_response.sources,
        }

        if llm_response.title:
            response_data['title'] = llm_response.title

        return Response(response_data)

    except Exception as e:
        logger.error(f"LLM chat error: {e}", exc_info=True)
        return Response(
            {'detail': f'LLM error: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([AllowAny])
def ask_view(request):
    """
    Simple ask endpoint (single question, no memory)

    POST /api/llm/ask
    """
    try:
        from backend.services.api.routers.llm import (
            get_rag_system, ask_question as llm_ask,
            QuestionRequest
        )

        question = request.data.get('question', '')
        model_type = request.data.get('model_type', 'ollama')
        with_memory = request.data.get('with_memory', False)

        if not question:
            return Response(
                {'detail': 'question field is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        rag_system = get_rag_system()
        llm_request = QuestionRequest(
            question=question,
            model_type=model_type,
            with_memory=with_memory
        )

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            llm_response = loop.run_until_complete(llm_ask(llm_request, rag_system))
        finally:
            loop.close()

        return Response({
            'message': llm_response.message,
            'sources': llm_response.sources,
        })

    except Exception as e:
        logger.error(f"LLM ask error: {e}", exc_info=True)
        return Response(
            {'detail': f'LLM error: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([AllowAny])
def clear_memory_view(request):
    """
    Clear conversation memory

    POST /api/llm/clear-memory
    """
    try:
        from backend.services.api.routers.llm import (
            clear_memory as llm_clear_memory,
            ModelType
        )

        model_type = request.data.get('model_type', 'ollama')

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(llm_clear_memory(model_type))
        finally:
            loop.close()

        return Response({'message': 'Memory cleared successfully'})

    except Exception as e:
        logger.error(f"Clear memory error: {e}", exc_info=True)
        return Response(
            {'detail': f'Error: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([AllowAny])
def ask_langgraph_view(request):
    """
    Ask question using LangGraph

    POST /api/llm/ask-langgraph

    Request:
    {
        "question": "...",
        "model_type": "openai"
    }

    Response:
    {
        "message": "...",
        "sources": [...]
    }
    """
    try:
        from backend.services.api.routers.llm import (
            ask_with_langgraph,
            QuestionRequest
        )

        question = request.data.get('question', '')
        model_type = request.data.get('model_type', 'openai')
        with_memory = request.data.get('with_memory', False)

        if not question:
            return Response(
                {'detail': 'question field is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        llm_request = QuestionRequest(
            question=question,
            model_type=model_type,
            with_memory=with_memory
        )

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            llm_response = loop.run_until_complete(ask_with_langgraph(llm_request))
        finally:
            loop.close()

        return Response({
            'message': llm_response.message,
            'sources': llm_response.sources,
        })

    except Exception as e:
        logger.error(f"LangGraph ask error: {e}", exc_info=True)
        return Response(
            {'detail': f'LangGraph error: {str(e)}'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
