"""
RAG 성능 평가기

다양한 모델의 검색 성능을 평가하고 비교합니다.
- 표준 검색 메트릭 (Precision@K, Recall@K, MRR, NDCG)
- Latency 메트릭 (percentiles)
- 한국어 이해도 메트릭
- 리랭킹 전후 성능 비교
"""

import time
import logging
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

from ..config import EmbeddingModelType
from .search import VectorRetriever
from .metrics import MetricsCalculator

logger = logging.getLogger(__name__)


class RAGEvaluator:
    """RAG 시스템의 성능을 평가하는 클래스"""

    def __init__(self, db_config: Dict[str, str] = None):
        self.db_config = db_config or {
            'host': 'localhost',
            'port': '5432',
            'database': 'rey',
            'user': 'postgres',
            'password': 'post1234'
        }

        self.metrics_calculator = MetricsCalculator()

        # 테스트 쿼리들 (test_queries.txt에서 로드)
        self.test_queries, self.expected_keywords = self._load_test_queries()

    def _load_test_queries(self) -> tuple[List[str], Dict[str, List[str]]]:
        """
        test_queries.txt 파일에서 테스트 쿼리와 예상 키워드를 로드합니다.

        Returns:
            (쿼리 리스트, 쿼리별 예상 키워드 딕셔너리)
        """
        try:
            queries_file = Path(__file__).parent.parent / "cli" / "test_queries.txt"
            queries = []
            expected_keywords = {}

            if queries_file.exists():
                with open(queries_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        # 주석이나 빈 줄 건너뛰기
                        if not line or line.startswith('#'):
                            continue

                        # "쿼리|키워드1,키워드2,..." 형식 파싱
                        if '|' in line:
                            query, keywords_str = line.split('|', 1)
                            query = query.strip()
                            keywords = [kw.strip() for kw in keywords_str.split(',')]
                            queries.append(query)
                            expected_keywords[query] = keywords
                        else:
                            # 구버전 호환성 - 키워드 없이 쿼리만
                            queries.append(line)

                logger.info(f"테스트 쿼리 {len(queries)}개 로드됨 (키워드 정의: {len(expected_keywords)}개)")
                return queries, expected_keywords
            else:
                logger.warning("test_queries.txt 파일을 찾을 수 없습니다. 기본 쿼리를 사용합니다.")
                default_queries = [
                    "신혼부부 임차보증금 이자지원",
                    "대출 한도와 소득 기준",
                    "신청 절차와 필요 서류"
                ]
                return default_queries, {}

        except Exception as e:
            logger.error(f"테스트 쿼리 로드 실패: {e}")
            return ["신혼부부 임차보증금 이자지원"], {}

    def evaluate_model(
        self,
        model_type: EmbeddingModelType,
        queries: List[str] = None,
        top_k: int = 5,
        use_reranking: bool = False,
        save_search_results: bool = False
    ) -> Dict[str, Any]:
        """
        단일 모델의 성능을 평가합니다.

        Args:
            model_type: 평가할 모델 타입
            queries: 테스트 쿼리 (None이면 기본 쿼리 사용)
            top_k: 검색할 결과 수
            use_reranking: 리랭킹 사용 여부
            save_search_results: 검색 결과를 저장할지 여부 (False=메트릭만, True=전체)

        Returns:
            평가 결과 딕셔너리
        """
        if queries is None:
            queries = self.test_queries

        logger.info(f"모델 {model_type.value} 성능 평가 시작 (리랭킹: {use_reranking})")

        retriever = VectorRetriever(model_type, self.db_config)

        try:
            # 검색 수행
            search_results = {}
            for query in queries:
                logger.info(f"쿼리 검색 중: {query}")
                start_time = time.time()

                if use_reranking:
                    results = retriever.search_with_reranking(
                        query=query,
                        top_k=top_k,
                        rerank_top_k=top_k * 4  # 4배 많이 가져와서 리랭킹
                    )
                else:
                    results = retriever.search(
                        query=query,
                        top_k=top_k
                    )

                search_time = (time.time() - start_time) * 1000  # ms

                search_results[query] = {
                    'results': results,
                    'search_time_ms': search_time,
                    'result_count': len(results)
                }

            # 성능 지표 계산 (예상 키워드 포함)
            metrics = self.metrics_calculator.calculate_metrics(
                search_results,
                expected_keywords=self.expected_keywords if self.expected_keywords else None
            )

            # 결과 정리
            evaluation_result = {
                'model_name': model_type.value,
                'total_queries': len(queries),
                'successful_queries': metrics.successful_queries,
                'use_reranking': use_reranking,
                'metrics': self.metrics_calculator.to_dict(metrics),
                'timestamp': datetime.now().isoformat()
            }

            # 검색 결과 저장 옵션 (기본: 메트릭만 저장)
            if save_search_results:
                evaluation_result['search_results'] = search_results
            else:
                # 간단한 요약만 저장
                evaluation_result['search_summary'] = {
                    'total_queries': len(search_results),
                    'avg_result_count': sum(r['result_count'] for r in search_results.values()) / len(search_results)
                }

            logger.info(f"모델 {model_type.value} 평가 완료")

            # 메트릭 출력
            self.metrics_calculator.print_metrics(metrics, model_type.value)

            return evaluation_result

        except Exception as e:
            logger.error(f"모델 {model_type.value} 평가 실패: {e}", exc_info=True)
            return {
                'model_name': model_type.value,
                'error': str(e),
                'status': 'failed',
                'timestamp': datetime.now().isoformat()
            }
        finally:
            retriever.close()

    def evaluate_all_models(
        self,
        models: List[EmbeddingModelType],
        queries: List[str] = None,
        top_k: int = 5,
        compare_reranking: bool = False,
        save_search_results: bool = False
    ) -> Dict[str, Any]:
        """
        여러 모델의 성능을 평가하고 비교합니다.

        Args:
            models: 평가할 모델 타입 리스트
            queries: 테스트 쿼리
            top_k: 검색할 결과 수
            compare_reranking: 리랭킹 전후 성능 비교 여부
            save_search_results: 검색 결과를 저장할지 여부 (기본: False)

        Returns:
            종합 평가 결과
        """
        if queries is None:
            queries = self.test_queries

        logger.info(f"{len(models)}개 모델 성능 평가 시작")

        results = {}

        for model_type in models:
            try:
                # 기본 검색 평가
                result = self.evaluate_model(
                    model_type, queries, top_k,
                    use_reranking=False,
                    save_search_results=save_search_results
                )
                results[f"{model_type.value}_baseline"] = result

                # 리랭킹 평가 (옵션)
                if compare_reranking:
                    result_reranked = self.evaluate_model(
                        model_type, queries, top_k,
                        use_reranking=True,
                        save_search_results=save_search_results
                    )
                    results[f"{model_type.value}_reranked"] = result_reranked

            except Exception as e:
                logger.error(f"모델 {model_type.value} 평가 실패: {e}")
                results[model_type.value] = {
                    'model_name': model_type.value,
                    'error': str(e),
                    'status': 'failed'
                }

        # 모델 비교
        comparison = self._compare_models(results)

        # 리랭킹 효과 비교
        reranking_comparison = None
        if compare_reranking:
            reranking_comparison = self._compare_reranking_effect(results)

        return {
            'evaluation_results': results,
            'comparison': comparison,
            'reranking_comparison': reranking_comparison,
            'summary': self._generate_summary(results, comparison),
            'timestamp': datetime.now().isoformat()
        }

    def _compare_models(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """모델들을 비교합니다."""

        successful_models = {k: v for k, v in results.items() if 'metrics' in v}

        if not successful_models:
            return {'error': 'No successful evaluations to compare'}

        # 주요 메트릭 추출
        comparisons = {
            'latency': {},
            'accuracy': {},
            'recall': {},
            'mrr': {},
            'ndcg': {}
        }

        for model_name, result in successful_models.items():
            metrics = result['metrics']

            # Latency
            if metrics.get('latency_metrics'):
                lm = metrics['latency_metrics']
                comparisons['latency'][model_name] = {
                    'avg': lm['avg_latency_ms'],
                    'p95': lm['p95_latency_ms'],
                    'p99': lm['p99_latency_ms']
                }

            # Accuracy (유사도)
            comparisons['accuracy'][model_name] = metrics.get('avg_similarity', 0)

            # Recall, MRR, NDCG (표준 메트릭이 있는 경우)
            if metrics.get('standard_metrics'):
                sm = metrics['standard_metrics']
                comparisons['recall'][model_name] = sm.get('recall_at_5', 0)
                comparisons['mrr'][model_name] = sm.get('mrr', 0)
                comparisons['ndcg'][model_name] = sm.get('ndcg_at_5', 0)

        # 순위 계산
        rankings = {}
        rankings['fastest'] = sorted(comparisons['latency'].items(),
                                     key=lambda x: x[1]['avg'])[0][0] if comparisons['latency'] else None
        rankings['most_accurate'] = sorted(comparisons['accuracy'].items(),
                                          key=lambda x: x[1], reverse=True)[0][0] if comparisons['accuracy'] else None
        rankings['best_recall'] = sorted(comparisons['recall'].items(),
                                        key=lambda x: x[1], reverse=True)[0][0] if comparisons['recall'] else None
        rankings['best_mrr'] = sorted(comparisons['mrr'].items(),
                                     key=lambda x: x[1], reverse=True)[0][0] if comparisons['mrr'] else None

        return {
            'rankings': rankings,
            'comparisons': comparisons
        }

    def _compare_reranking_effect(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """리랭킹 전후 성능 비교"""

        reranking_effects = {}

        for key, result in results.items():
            if '_baseline' in key:
                model_name = key.replace('_baseline', '')
                reranked_key = f"{model_name}_reranked"

                if reranked_key in results and 'metrics' in result and 'metrics' in results[reranked_key]:
                    baseline_metrics = result['metrics']
                    reranked_metrics = results[reranked_key]['metrics']

                    # 개선 정도 계산
                    improvements = {}

                    # 유사도 개선
                    baseline_sim = baseline_metrics.get('avg_similarity', 0)
                    reranked_sim = reranked_metrics.get('avg_similarity', 0)
                    improvements['similarity'] = ((reranked_sim - baseline_sim) / baseline_sim * 100) if baseline_sim > 0 else 0

                    # Latency 변화
                    if baseline_metrics.get('latency_metrics') and reranked_metrics.get('latency_metrics'):
                        baseline_lat = baseline_metrics['latency_metrics']['avg_latency_ms']
                        reranked_lat = reranked_metrics['latency_metrics']['avg_latency_ms']
                        improvements['latency_overhead'] = reranked_lat - baseline_lat

                    # 표준 메트릭 개선
                    if baseline_metrics.get('standard_metrics') and reranked_metrics.get('standard_metrics'):
                        baseline_sm = baseline_metrics['standard_metrics']
                        reranked_sm = reranked_metrics['standard_metrics']

                        improvements['recall_at_5'] = (reranked_sm.get('recall_at_5', 0) -
                                                      baseline_sm.get('recall_at_5', 0))
                        improvements['ndcg_at_5'] = (reranked_sm.get('ndcg_at_5', 0) -
                                                    baseline_sm.get('ndcg_at_5', 0))

                    reranking_effects[model_name] = improvements

        return reranking_effects

    def _generate_summary(self, results: Dict[str, Any], comparison: Dict[str, Any]) -> str:
        """평가 결과 요약을 생성합니다."""

        successful_count = len([r for r in results.values() if 'metrics' in r])
        failed_count = len(results) - successful_count

        rankings = comparison.get('rankings', {})

        summary = f"""
🏆 RAG 성능 평가 결과 요약
{'='*50}
📊 평가된 모델: {len(results)}개
✅ 성공: {successful_count}개
❌ 실패: {failed_count}개

🏃‍♂️ 가장 빠른 모델: {rankings.get('fastest', 'N/A')}
🎯 가장 정확한 모델: {rankings.get('most_accurate', 'N/A')}
🔍 Best Recall: {rankings.get('best_recall', 'N/A')}
⭐ Best MRR: {rankings.get('best_mrr', 'N/A')}
"""
        return summary

    def save_results(self, results: Dict[str, Any], output_path: Optional[Path] = None) -> Path:
        """평가 결과를 JSON 파일로 저장합니다."""

        if output_path is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_dir = Path(__file__).parent.parent / "results"
            output_dir.mkdir(parents=True, exist_ok=True)
            output_path = output_dir / f"evaluation_{timestamp}.json"

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2, default=str)

        logger.info(f"평가 결과 저장: {output_path}")
        return output_path
