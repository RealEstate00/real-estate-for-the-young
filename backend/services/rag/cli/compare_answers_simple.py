#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
임베딩 모델별 답변 비교 (간단 버전)
메모리 효율적으로 한 번에 1개 모델씩 실행하여 답변만 비교
"""

import sys
import os
from pathlib import Path
from datetime import datetime
import gc

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

from backend.services.rag.rag_system import RAGSystem
from backend.services.rag.models.config import EmbeddingModelType
from backend.services.rag.generation.generator import OllamaGenerator, GenerationConfig
from backend.services.rag.augmentation.formatters import EnhancedPromptFormatter
from backend.services.rag.retrieval.reranker import KeywordReranker
import logging

logging.basicConfig(level=logging.WARNING)  # 로그 최소화
logger = logging.getLogger(__name__)


def get_db_config() -> dict:
    """데이터베이스 설정"""
    return {
        'host': os.getenv('PG_HOST', 'localhost'),
        'port': os.getenv('PG_PORT', '5432'),
        'database': os.getenv('PG_DB', 'rey'),
        'user': os.getenv('PG_USER', 'postgres'),
        'password': os.getenv('PG_PASSWORD', 'post1234')
    }


def test_single_model(
    model_name: str,
    model_type: EmbeddingModelType,
    query: str,
    llm_model: str,
    db_config: dict
) -> dict:
    """단일 모델 테스트 (메모리 효율적)"""

    print(f"\n{'='*60}")
    print(f"🔍 {model_name} 모델 테스트 중...")
    print(f"{'='*60}")

    try:
        # LLM Generator 초기화
        llm_generator = OllamaGenerator(
            base_url="http://localhost:11434",
            default_model=llm_model
        )

        # Reranker 설정 (리랭킹 사용 시 LLM 키워드 추출 기본 활성화)
        reranker = KeywordReranker()  # 기본값: LLM 키워드 추출 활성화, gemma3:4b 사용

        # RAG 시스템 초기화
        rag_system = RAGSystem(
            model_type=model_type,
            db_config=db_config,
            reranker=reranker,
            formatter=EnhancedPromptFormatter(),
            llm_generator=llm_generator,
            enable_generation=True
        )

        # 검색
        print(f"1️⃣ 검색 중...")
        search_results = rag_system.search_only(query=query, top_k=3)
        avg_similarity = sum(d.get('similarity', 0) for d in search_results) / len(search_results) if search_results else 0
        print(f"   ✅ {len(search_results)}개 문서 (평균 유사도: {avg_similarity:.3f})")

        # 답변 생성
        print(f"2️⃣ 답변 생성 중...")
        full_response = rag_system.generate_answer(
            query=query,
            top_k=3,  # 메모리 절약을 위해 3개만
            use_reranker=True,  # 리랭킹 사용
            generation_config=GenerationConfig(
                model=llm_model,
                temperature=0.7,
                max_tokens=2000,
                timeout=120  # 타임아웃 120초로 설정
            )
        )

        answer = full_response.generated_answer.answer
        gen_time = full_response.generated_answer.generation_time_ms
        tokens_used = full_response.generated_answer.tokens_used
        context_length = len(full_response.augmented_context.context_text)

        print(f"   ✅ 완료 ({gen_time:.0f}ms)")
        print(f"   컨텍스트: {context_length} 글자, 생성 토큰: {tokens_used}, 답변: {len(answer)} 글자")

        # 검색된 문서 정보
        doc_sources = [
            doc.get('metadata', {}).get('source', 'N/A')
            for doc in search_results
        ]

        result = {
            "model_name": model_name,
            "answer": answer,
            "generation_time_ms": gen_time,
            "tokens_used": tokens_used,
            "context_length": context_length,
            "answer_length": len(answer),
            "avg_similarity": avg_similarity,
            "doc_sources": doc_sources,
            "success": True
        }

        # 메모리 정리
        del rag_system
        del llm_generator
        gc.collect()

        return result

    except Exception as e:
        print(f"   ❌ 오류: {e}")
        return {
            "model_name": model_name,
            "error": str(e),
            "success": False
        }


def generate_comparison_report(
    query: str,
    llm_model: str,
    results: list,
    output_dir: str
) -> str:
    """자연어 답변 중심 비교 보고서 생성"""

    os.makedirs(output_dir, exist_ok=True)

    # 파일명
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"answer_comparison_{timestamp}.md"
    filepath = os.path.join(output_dir, filename)

    # 마크다운 생성
    md = f"""# 임베딩 모델별 답변 비교

## 📋 실험 정보

- **질문**: {query}
- **LLM 모델**: {llm_model}
- **비교 모델**: {len([r for r in results if r['success']])}개
- **생성 시간**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

---

## 📊 간단 요약

| 모델 | 생성 시간 | 유사도 | 컨텍스트 길이 | 생성 토큰 | 답변 길이 | 상태 |
|------|-----------|--------|---------------|-----------|-----------|------|
"""

    for result in results:
        if result['success']:
            ctx_len = result.get('context_length', 0)
            tokens = result.get('tokens_used', 0)
            ans_len = result.get('answer_length', 0)
            md += f"| {result['model_name']} | {result['generation_time_ms']:.0f}ms | {result['avg_similarity']:.3f} | {ctx_len} | {tokens} | {ans_len} | ✅ |\n"
        else:
            md += f"| {result['model_name']} | - | - | - | - | - | ❌ |\n"

    md += "\n---\n\n"

    # 각 모델의 답변 비교
    md += "## 💬 답변 내용 비교\n\n"

    for i, result in enumerate(results, 1):
        if not result['success']:
            md += f"### {i}. ❌ {result['model_name']} 모델 - 오류\n\n"
            md += f"```\n{result.get('error', 'Unknown error')}\n```\n\n"
            md += "---\n\n"
            continue

        md += f"### {i}. {result['model_name']} 모델\n\n"

        # 검색 정보
        md += f"**검색 정보**:\n"
        md += f"- 평균 유사도: {result['avg_similarity']:.3f}\n"
        md += f"- 참고 문서: {len(result['doc_sources'])}개\n"
        for j, source in enumerate(result['doc_sources'], 1):
            md += f"  {j}. {source}\n"
        md += f"\n**생성 시간**: {result['generation_time_ms']:.0f}ms\n\n"

        # 답변
        md += f"**답변**:\n\n{result['answer']}\n\n"
        md += "---\n\n"

    # 분석
    successful = [r for r in results if r['success']]
    if len(successful) > 1:
        md += "## 🔍 답변 분석\n\n"

        # 가장 빠른 모델
        fastest = min(successful, key=lambda x: x['generation_time_ms'])
        md += f"### ⚡ 가장 빠른 답변\n**{fastest['model_name']}** ({fastest['generation_time_ms']:.0f}ms)\n\n"

        # 가장 높은 유사도
        best_sim = max(successful, key=lambda x: x['avg_similarity'])
        md += f"### 🎯 가장 높은 검색 품질\n**{best_sim['model_name']}** (유사도: {best_sim['avg_similarity']:.3f})\n\n"

        # 가장 긴 답변
        longest = max(successful, key=lambda x: len(x['answer']))
        md += f"### 📝 가장 상세한 답변\n**{longest['model_name']}** ({len(longest['answer'])} 글자)\n\n"

        md += "### 💡 권장 사항\n\n"
        md += f"- **검색 품질 우선**: {best_sim['model_name']}\n"
        md += f"- **속도 우선**: {fastest['model_name']}\n"
        md += f"- **상세함 우선**: {longest['model_name']}\n\n"

    md += "---\n\n"
    md += f"*보고서 생성: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n"

    # 저장
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(md)

    return filepath


def main():
    import argparse

    parser = argparse.ArgumentParser(description="임베딩 모델별 답변 비교 (간단 버전)")
    parser.add_argument(
        "query",
        type=str,
        nargs="?",
        default=None,
        help="단일 테스트 질문 (미지정 시 --queries-file 사용)"
    )
    parser.add_argument(
        "--llm-model",
        type=str,
        default="gemma3:4b",
        help="LLM 모델 (기본: gemma3:4b)"
    )
    parser.add_argument(
        "--models",
        type=str,
        nargs="+",
        default=["E5_SMALL", "E5_BASE", "E5_LARGE", "KAKAO"],
        help="비교할 임베딩 모델들"
    )
    parser.add_argument(
        "--queries-file",
        type=str,
        default=str(Path(__file__).resolve().parent / "test_queries.txt"),
        help="질문 목록 파일 경로 (기본: cli/test_queries.txt)"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=None,
        help="결과 저장 디렉토리 (기본: services/rag/results)"
    )

    args = parser.parse_args()

    # 모델 매핑
    model_mapping = {
        "E5_SMALL": EmbeddingModelType.MULTILINGUAL_E5_SMALL,
        "E5_BASE": EmbeddingModelType.MULTILINGUAL_E5_BASE,
        "E5_LARGE": EmbeddingModelType.MULTILINGUAL_E5_LARGE,
        "KAKAO": EmbeddingModelType.KAKAOBANK_DEBERTA
    }

    db_config = get_db_config()

    print(f"\n{'='*60}")
    print(f"임베딩 모델별 답변 비교")
    print(f"{'='*60}")
    if args.query:
        queries = [args.query]
    else:
        # 파일에서 질문 로드
        qpath = Path(args.queries_file)
        if not qpath.exists():
            raise FileNotFoundError(f"질문 파일을 찾을 수 없습니다: {qpath}")
        queries = [
            line.strip() 
            for line in qpath.read_text(encoding='utf-8').splitlines() 
            if line.strip() and not line.strip().startswith('#')
        ]

    if len(queries) == 1:
        print(f"질문: {queries[0]}")
    else:
        print(f"질문 개수: {len(queries)}")
    print(f"LLM: {args.llm_model}")
    print(f"모델: {', '.join(args.models)}")
    print(f"{'='*60}\n")

    # 기본 출력 디렉토리 설정
    output_dir = args.output_dir
    if output_dir is None:
        script_dir = Path(__file__).resolve().parent  # cli 디렉토리
        output_dir = str(script_dir.parent / "results")

    # 각 질문별 보고서 생성
    for q in queries:
        # 각 모델 테스트 (순차 실행)
        results = []
        for model_name in args.models:
            if model_name not in model_mapping:
                print(f"⚠️  '{model_name}' 모델을 찾을 수 없습니다. 건너뜀.")
                continue

            result = test_single_model(
                model_name=model_name,
                model_type=model_mapping[model_name],
                query=q,
                llm_model=args.llm_model,
                db_config=db_config
            )
            results.append(result)

        # 보고서 생성
        print(f"\n{'='*60}")
        print(f"📝 보고서 생성 중... 질문: {q[:50]}...")
        report_path = generate_comparison_report(
            query=q,
            llm_model=args.llm_model,
            results=results,
            output_dir=output_dir
        )

        print(f"\n{'='*60}")
        print(f"✅ 완료!")
        print(f"📄 보고서: {report_path}")
        print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
