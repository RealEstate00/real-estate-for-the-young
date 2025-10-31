#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
스트리밍 LLM Generator
Ollama를 통한 스트리밍 답변 생성
"""

import logging
import os
import requests
import json
from typing import Optional, Dict, Any, Generator
from dataclasses import dataclass

from .generator import GenerationConfig

logger = logging.getLogger(__name__)


@dataclass
class StreamingChunk:
    """스트리밍 청크"""
    text: str
    done: bool = False
    metadata: Optional[Dict[str, Any]] = None


class OllamaStreamingGenerator:
    """Ollama 기반 스트리밍 생성기"""

    def __init__(
        self,
        base_url: Optional[str] = None,
        default_model: str = "gemma3:4b"
    ):
        """
        Args:
            base_url: Ollama API URL (없으면 환경 변수 또는 기본값 사용)
            default_model: 기본 모델명
        """
        # 환경 변수 또는 기본값 사용
        if base_url is None:
            base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
        
        self.base_url = base_url.rstrip('/')
        self.default_model = default_model
        self.api_url = f"{self.base_url}/api/generate"

        logger.info(f"OllamaStreamingGenerator initialized with base_url: {self.base_url}, model: {default_model}")

    def _create_prompt(self, query: str, context: str) -> str:
        """프롬프트 생성"""
        prompt = f"""당신은 청년 주거 정책 전문 상담사입니다. 주어진 문서를 바탕으로 사용자의 질문에 정확하고 친절하게 답변해주세요.

## 참고 문서
{context}

## 사용자 질문
{query}

## 답변 작성 규칙
1. **정확성**: 참고 문서의 내용만을 기반으로 답변하고, 문서에 없는 내용은 추측하지 마세요
2. **구조화**: 명확한 섹션으로 나누어 체계적으로 작성하세요 (예: 신청 자격, 금리, 한도, 신청 방법 등)
3. **완전성**: 표나 리스트를 작성할 때 중간에 끊기지 않도록 완전하게 작성하세요
4. **구체성**: 조건, 금액, 금리, 절차 등 구체적인 수치와 정보를 명시하세요
5. **명확성**: 마크다운 형식을 사용하여 읽기 쉽게 작성하세요 (**, -, 1. 등)
6. **관련성**: 질문과 직접 관련된 정보만 제공하고, 불필요한 내용은 제외하세요
7. **친절성**: 한국어로 자연스럽고 친절하게 답변하세요

답변:"""
        return prompt

    def generate_stream(
        self,
        query: str,
        context: str,
        config: Optional[GenerationConfig] = None
    ) -> Generator[StreamingChunk, None, None]:
        """
        스트리밍 답변 생성

        Args:
            query: 사용자 질문
            context: RAG로 검색된 컨텍스트
            config: 생성 설정

        Yields:
            StreamingChunk: 스트리밍 청크
        """
        if config is None:
            config = GenerationConfig(model=self.default_model)

        # 프롬프트 생성
        prompt = self._create_prompt(query, context)

        # API 요청 페이로드
        payload = {
            "model": config.model,
            "prompt": prompt,
            "stream": True,  # 스트리밍 활성화
            "options": {
                "temperature": config.temperature,
                "num_predict": config.max_tokens,
                "top_p": config.top_p
            }
        }

        logger.info(f"Streaming generation started with {config.model}...")

        try:
            response = requests.post(
                self.api_url,
                json=payload,
                timeout=config.timeout,
                stream=True  # 스트리밍 요청
            )
            response.raise_for_status()

            full_text = ""
            for line in response.iter_lines():
                if not line:
                    continue

                try:
                    chunk_data = line.decode('utf-8')
                    # Ollama는 각 라인마다 JSON 객체를 보냄
                    chunk_json = json.loads(chunk_data)
                    
                    # 응답 텍스트 추출
                    chunk_text = chunk_json.get("response", "")
                    if chunk_text:
                        full_text += chunk_text
                        yield StreamingChunk(
                            text=chunk_text,
                            done=False,
                            metadata={
                                "model": chunk_json.get("model"),
                                "done": chunk_json.get("done", False)
                            }
                        )
                    
                    # 완료 확인
                    if chunk_json.get("done", False):
                        yield StreamingChunk(
                            text="",
                            done=True,
                            metadata={
                                "model": chunk_json.get("model"),
                                "eval_count": chunk_json.get("eval_count"),
                                "prompt_eval_count": chunk_json.get("prompt_eval_count"),
                                "total_duration": chunk_json.get("total_duration")
                            }
                        )
                        break
                except json.JSONDecodeError:
                    # JSON 파싱 오류는 무시하고 다음 라인 처리
                    continue
                except Exception as e:
                    # 기타 오류 로깅 후 계속 진행
                    logger.warning(f"Error processing chunk: {e}")
                    continue

            logger.info(f"Streaming generation completed: {len(full_text)} chars")
            
        except requests.exceptions.Timeout:
            logger.error("Streaming generation timeout")
            yield StreamingChunk(
                text="\n\n[답변 생성 시간이 초과되었습니다. 잠시 후 다시 시도해주세요.]",
                done=True,
                metadata={"error": "timeout"}
            )
        except Exception as e:
            logger.error(f"Streaming generation error: {e}", exc_info=True)
            yield StreamingChunk(
                text=f"\n\n[오류가 발생했습니다: {str(e)}]",
                done=True,
                metadata={"error": str(e)}
            )
