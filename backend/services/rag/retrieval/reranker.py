#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
리랭킹 모듈
검색 결과의 품질을 향상시키기 위한 다양한 리랭킹 전략
"""

import logging
import re
import requests
import time
from typing import List, Dict, Any, Optional, Callable
from collections import Counter
import math

logger = logging.getLogger(__name__)


class BaseReranker:
    """기본 리랭커 클래스"""

    def __init__(self, name: str = "BaseReranker"):
        self.name = name
        logger.info(f"Initialized {self.name}")

    def rerank(
        self,
        query: str,
        candidates: List[Dict[str, Any]],
        top_k: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        후보들을 리랭킹

        Args:
            query: 원본 쿼리
            candidates: 후보 결과들
            top_k: 반환할 최대 결과 수

        Returns:
            리랭킹된 결과
        """
        raise NotImplementedError

    def _normalize_score(self, score: float, min_score: float, max_score: float) -> float:
        """점수를 0-1 범위로 정규화"""
        if max_score == min_score:
            return 0.5
        return (score - min_score) / (max_score - min_score)


class KeywordReranker(BaseReranker):
    """키워드 기반 리랭커"""

    def __init__(
        self,
        weight: float = 0.3,
        use_llm_extraction: bool = True,
        llm_generator = None,
        llm_model: str = "gemma3:4b"
    ):
        """
        Args:
            weight: 키워드 점수의 가중치 (0.0 ~ 1.0)
            use_llm_extraction: LLM을 사용한 키워드 추출 여부 (기본값: True)
            llm_generator: LLM 생성기 인스턴스 (None이면 자동 초기화)
            llm_model: LLM 모델명 (기본값: gemma3:4b)
        """
        super().__init__("KeywordReranker")
        self.weight = weight
        self.use_llm_extraction = use_llm_extraction
        self.llm_model = llm_model
        self._keyword_cache = {}  # 키워드 추출 결과 캐싱
        
        # LLM 추출 활성화 시 LLM 생성기 자동 초기화
        if self.use_llm_extraction:
            if llm_generator is None:
                from ..generation.generator import OllamaGenerator
                self.llm_generator = OllamaGenerator(
                    base_url="http://localhost:11434",
                    default_model=self.llm_model
                )
                logger.info(f"KeywordReranker: LLM 키워드 추출 활성화 (모델: {self.llm_model})")
            else:
                self.llm_generator = llm_generator
        else:
            self.llm_generator = None

    def rerank(
        self,
        query: str,
        candidates: List[Dict[str, Any]],
        top_k: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """키워드 매칭을 기반으로 리랭킹"""
        if not candidates:
            return candidates

        query_words = set(self._extract_keywords(query))
        
        for candidate in candidates:
            content = candidate['content']
            content_words = set(self._extract_keywords(content))
            
            # 키워드 겹침 점수 계산
            overlap = len(query_words.intersection(content_words))
            keyword_score = overlap / len(query_words) if query_words else 0.0
            
            # 기존 유사도와 결합
            original_similarity = candidate.get('similarity', 0.0)
            combined_score = (1 - self.weight) * original_similarity + self.weight * keyword_score
            
            candidate['keyword_score'] = keyword_score
            candidate['rerank_score'] = combined_score

        # 리랭킹 점수로 정렬
        reranked = sorted(candidates, key=lambda x: x['rerank_score'], reverse=True)
        
        return reranked[:top_k] if top_k else reranked

    def _extract_keywords(self, text: str) -> List[str]:
        """텍스트에서 키워드 추출"""
        if not text:
            return []
            
        # 캐시 확인
        if text in self._keyword_cache:
            return self._keyword_cache[text]
        
        # LLM 기반 추출
        if self.use_llm_extraction and self.llm_generator:
            keywords = self._extract_keywords_with_llm(text)
        else:
            # 정규식 기반 추출 (기본 방식)
            keywords = self._extract_keywords_with_regex(text)
        
        # 캐시 저장
        self._keyword_cache[text] = keywords
        return keywords
    
    def _extract_keywords_with_regex(self, text: str) -> List[str]:
        """정규식 기반 키워드 추출 (기본 방식)"""
        # 한글, 영문, 숫자만 추출
        words = re.findall(r'[가-힣a-zA-Z0-9]+', text.lower())
        # 2글자 이상만 유효한 키워드로 간주
        return [word for word in words if len(word) >= 2]
    
    def _extract_keywords_with_llm(self, text: str) -> List[str]:
        """LLM을 사용한 키워드 추출"""
        try:
            # 프롬프트 생성
            prompt = self._create_keyword_extraction_prompt(text)
            
            # LLM 직접 호출 (generate 메서드의 프롬프트 템플릿 우회)
            
            if isinstance(self.llm_generator, type):  # 클래스인 경우
                raise ValueError("llm_generator must be an instance, not a class")
            
            # Ollama API 직접 호출
            api_url = self.llm_generator.api_url
            payload = {
                "model": self.llm_model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.3,
                    "num_predict": 200
                }
            }
            
            start_time = time.time()
            response = requests.post(
                api_url,
                json=payload,
                timeout=10
            )
            response.raise_for_status()
            
            result = response.json()
            answer_text = result.get("response", "").strip()
            
            # 키워드 파싱
            keywords = self._parse_keywords_from_llm_response(answer_text)
            
            if not keywords:
                # LLM 실패 시 정규식 방식으로 fallback
                logger.warning(f"LLM keyword extraction failed, falling back to regex. Text: {text[:50]}...")
                return self._extract_keywords_with_regex(text)
            
            return keywords
            
        except Exception as e:
            logger.warning(f"LLM keyword extraction error: {e}, falling back to regex")
            return self._extract_keywords_with_regex(text)
    
    def _create_keyword_extraction_prompt(self, text: str) -> str:
        """키워드 추출용 프롬프트 생성"""
        prompt = f"""다음 텍스트에서 핵심 키워드만 추출해주세요. 

텍스트:
{text}

지시사항:
1. 청년 주거 정책 도메인에 관련된 핵심 키워드만 추출
2. 동의어나 유사어도 함께 고려 (예: "대출" = "융자", "차입")
3. 2글자 이상의 단어만 추출
4. 키워드는 쉼표로 구분하여 나열
5. 불필요한 설명 없이 키워드만 출력

키워드:"""
        return prompt
    
    def _parse_keywords_from_llm_response(self, response: str) -> List[str]:
        """LLM 응답에서 키워드 파싱"""
        if not response:
            return []
        
        # "키워드:" 또는 "키워드:" 이후의 텍스트 추출
        lines = response.split('\n')
        keywords_line = None
        
        for line in lines:
            if '키워드' in line and ':' in line:
                keywords_line = line.split(':', 1)[-1].strip()
                break
        
        # 키워드 라인을 찾지 못하면 마지막 줄 사용
        if keywords_line is None:
            keywords_line = lines[-1].strip()
        
        # 쉼표 또는 줄바꿈으로 분리
        keywords = []
        for part in keywords_line.replace('\n', ',').split(','):
            keyword = part.strip().lower()
            # 불필요한 문자 제거
            keyword = re.sub(r'[^\w가-힣]', '', keyword)
            if len(keyword) >= 2:  # 2글자 이상만
                keywords.append(keyword)
        
        return keywords


class LengthReranker(BaseReranker):
    """길이 기반 리랭커"""

    def __init__(self, optimal_length: int = 200, weight: float = 0.1):
        super().__init__("LengthReranker")
        self.optimal_length = optimal_length
        self.weight = weight

    def rerank(
        self,
        query: str,
        candidates: List[Dict[str, Any]],
        top_k: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """콘텐츠 길이를 고려하여 리랭킹"""
        if not candidates:
            return candidates

        for candidate in candidates:
            content_length = len(candidate['content'])
            
            # 최적 길이에서의 거리 계산
            length_diff = abs(content_length - self.optimal_length)
            length_score = 1.0 / (1.0 + length_diff / self.optimal_length)
            
            # 기존 유사도와 결합
            original_similarity = candidate.get('similarity', 0.0)
            combined_score = (1 - self.weight) * original_similarity + self.weight * length_score
            
            candidate['length_score'] = length_score
            candidate['rerank_score'] = combined_score

        # 리랭킹 점수로 정렬
        reranked = sorted(candidates, key=lambda x: x['rerank_score'], reverse=True)
        
        return reranked[:top_k] if top_k else reranked


class PositionReranker(BaseReranker):
    """위치 기반 리랭커 (문서 내 위치 고려)"""

    def __init__(self, weight: float = 0.1):
        super().__init__("PositionReranker")
        self.weight = weight

    def rerank(
        self,
        query: str,
        candidates: List[Dict[str, Any]],
        top_k: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """문서 내 위치를 고려하여 리랭킹"""
        if not candidates:
            return candidates

        for candidate in candidates:
            # 메타데이터에서 위치 정보 추출
            metadata = candidate.get('metadata', {})
            chunk_index = metadata.get('chunk_index', 0)
            
            # 앞쪽 청크일수록 높은 점수 (문서 시작 부분이 중요)
            position_score = 1.0 / (1.0 + chunk_index * 0.1)
            
            # 기존 유사도와 결합
            original_similarity = candidate.get('similarity', 0.0)
            combined_score = (1 - self.weight) * original_similarity + self.weight * position_score
            
            candidate['position_score'] = position_score
            candidate['rerank_score'] = combined_score

        # 리랭킹 점수로 정렬
        reranked = sorted(candidates, key=lambda x: x['rerank_score'], reverse=True)
        
        return reranked[:top_k] if top_k else reranked


class CombinedReranker(BaseReranker):
    """여러 리랭커를 조합한 통합 리랭커"""

    def __init__(
        self,
        rerankers: List[BaseReranker],
        weights: Optional[List[float]] = None
    ):
        super().__init__("CombinedReranker")
        self.rerankers = rerankers
        self.weights = weights or [1.0] * len(rerankers)
        
        if len(self.weights) != len(self.rerankers):
            raise ValueError("Weights length must match rerankers length")

    def rerank(
        self,
        query: str,
        candidates: List[Dict[str, Any]],
        top_k: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """여러 리랭커의 결과를 조합하여 최종 리랭킹"""
        if not candidates:
            return candidates

        # 각 리랭커로 점수 계산
        for reranker in self.rerankers:
            candidates = reranker.rerank(query, candidates, top_k=None)

        # 가중 평균으로 최종 점수 계산
        for candidate in candidates:
            scores = []
            for i, reranker in enumerate(self.rerankers):
                score_key = f"{reranker.name.lower()}_score"
                if score_key in candidate:
                    scores.append(candidate[score_key] * self.weights[i])
            
            if scores:
                # 원본 유사도도 포함
                original_similarity = candidate.get('similarity', 0.0)
                final_score = (original_similarity * 0.5 + sum(scores) * 0.5) / (0.5 + sum(self.weights) * 0.5)
                candidate['final_rerank_score'] = final_score
            else:
                candidate['final_rerank_score'] = candidate.get('similarity', 0.0)

        # 최종 점수로 정렬
        reranked = sorted(candidates, key=lambda x: x['final_rerank_score'], reverse=True)
        
        return reranked[:top_k] if top_k else reranked


class SemanticReranker(BaseReranker):
    """의미적 유사도 기반 리랭커 (추가 임베딩 모델 사용)"""

    def __init__(
        self,
        encoder,
        weight: float = 0.4
    ):
        super().__init__("SemanticReranker")
        self.encoder = encoder
        self.weight = weight

    def rerank(
        self,
        query: str,
        candidates: List[Dict[str, Any]],
        top_k: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """의미적 유사도를 기반으로 리랭킹"""
        if not candidates:
            return candidates

        try:
            # 쿼리 임베딩
            query_embedding = self.encoder.encode_query(query)
            
            # 각 후보에 대한 의미적 유사도 계산
            for candidate in candidates:
                content = candidate['content']
                content_embedding = self.encoder.encode_query(content)
                
                # 코사인 유사도 계산
                semantic_similarity = self._cosine_similarity(query_embedding, content_embedding)
                
                # 기존 유사도와 결합
                original_similarity = candidate.get('similarity', 0.0)
                combined_score = (1 - self.weight) * original_similarity + self.weight * semantic_similarity
                
                candidate['semantic_score'] = semantic_similarity
                candidate['rerank_score'] = combined_score

        except Exception as e:
            logger.warning(f"Semantic reranking failed: {e}")
            # 실패 시 원본 점수 유지
            for candidate in candidates:
                candidate['semantic_score'] = candidate.get('similarity', 0.0)
                candidate['rerank_score'] = candidate.get('similarity', 0.0)

        # 리랭킹 점수로 정렬
        reranked = sorted(candidates, key=lambda x: x['rerank_score'], reverse=True)
        
        return reranked[:top_k] if top_k else reranked

    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """코사인 유사도 계산"""
        if len(vec1) != len(vec2):
            return 0.0
        
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = math.sqrt(sum(a * a for a in vec1))
        norm2 = math.sqrt(sum(a * a for a in vec2))
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot_product / (norm1 * norm2)


def create_default_reranker() -> CombinedReranker:
    """기본 리랭커 조합 생성"""
    keyword_reranker = KeywordReranker(weight=0.3)
    length_reranker = LengthReranker(optimal_length=200, weight=0.1)
    position_reranker = PositionReranker(weight=0.1)
    
    return CombinedReranker(
        rerankers=[keyword_reranker, length_reranker, position_reranker],
        weights=[0.6, 0.2, 0.2]
    )


if __name__ == "__main__":
    # 테스트
    import logging
    logging.basicConfig(level=logging.INFO)
    
    print("=== Reranker Test ===\n")
    
    # 테스트 데이터
    query = "신혼부부 임차보증금 이자지원"
    candidates = [
        {
            'chunk_id': 1,
            'content': '신혼부부 임차보증금 이자지원사업은 서울시에서 운영하는 주거지원 정책입니다.',
            'similarity': 0.85,
            'metadata': {'chunk_index': 0}
        },
        {
            'chunk_id': 2,
            'content': '이자지원 금리는 연소득에 따라 차등 적용됩니다.',
            'similarity': 0.75,
            'metadata': {'chunk_index': 5}
        },
        {
            'chunk_id': 3,
            'content': '신청 자격은 부부합산 연소득 1억 3천만원 이하입니다.',
            'similarity': 0.80,
            'metadata': {'chunk_index': 2}
        }
    ]
    
    # 키워드 리랭커 테스트
    keyword_reranker = KeywordReranker()
    reranked = keyword_reranker.rerank(query, candidates.copy())
    
    print("Keyword Reranking Results:")
    for i, result in enumerate(reranked, 1):
        print(f"{i}. Similarity: {result['similarity']:.3f}, "
              f"Keyword Score: {result['keyword_score']:.3f}, "
              f"Rerank Score: {result['rerank_score']:.3f}")
        print(f"   Content: {result['content']}")
        print()
    
    # 통합 리랭커 테스트
    combined_reranker = create_default_reranker()
    final_reranked = combined_reranker.rerank(query, candidates.copy())
    
    print("Combined Reranking Results:")
    for i, result in enumerate(final_reranked, 1):
        print(f"{i}. Final Score: {result['final_rerank_score']:.3f}")
        print(f"   Content: {result['content']}")
        print()
