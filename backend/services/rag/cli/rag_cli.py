#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
RAG 시스템 통합 CLI

Usage:
  rag-eval all              # 5개 모델 전체 평가
  rag-eval model --model E5  # 특정 모델 평가
  rag-eval reranking        # 리랭킹 효과 비교
"""

import os
import sys
import logging
import argparse
from pathlib import Path
from typing import List, Optional

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(project_root))

from backend.services.rag.config import EmbeddingModelType, get_model_config
from backend.services.rag.core.evaluator import RAGEvaluator
from backend.services.rag.core.embedder import MultiModelEmbedder
from backend.services.db.common.db_utils import test_connection

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def get_db_config() -> dict:
    """데이터베이스 설정 가져오기"""
    return {
        'host': os.getenv('PG_HOST', 'localhost'),
        'port': os.getenv('PG_PORT', '5432'),
        'database': os.getenv('PG_DB', 'rey'),
        'user': os.getenv('PG_USER', 'postgres'),
        'password': os.getenv('PG_PASSWORD', 'post1234')
    }


def list_models():
    """사용 가능한 모델 목록 출력"""
    print("\n" + "="*80)
    print("사용 가능한 임베딩 모델")
    print("="*80)
    print(f"{'모델 타입':<30} {'이름':<40} {'차원':>6}")
    print("-"*80)

    for model_type in EmbeddingModelType:
        config = get_model_config(model_type)
        print(f"{model_type.name:<30} {config.display_name:<40} {config.dimension:>6}")

    print("="*80)
    print("\n사용 방법:")
    print("  rag-eval model --model E5")
    print("  rag-eval model --model KAKAOBANK_DEBERTA")
    print()


def evaluate_single_model(
    model_type: EmbeddingModelType,
    db_config: dict,
    top_k: int = 5,
    use_reranking: bool = False,
    save_results: bool = True,
    save_search_results: bool = False
) -> bool:
    """단일 모델 평가"""
    try:
        logger.info(f"=== {model_type.value} 모델 평가 시작 ===")

        evaluator = RAGEvaluator(db_config)
        result = evaluator.evaluate_model(
            model_type=model_type,
            top_k=top_k,
            use_reranking=use_reranking,
            save_search_results=save_search_results
        )

        if result.get('status') == 'failed':
            logger.error(f"평가 실패: {result.get('error')}")
            return False

        # 결과 저장
        if save_results:
            output_path = evaluator.save_results({'evaluation': result})
            print(f"\n✅ 평가 결과 저장: {output_path}")

        return True

    except Exception as e:
        logger.exception(f"모델 평가 중 오류 발생: {e}")
        return False


def evaluate_all_models(
    db_config: dict,
    top_k: int = 5,
    compare_reranking: bool = False,
    save_results: bool = True,
    save_search_results: bool = False
) -> bool:
    """전체 모델 평가"""
    try:
        logger.info("=== 5개 모델 전체 평가 시작 ===")

        # 모든 모델
        models = list(EmbeddingModelType)

        evaluator = RAGEvaluator(db_config)
        results = evaluator.evaluate_all_models(
            models=models,
            top_k=top_k,
            compare_reranking=compare_reranking,
            save_search_results=save_search_results
        )

        # 요약 출력
        print(results['summary'])

        # 상세 비교 출력
        print_comparison_table(results)

        # 리랭킹 비교 (옵션)
        if compare_reranking and results.get('reranking_comparison'):
            print_reranking_comparison(results['reranking_comparison'])

        # 결과 저장
        if save_results:
            output_path = evaluator.save_results(results)
            print(f"\n✅ 전체 평가 결과 저장: {output_path}")

        return True

    except Exception as e:
        logger.exception(f"전체 모델 평가 중 오류 발생: {e}")
        return False


def print_comparison_table(results: dict):
    """비교 결과를 표로 출력"""
    print("\n" + "="*120)
    print("모델 성능 비교")
    print("="*120)

    comparisons = results.get('comparison', {}).get('comparisons', {})

    if not comparisons:
        print("비교 결과가 없습니다.")
        return

    # 헤더
    print(f"{'모델명':<40} {'평균 Latency':>15} {'P95 Latency':>15} {'유사도':>10} {'Recall@5':>12} {'MRR':>10}")
    print("-"*120)

    # 각 모델 정보
    for model_name in comparisons.get('accuracy', {}).keys():
        latency = comparisons.get('latency', {}).get(model_name, {})
        accuracy = comparisons.get('accuracy', {}).get(model_name, 0)
        recall = comparisons.get('recall', {}).get(model_name, 0)
        mrr = comparisons.get('mrr', {}).get(model_name, 0)

        avg_lat = latency.get('avg', 0)
        p95_lat = latency.get('p95', 0)

        print(
            f"{model_name:<40} "
            f"{avg_lat:>13.2f}ms "
            f"{p95_lat:>13.2f}ms "
            f"{accuracy:>10.4f} "
            f"{recall:>12.4f} "
            f"{mrr:>10.4f}"
        )

    print("="*120)


def print_reranking_comparison(reranking_effects: dict):
    """리랭킹 효과 비교 출력"""
    print("\n" + "="*100)
    print("리랭킹 효과 비교")
    print("="*100)
    print(f"{'모델명':<30} {'유사도 개선':>15} {'Latency 오버헤드':>20} {'Recall@5 개선':>18} {'NDCG@5 개선':>18}")
    print("-"*100)

    for model_name, improvements in reranking_effects.items():
        sim_imp = improvements.get('similarity', 0)
        lat_over = improvements.get('latency_overhead', 0)
        recall_imp = improvements.get('recall_at_5', 0)
        ndcg_imp = improvements.get('ndcg_at_5', 0)

        print(
            f"{model_name:<30} "
            f"{sim_imp:>13.2f}% "
            f"{lat_over:>18.2f}ms "
            f"{recall_imp:>18.4f} "
            f"{ndcg_imp:>18.4f}"
        )

    print("="*100)


def embed_all_models(
    data_file: str,
    db_config: dict
) -> bool:
    """5개 모델로 데이터 임베딩"""
    try:
        logger.info("=== 5개 모델 임베딩 생성 시작 ===")

        if not Path(data_file).exists():
            logger.error(f"데이터 파일을 찾을 수 없습니다: {data_file}")
            return False

        embedder = MultiModelEmbedder(data_file, db_config)
        results = embedder.embed_all_models()

        # 결과 요약 출력
        print(embedder.get_summary())

        # 성공한 모델 확인
        successful = [k for k, v in results.items() if v.get("status") == "success"]

        if successful:
            logger.info(f"✅ {len(successful)}개 모델 임베딩 완료")
            return True
        else:
            logger.error("❌ 모든 모델 임베딩 실패")
            return False

    except Exception as e:
        logger.exception(f"임베딩 생성 중 오류 발생: {e}")
        return False


def main():
    # 환경 변수 설정
    os.environ.setdefault("PG_USER", "postgres")
    os.environ.setdefault("PG_PASSWORD", "post1234")
    os.environ.setdefault("PG_HOST", "localhost")
    os.environ.setdefault("PG_PORT", "5432")
    os.environ.setdefault("PG_DB", "rey")

    parser = argparse.ArgumentParser(
        description="rag-eval: RAG 시스템 평가 도구"
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="상세 로그 출력")

    subparsers = parser.add_subparsers(dest="command", help="사용 가능한 명령어")

    # 모델 목록
    p_list = subparsers.add_parser("list", help="사용 가능한 모델 목록")

    # 단일 모델 평가
    p_model = subparsers.add_parser("model", help="단일 모델 평가")
    p_model.add_argument(
        "--model",
        type=str,
        required=True,
        choices=[m.name for m in EmbeddingModelType],
        help="평가할 모델"
    )
    p_model.add_argument("--top-k", type=int, default=5, help="검색할 결과 수 (기본: 5)")
    p_model.add_argument("--reranking", action="store_true", help="리랭킹 사용")
    p_model.add_argument("--no-save", action="store_true", help="결과 저장 안 함")
    p_model.add_argument("--save-search-results", action="store_true", help="검색 결과도 함께 저장 (파일 크기 증가)")

    # 전체 모델 평가
    p_all = subparsers.add_parser("all", help="전체 모델 평가")
    p_all.add_argument("--top-k", type=int, default=5, help="검색할 결과 수 (기본: 5)")
    p_all.add_argument("--no-save", action="store_true", help="결과 저장 안 함")
    p_all.add_argument("--save-search-results", action="store_true", help="검색 결과도 함께 저장 (파일 크기 증가)")

    # 리랭킹 비교
    p_rerank = subparsers.add_parser("reranking", help="리랭킹 전후 성능 비교")
    p_rerank.add_argument("--top-k", type=int, default=5, help="검색할 결과 수 (기본: 5)")
    p_rerank.add_argument("--no-save", action="store_true", help="결과 저장 안 함")
    p_rerank.add_argument("--save-search-results", action="store_true", help="검색 결과도 함께 저장 (파일 크기 증가)")

    # 임베딩 생성
    p_embed = subparsers.add_parser("embed", help="5개 모델로 데이터 임베딩")
    p_embed.add_argument(
        "--data-file",
        type=str,
        required=True,
        help="임베딩할 JSON 데이터 파일"
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # DB 연결 테스트
    if args.command not in ['list']:
        logger.info("DB 연결 테스트 중...")
        if not test_connection():
            logger.error("DB 연결 실패")
            sys.exit(1)
        logger.info("DB 연결 성공")

    db_config = get_db_config()

    success = False

    # 명령어 실행
    if args.command == "list":
        list_models()
        success = True

    elif args.command == "model":
        model_type = EmbeddingModelType[args.model]
        success = evaluate_single_model(
            model_type=model_type,
            db_config=db_config,
            top_k=args.top_k,
            use_reranking=args.reranking,
            save_results=not args.no_save,
            save_search_results=args.save_search_results
        )

    elif args.command == "all":
        success = evaluate_all_models(
            db_config=db_config,
            top_k=args.top_k,
            compare_reranking=False,
            save_results=not args.no_save,
            save_search_results=args.save_search_results
        )

    elif args.command == "reranking":
        success = evaluate_all_models(
            db_config=db_config,
            top_k=args.top_k,
            compare_reranking=True,
            save_results=not args.no_save,
            save_search_results=args.save_search_results
        )

    elif args.command == "embed":
        success = embed_all_models(
            data_file=args.data_file,
            db_config=db_config
        )

    if success:
        logger.info(f"{args.command} 명령이 성공적으로 완료되었습니다.")
        sys.exit(0)
    else:
        logger.error(f"{args.command} 명령 실행 실패")
        sys.exit(1)


if __name__ == "__main__":
    main()
