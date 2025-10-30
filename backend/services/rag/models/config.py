#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
임베딩 모델 설정 및 파라미터 관리
5가지 HuggingFace 모델을 쉽게 교체하고 비교할 수 있도록 구성
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional
from enum import Enum


class EmbeddingModelType(str, Enum):
    """지원하는 임베딩 모델 타입"""
    MULTILINGUAL_E5_SMALL = "intfloat/multilingual-e5-small"
    KAKAOBANK_DEBERTA = "kakaobank/kf-deberta-base"
    QWEN_EMBEDDING = "Qwen/Qwen3-Embedding-0.6B"
    EMBEDDING_GEMMA = "google/embeddinggemma-300m"


@dataclass
class ModelConfig:
    """개별 모델 설정"""
    model_name: str
    display_name: str
    dimension: int
    max_seq_length: int
    batch_size: int
    normalize_embeddings: bool
    pooling_mode: str  # 'mean', 'cls', 'max', 'last_token'
    trust_remote_code: bool
    device: str = "cuda"  # "cuda" or "cpu"

    # 모델별 특수 파라미터
    extra_params: Dict[str, Any] = field(default_factory=dict)

    # 검색 성능 메타정보
    notes: str = ""


# ============================================================================
# 모델별 최적화 파라미터 설정
# ============================================================================

MODEL_CONFIGS: Dict[EmbeddingModelType, ModelConfig] = {

    # 1. Multilingual E5 Small (경량, 빠른 속도)
    EmbeddingModelType.MULTILINGUAL_E5_SMALL: ModelConfig(
        model_name="intfloat/multilingual-e5-small",
        display_name="E5-Small (Multilingual)",
        dimension=384,
        max_seq_length=512,
        batch_size=64,
        normalize_embeddings=True,
        pooling_mode="mean",
        trust_remote_code=False,
        extra_params={
            "query_prefix": "query: ",  # E5 모델은 쿼리에 prefix 필수
            "passage_prefix": "passage: ",  # 문서에도 prefix 필수
            "torch_dtype": "float32"  # E5는 float32 권장
        },
        notes="경량 모델, 빠른 추론 속도, 100개 언어 지원, prefix 필수 사용"
    ),

    # 2. KakaoBank KF-DeBERTa Base (한국어 특화)
    EmbeddingModelType.KAKAOBANK_DEBERTA: ModelConfig(
        model_name="kakaobank/kf-deberta-base",
        display_name="KakaoBank DeBERTa",
        dimension=768,
        max_seq_length=512,
        batch_size=32,
        normalize_embeddings=True,
        pooling_mode="mean",
        trust_remote_code=False,
        extra_params={
            "use_auth_token": False,
            "torch_dtype": "float32"
        },
        notes="한국어 금융 데이터 특화, MIT 라이선스, DeBERTa-v2 아키텍처"
    ),

    # 3. Qwen3 Embedding 0.6B (고성능, 긴 문맥)
    EmbeddingModelType.QWEN_EMBEDDING: ModelConfig(
        model_name="Qwen/Qwen3-Embedding-0.6B",
        display_name="Qwen3 Embedding 0.6B",
        dimension=1024,  # 기본 1024, MRL로 32~1024 가변 지원
        max_seq_length=32768,  # 32k 토큰 지원 (매우 긴 문맥)
        batch_size=16,
        normalize_embeddings=True,
        pooling_mode="last_token",  # Qwen3는 last token pooling 사용
        trust_remote_code=True,
        extra_params={
            "padding_side": "left",  # Qwen3는 left padding 필수
            "torch_dtype": "float16",  # float16 권장
            "attn_implementation": "flash_attention_2",  # FlashAttention2 지원
            "query_instruction": "Instruct: Given a web search query, retrieve relevant passages that answer the query\nQuery: ",  # 쿼리용 instruction
            "matryoshka_dims": [32, 64, 128, 256, 512, 1024]  # MRL 지원 차원
        },
        notes="MTEB 1위, 100개 언어, 32k 문맥, MRL 지원, instruction-aware"
    ),

    # 4. Google EmbeddingGemma 300M
    EmbeddingModelType.EMBEDDING_GEMMA: ModelConfig(
        model_name="google/embeddinggemma-300m",
        display_name="EmbeddingGemma 300M",
        dimension=768,  # 고정 768차원 사용 (MRL 비활성화)
        max_seq_length=2048,  # 2048 토큰
        batch_size=32,
        normalize_embeddings=True,
        pooling_mode="mean",
        trust_remote_code=True,
        extra_params={
            "torch_dtype": "bfloat16",  # float16 미지원, bfloat16 또는 float32 사용
            "matryoshka_dims": [768],  # MRL 비활성화, 768차원만 사용
            "task_prompts": {
                "retrieval_query": "task: search result | query: ",
                "retrieval_document": "title: none | text: ",
                "classification": "task: classification | query: ",
                "clustering": "task: clustering | query: ",
                "similarity": "task: sentence similarity | query: "
            }
        },
        notes="Google Gemma3 기반, 100개 언어, task-specific prompts, 768차원 고정"
    ),

}


# ============================================================================
# 비교 실험 설정
# ============================================================================

@dataclass
class ExperimentConfig:
    """임베딩 모델 비교 실험 설정"""

    # 테스트할 모델 목록
    models_to_test: list[EmbeddingModelType] = field(
        default_factory=lambda: list(EmbeddingModelType)
    )

    # 검색 파라미터
    top_k: int = 5
    similarity_threshold: float = 0.5

    # 결과 저장 경로
    results_dir: str = "data/embedding_comparisons"

    # 로깅
    save_embeddings: bool = False  # 임베딩 벡터 저장 여부
    save_search_results: bool = True  # 검색 결과 저장 여부
    save_metrics: bool = True  # 성능 메트릭 저장 여부


# ============================================================================
# 유틸리티 함수
# ============================================================================

def get_model_config(model_type: EmbeddingModelType) -> ModelConfig:
    """모델 타입으로 설정 가져오기"""
    return MODEL_CONFIGS[model_type]


def get_all_model_names() -> list[str]:
    """모든 모델 이름 반환"""
    return [model.value for model in EmbeddingModelType]


def get_model_by_name(model_name: str) -> Optional[ModelConfig]:
    """모델 이름으로 설정 가져오기"""
    for model_type in EmbeddingModelType:
        if model_type.value == model_name:
            return MODEL_CONFIGS[model_type]
    return None


def print_model_comparison():
    """모델 비교 정보 출력"""
    print("=" * 100)
    print("임베딩 모델 비교표")
    print("=" * 100)
    print(f"{'모델명':<35} {'차원':>6} {'최대길이':>8} {'배치':>6} {'Pooling':<12} {'설명':<30}")
    print("-" * 100)

    for model_type, config in MODEL_CONFIGS.items():
        print(f"{config.display_name:<35} {config.dimension:>6} {config.max_seq_length:>8} "
              f"{config.batch_size:>6} {config.pooling_mode:<12} {config.notes[:28]:<30}")

    print("=" * 100)


def print_usage_recommendations():
    """모델별 사용 권장사항 출력"""
    print("\n" + "=" * 100)
    print("📌 모델별 사용 권장사항")
    print("=" * 100)
    
    recommendations = {
        "E5-Small (Multilingual)": [
            "✅ 빠른 프로토타이핑 및 테스트",
            "✅ 리소스 제약 환경 (모바일, 엣지)",
            "✅ 다국어 지원 필요시",
            "⚠️ 쿼리와 문서에 반드시 'query:' 'passage:' prefix 추가 필요"
        ],
        "KakaoBank DeBERTa": [
            "✅ 한국어 금융/주택 도메인 텍스트",
            "✅ 높은 한국어 이해도 필요시",
            "✅ 상업용 프로젝트 (MIT 라이선스)",
            "⚠️ 512 토큰 제한"
        ],
        "Qwen3 Embedding 0.6B": [
            "✅ 긴 문서 처리 (최대 32k 토큰)",
            "✅ 높은 검색 정확도 필요시 (MTEB 1위급)",
            "✅ MRL로 임베딩 차원 유연한 조정 필요시",
            "⚠️ left padding 및 instruction 필수"
        ],
        "EmbeddingGemma 300M": [
            "✅ task-specific 최적화 필요시",
            "✅ Google 생태계 통합",
            "✅ 균형잡힌 성능/속도",
            "⚠️ float16 미지원 (bfloat16 또는 float32 사용)"
        ],
        "Jina Embeddings v4": [
            "✅ 멀티모달 검색 (텍스트+이미지)",
            "✅ 최신 기술 및 최고 성능 필요시",
            "✅ 긴 문맥 처리 (32k)",
            "⚠️ 큰 모델 크기 (3B 기반), GPU 메모리 요구량 높음"
        ]
    }
    
    for model_name, recs in recommendations.items():
        print(f"\n🔹 {model_name}")
        for rec in recs:
            print(f"  {rec}")
    
    print("=" * 100)


if __name__ == "__main__":
    # 모델 비교 정보 출력
    print_model_comparison()

    # 개별 모델 설정 확인
    print("\n\n=== 모델별 상세 설정 ===\n")
    for model_type in EmbeddingModelType:
        config = get_model_config(model_type)
        print(f"\n{'='*80}")
        print(f"🔸 {config.display_name}")
        print(f"{'='*80}")
        print(f"  모델명: {config.model_name}")
        print(f"  차원: {config.dimension}")
        print(f"  최대 시퀀스 길이: {config.max_seq_length:,} 토큰")
        print(f"  배치 크기: {config.batch_size}")
        print(f"  정규화: {config.normalize_embeddings}")
        print(f"  Pooling 방식: {config.pooling_mode}")
        print(f"  Trust Remote Code: {config.trust_remote_code}")
        print(f"  추가 파라미터:")
        for key, value in config.extra_params.items():
            print(f"    - {key}: {value}")
        print(f"  특징: {config.notes}")
    
    # 사용 권장사항 출력
    print_usage_recommendations()