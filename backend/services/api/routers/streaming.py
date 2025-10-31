#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
스트리밍 API 라우터
실시간 스트리밍 답변 생성
"""

import logging
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import Optional
import json

from .llm import get_rag_system
from backend.services.rag.generation.streaming_generator import OllamaStreamingGenerator
from backend.services.rag.generation.generator import GenerationConfig

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/llm", tags=["llm"])


class QuestionRequest(BaseModel):
    """질문 요청"""
    question: str = Field(..., description="사용자 질문")
    model_type: str = Field(default="ollama", description="모델 타입")


@router.post("/ask-agent-stream")
async def ask_question_with_agent_stream(
    request: QuestionRequest,
    rag_system = Depends(get_rag_system)
):
    """
    RAG 시스템을 사용한 스트리밍 질문 답변
    
    **스트리밍 응답**: 실시간으로 생성된 답변을 청크 단위로 전송
    """
    try:
        # 1. 검색 및 증강 (비동기로 병렬 처리 가능)
        response = rag_system.retrieve_and_augment(
            query=request.question,
            top_k=3,
            use_reranker=True
        )
        
        # 2. 스트리밍 생성기 초기화
        streaming_generator = OllamaStreamingGenerator(
            base_url=None,  # 환경 변수에서 읽음
            default_model="gemma3:4b"
        )
        
        # 3. 스트리밍 응답 생성
        def generate():
            """스트리밍 응답 생성 제너레이터"""
            try:
                # 먼저 소스 정보를 보냄
                sources = []
                if response.retrieved_documents and len(response.retrieved_documents) > 0:
                    doc = response.retrieved_documents[0]
                    metadata = doc.get("metadata", {})
                    source_title = (
                        doc.get("source") or 
                        metadata.get("source") or 
                        metadata.get("source_doc_title") or 
                        doc.get("title") or 
                        (doc.get("content", "")[:50] if doc.get("content") else "문서")
                    )
                    sources.append({
                        "title": source_title or "문서",
                        "address": doc.get("address", ""),
                        "district": doc.get("district", "")
                    })
                
                # 소스 정보 전송
                yield f"data: {json.dumps({'type': 'sources', 'data': sources})}\n\n"
                
                # 스트리밍 답변 생성
                full_text = ""
                for chunk in streaming_generator.generate_stream(
                    query=request.question,
                    context=response.augmented_context.context_text,
                    config=GenerationConfig(
                        model="gemma3:4b",
                        temperature=0.7,
                        max_tokens=1500,
                        timeout=120
                    )
                ):
                    if chunk.done:
                        # 완료 신호
                        yield f"data: {json.dumps({'type': 'done', 'text': '', 'metadata': chunk.metadata})}\n\n"
                        break
                    else:
                        # 텍스트 청크 전송
                        full_text += chunk.text
                        yield f"data: {json.dumps({'type': 'chunk', 'text': chunk.text})}\n\n"
                
                # 최종 완료 메시지
                yield f"data: {json.dumps({'type': 'complete', 'full_text': full_text})}\n\n"
                
            except Exception as e:
                logger.error(f"Streaming error: {e}", exc_info=True)
                error_msg = json.dumps({
                    'type': 'error',
                    'message': f'스트리밍 중 오류가 발생했습니다: {str(e)}'
                })
                yield f"data: {error_msg}\n\n"
        
        return StreamingResponse(
            generate(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"  # Nginx 버퍼링 비활성화
            }
        )
        
    except Exception as e:
        logger.error(f"Error in ask_question_with_agent_stream: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

