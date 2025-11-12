#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
HuggingFace 모델 다운로드 스크립트
RAG 시스템에서 사용하는 모든 임베딩 모델을 미리 다운로드
"""

import os
import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from backend.services.rag.models.config import EmbeddingModelType
from backend.services.rag.models.loader import ModelFactory
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def download_model(model_type: EmbeddingModelType, model_name: str):
    """모델 다운로드"""
    print(f"\n{'='*60}")
    print(f"📥 다운로드 중: {model_name}")
    print(f"   모델 타입: {model_type.value}")
    print(f"{'='*60}\n")
    
    try:
        # ModelFactory를 사용하여 모델 다운로드 및 로드
        model = ModelFactory.create_model(model_type, auto_load=True)
        
        print(f"✅ 다운로드 완료: {model_name}")
        print(f"   모델 타입: {type(model.model).__name__}")
        print(f"   차원: {model.get_dimension()}")
        return True
        
    except Exception as e:
        print(f"❌ 다운로드 실패: {model_name}")
        print(f"   오류: {e}")
        import traceback
        traceback.print_exc()
        return False


def download_all_models():
    """모든 모델 다운로드"""
    print("="*60)
    print("🚀 HuggingFace 모델 다운로드 시작")
    print("="*60)
    
    models_to_download = [
        (EmbeddingModelType.MULTILINGUAL_E5_SMALL, "E5-Small"),
        (EmbeddingModelType.MULTILINGUAL_E5_BASE, "E5-Base"),
        (EmbeddingModelType.MULTILINGUAL_E5_LARGE, "E5-Large"),
        (EmbeddingModelType.KAKAOBANK_DEBERTA, "KakaoBank DeBERTa"),
    ]
    
    results = {}
    for model_type, model_name in models_to_download:
        results[model_name] = download_model(model_type, model_name)
    
    # 결과 요약
    print("\n" + "="*60)
    print("📊 다운로드 결과 요약")
    print("="*60)
    
    success_count = sum(1 for v in results.values() if v)
    total_count = len(results)
    
    for model_name, success in results.items():
        status = "✅ 성공" if success else "❌ 실패"
        print(f"  {model_name}: {status}")
    
    print(f"\n총 {total_count}개 중 {success_count}개 성공")
    
    if success_count == total_count:
        print("\n🎉 모든 모델 다운로드 완료!")
    else:
        print(f"\n⚠️  {total_count - success_count}개 모델 다운로드 실패")


def download_specific_model(model_name: str):
    """특정 모델만 다운로드"""
    model_mapping = {
        "e5_small": (EmbeddingModelType.MULTILINGUAL_E5_SMALL, "E5-Small"),
        "e5_base": (EmbeddingModelType.MULTILINGUAL_E5_BASE, "E5-Base"),
        "e5_large": (EmbeddingModelType.MULTILINGUAL_E5_LARGE, "E5-Large"),
        "kakao": (EmbeddingModelType.KAKAOBANK_DEBERTA, "KakaoBank DeBERTa"),
    }
    
    if model_name.lower() not in model_mapping:
        print(f"❌ 알 수 없는 모델: {model_name}")
        print(f"사용 가능한 모델: {', '.join(model_mapping.keys())}")
        return
    
    model_type, display_name = model_mapping[model_name.lower()]
    download_model(model_type, display_name)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="HuggingFace 모델 다운로드")
    parser.add_argument(
        "--model",
        type=str,
        choices=["e5_small", "e5_base", "e5_large", "kakao", "all"],
        default="all",
        help="다운로드할 모델 (기본값: all)"
    )
    
    args = parser.parse_args()
    
    if args.model == "all":
        download_all_models()
    else:
        download_specific_model(args.model)

