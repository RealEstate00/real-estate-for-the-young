#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
4가지 임베딩 모델로 같은 질문 검색 비교
각 모델이 어떻게 다른 문서를 검색하는지 확인
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

from backend.services.rag.rag_system import RAGSystem
from backend.services.rag.models.config import EmbeddingModelType
import os

def compare_embeddings(query: str):
    """4가지 임베딩 모델로 검색 결과 비교"""
    db_config = {
        'host': os.getenv('PG_HOST', 'localhost'),
        'port': os.getenv('PG_PORT', '5432'),
        'database': os.getenv('PG_DB', 'rey'),
        'user': os.getenv('PG_USER', 'postgres'),
        'password': os.getenv('PG_PASSWORD', 'post1234')
    }

    models = [
        ("E5", EmbeddingModelType.MULTILINGUAL_E5_SMALL),
        ("KAKAO", EmbeddingModelType.KAKAOBANK_DEBERTA),
        ("QWEN", EmbeddingModelType.QWEN_EMBEDDING),
        ("GEMMA", EmbeddingModelType.EMBEDDING_GEMMA)
    ]

    print(f"\n{'='*80}")
    print(f"질문: {query}")
    print(f"{'='*80}\n")

    all_results = {}

    for name, model_type in models:
        print(f"🔍 {name} 모델 검색 중...")

        try:
            rag = RAGSystem(
                model_type=model_type,
                db_config=db_config
            )

            results = rag.search_only(query=query, top_k=5)
            all_results[name] = results

            print(f"   ✅ {len(results)}개 문서 검색 완료")
            print(f"   평균 유사도: {sum(d.get('similarity', 0) for d in results) / len(results):.3f}\n")

        except Exception as e:
            print(f"   ❌ 오류: {e}\n")
            all_results[name] = []

    # 상세 결과 출력
    print(f"\n{'='*80}")
    print("📊 상세 검색 결과 비교")
    print(f"{'='*80}\n")

    for name, results in all_results.items():
        if not results:
            continue

        print(f"\n🔹 {name} 모델:")
        print("-"*80)

        for i, doc in enumerate(results, 1):
            sim = doc.get('similarity', 0)
            source = doc.get('metadata', {}).get('source', 'N/A')
            content = doc.get('content', '')[:150].replace('\n', ' ')

            print(f"{i}. [유사도: {sim:.3f}]")
            print(f"   출처: {source}")
            print(f"   내용: {content}...")
            print()

    # 결론
    print(f"\n{'='*80}")
    print("💡 결론:")
    print(f"{'='*80}")
    print("1. 각 임베딩 모델은 다른 문서를 검색합니다")
    print("2. 유사도 점수도 모델마다 다릅니다")
    print("3. 포맷터는 각 모델이 찾은 문서를 받아서 정리합니다")
    print("4. 즉, --model 선택에 따라 증강되는 내용이 달라집니다!")
    print(f"{'='*80}\n")

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="임베딩 모델별 검색 결과 비교")
    parser.add_argument("query", type=str, nargs="?", default="청년 전세대출 조건과 금리", help="검색 질문")

    args = parser.parse_args()
    compare_embeddings(args.query)
