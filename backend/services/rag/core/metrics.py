"""
성능 지표 계산기

검색 결과를 분석하여 다양한 성능 지표를 계산합니다.
- 기본 검색 메트릭 (유사도, 검색 시간)
- 정보 검색 표준 메트릭 (Precision@K, Recall@K, F1@K, MRR, NDCG)
- 한국어 이해도 메트릭 (키워드 정확도, 도메인 특화성)
- Latency 메트릭 (percentiles)
"""

import logging
import math
import numpy as np
from typing import List, Dict, Any, Optional, Set
from statistics import mean, median, stdev
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


@dataclass
class StandardMetrics:
    """정보 검색 표준 메트릭"""
    # Precision, Recall, F1
    precision_at_1: float = 0.0
    precision_at_3: float = 0.0
    precision_at_5: float = 0.0
    recall_at_1: float = 0.0
    recall_at_3: float = 0.0
    recall_at_5: float = 0.0
    f1_at_1: float = 0.0
    f1_at_3: float = 0.0
    f1_at_5: float = 0.0

    # MRR & NDCG
    mrr: float = 0.0  # Mean Reciprocal Rank
    ndcg_at_3: float = 0.0  # Normalized Discounted Cumulative Gain
    ndcg_at_5: float = 0.0

    # Hit Rate
    hit_rate_at_1: float = 0.0
    hit_rate_at_3: float = 0.0
    hit_rate_at_5: float = 0.0


@dataclass
class LatencyMetrics:
    """Latency 통계 메트릭"""
    avg_latency_ms: float = 0.0
    median_latency_ms: float = 0.0
    min_latency_ms: float = 0.0
    max_latency_ms: float = 0.0
    stddev_latency_ms: float = 0.0
    p50_latency_ms: float = 0.0  # 50th percentile
    p95_latency_ms: float = 0.0  # 95th percentile
    p99_latency_ms: float = 0.0  # 99th percentile


@dataclass
class KoreanMetrics:
    """한국어 특화 메트릭"""
    keyword_precision: float = 0.0
    keyword_recall: float = 0.0
    keyword_f1: float = 0.0
    domain_specificity: float = 0.0
    semantic_coherence: float = 0.0


@dataclass
class ComprehensiveMetrics:
    """종합 메트릭"""
    # 기본 통계
    total_queries: int = 0
    successful_queries: int = 0
    success_rate: float = 0.0
    total_results: int = 0
    avg_result_count: float = 0.0

    # 유사도 메트릭
    avg_similarity: float = 0.0
    min_similarity: float = 0.0
    max_similarity: float = 0.0
    stddev_similarity: float = 0.0

    # 표준 메트릭
    standard_metrics: Optional[StandardMetrics] = None

    # Latency 메트릭
    latency_metrics: Optional[LatencyMetrics] = None

    # 한국어 메트릭
    korean_metrics: Optional[KoreanMetrics] = None


class MetricsCalculator:
    """성능 지표를 계산하는 클래스"""

    def __init__(self):
        self.korean_keywords = [
            '신혼부부', '임차보증금', '이자지원', '대출', '한도', '소득', '기준',
            '신청', '절차', '서류', '금리', '기간', '대상주택', '조건', '제외사항',
            '반환보증', '보증료', '연장', '중단', '예비신혼부부', '자격', '청년',
            '전세', '월세', '버팀목', '주거급여', '서울형', '바우처', '긴급', '복지'
        ]

    def _safe_stdev(self, values: List[float]) -> float:
        """안전한 표준편차 계산 (NaN/Inf 값 처리)"""
        if not values or len(values) < 2:
            return 0.0
        
        # NaN, Inf 값 필터링
        clean_values = []
        for v in values:
            if isinstance(v, (int, float)) and not (math.isnan(v) or math.isinf(v)):
                clean_values.append(v)
        
        if len(clean_values) < 2:
            return 0.0
            
        try:
            return stdev(clean_values)
        except (ValueError, TypeError, AttributeError):
            # stdev 함수에서 오류 발생 시 numpy 사용
            return float(np.std(clean_values))

    def calculate_metrics(
        self,
        search_results: Dict[str, Dict[str, Any]],
        expected_keywords: Optional[Dict[str, List[str]]] = None
    ) -> ComprehensiveMetrics:
        """
        검색 결과로부터 종합 성능 지표를 계산합니다.

        Args:
            search_results: 검색 결과 딕셔너리 {query: {results, search_time_ms, result_count}}
            expected_keywords: 쿼리별 예상 키워드 딕셔너리 {query: [keywords]}

        Returns:
            종합 메트릭
        """
        if not search_results:
            return ComprehensiveMetrics()

        # 기본 통계
        search_times = [result['search_time_ms'] for result in search_results.values()]
        result_counts = [result['result_count'] for result in search_results.values()]

        # 유사도 계산 (결과가 있는 경우, NaN/Inf 필터링)
        similarities = []
        for result in search_results.values():
            if result['results']:
                for r in result['results']:
                    sim = r.get('similarity', 0)
                    # NaN, Inf 값 필터링
                    if isinstance(sim, (int, float)) and not (math.isnan(sim) or math.isinf(sim)):
                        similarities.append(sim)

        # 기본 메트릭
        total_queries = len(search_results)
        successful_queries = len([r for r in result_counts if r > 0])
        success_rate = successful_queries / total_queries if total_queries else 0

        # Latency 메트릭 계산
        latency_metrics = self._calculate_latency_metrics(search_times)

        # 표준 메트릭 계산 (예상 키워드가 있는 경우)
        standard_metrics = None
        if expected_keywords:
            standard_metrics = self._calculate_standard_metrics(search_results, expected_keywords)

        # 한국어 메트릭 계산
        korean_metrics = self._calculate_korean_metrics(search_results, expected_keywords)

        return ComprehensiveMetrics(
            total_queries=total_queries,
            successful_queries=successful_queries,
            success_rate=success_rate,
            total_results=sum(result_counts),
            avg_result_count=mean(result_counts) if result_counts else 0,

            # 유사도 메트릭
            avg_similarity=mean(similarities) if similarities else 0,
            min_similarity=min(similarities) if similarities else 0,
            max_similarity=max(similarities) if similarities else 0,
            stddev_similarity=self._safe_stdev(similarities),

            # 서브 메트릭
            standard_metrics=standard_metrics,
            latency_metrics=latency_metrics,
            korean_metrics=korean_metrics
        )

    def _calculate_latency_metrics(self, search_times: List[float]) -> LatencyMetrics:
        """Latency 메트릭 계산 (percentiles 포함)"""
        if not search_times:
            return LatencyMetrics()

        sorted_times = sorted(search_times)

        return LatencyMetrics(
            avg_latency_ms=mean(search_times),
            median_latency_ms=median(search_times),
            min_latency_ms=min(search_times),
            max_latency_ms=max(search_times),
            stddev_latency_ms=self._safe_stdev(search_times),
            p50_latency_ms=np.percentile(sorted_times, 50),
            p95_latency_ms=np.percentile(sorted_times, 95),
            p99_latency_ms=np.percentile(sorted_times, 99)
        )

    def _calculate_standard_metrics(
        self,
        search_results: Dict[str, Dict[str, Any]],
        expected_keywords: Dict[str, List[str]]
    ) -> StandardMetrics:
        """정보 검색 표준 메트릭 계산 (Precision@K, Recall@K, F1@K, MRR, NDCG)"""

        precisions_at_k = {1: [], 3: [], 5: []}
        recalls_at_k = {1: [], 3: [], 5: []}
        f1s_at_k = {1: [], 3: [], 5: []}
        hit_rates_at_k = {1: [], 3: [], 5: []}
        mrr_scores = []
        ndcg_scores_at_3 = []
        ndcg_scores_at_5 = []

        for query, result in search_results.items():
            if query not in expected_keywords:
                continue

            expected = set(expected_keywords[query])
            results = result['results']

            if not results:
                # 결과 없음 - 모든 메트릭 0
                for k in [1, 3, 5]:
                    precisions_at_k[k].append(0.0)
                    recalls_at_k[k].append(0.0)
                    f1s_at_k[k].append(0.0)
                    hit_rates_at_k[k].append(0.0)
                mrr_scores.append(0.0)
                ndcg_scores_at_3.append(0.0)
                ndcg_scores_at_5.append(0.0)
                continue

            # Precision@K, Recall@K, F1@K 계산
            for k in [1, 3, 5]:
                top_k_results = results[:k]
                top_k_keywords = set()

                for r in top_k_results:
                    content = r.get('content', '').lower()
                    found = [kw for kw in expected if kw.lower() in content]
                    top_k_keywords.update(found)

                # Precision@K = 상위 K개 중 정답인 비율
                precision = len(top_k_keywords) / min(k, len(results)) if results else 0.0

                # Recall@K = 전체 정답 중 상위 K개에서 찾은 비율
                recall = len(top_k_keywords) / len(expected) if expected else 0.0

                # F1@K
                f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0

                # Hit Rate@K = 상위 K개 중 최소 1개 이상 정답이 있는지
                hit_rate = 1.0 if top_k_keywords else 0.0

                precisions_at_k[k].append(precision)
                recalls_at_k[k].append(recall)
                f1s_at_k[k].append(f1)
                hit_rates_at_k[k].append(hit_rate)

            # MRR (Mean Reciprocal Rank) - 첫 번째 정답의 순위
            first_relevant_rank = None
            for idx, r in enumerate(results, 1):
                content = r.get('content', '').lower()
                if any(kw.lower() in content for kw in expected):
                    first_relevant_rank = idx
                    break

            mrr = 1.0 / first_relevant_rank if first_relevant_rank else 0.0
            mrr_scores.append(mrr)

            # NDCG@K (Normalized Discounted Cumulative Gain)
            ndcg_scores_at_3.append(self._calculate_ndcg(results[:3], expected))
            ndcg_scores_at_5.append(self._calculate_ndcg(results[:5], expected))

        return StandardMetrics(
            precision_at_1=mean(precisions_at_k[1]) if precisions_at_k[1] else 0.0,
            precision_at_3=mean(precisions_at_k[3]) if precisions_at_k[3] else 0.0,
            precision_at_5=mean(precisions_at_k[5]) if precisions_at_k[5] else 0.0,
            recall_at_1=mean(recalls_at_k[1]) if recalls_at_k[1] else 0.0,
            recall_at_3=mean(recalls_at_k[3]) if recalls_at_k[3] else 0.0,
            recall_at_5=mean(recalls_at_k[5]) if recalls_at_k[5] else 0.0,
            f1_at_1=mean(f1s_at_k[1]) if f1s_at_k[1] else 0.0,
            f1_at_3=mean(f1s_at_k[3]) if f1s_at_k[3] else 0.0,
            f1_at_5=mean(f1s_at_k[5]) if f1s_at_k[5] else 0.0,
            mrr=mean(mrr_scores) if mrr_scores else 0.0,
            ndcg_at_3=mean(ndcg_scores_at_3) if ndcg_scores_at_3 else 0.0,
            ndcg_at_5=mean(ndcg_scores_at_5) if ndcg_scores_at_5 else 0.0,
            hit_rate_at_1=mean(hit_rates_at_k[1]) if hit_rates_at_k[1] else 0.0,
            hit_rate_at_3=mean(hit_rates_at_k[3]) if hit_rates_at_k[3] else 0.0,
            hit_rate_at_5=mean(hit_rates_at_k[5]) if hit_rates_at_k[5] else 0.0,
        )

    def _calculate_ndcg(self, results: List[Dict[str, Any]], expected_keywords: Set[str]) -> float:
        """NDCG (Normalized Discounted Cumulative Gain) 계산"""
        if not results:
            return 0.0

        # DCG 계산
        dcg = 0.0
        for idx, r in enumerate(results, 1):
            content = r.get('content', '').lower()
            # Relevance: 예상 키워드가 있으면 1, 없으면 0
            relevance = 1.0 if any(kw.lower() in content for kw in expected_keywords) else 0.0
            # DCG formula: sum(rel_i / log2(i + 1))
            dcg += relevance / np.log2(idx + 1)

        # IDCG (Ideal DCG) 계산 - 모든 결과가 정답인 경우
        idcg = sum(1.0 / np.log2(idx + 1) for idx in range(1, min(len(results), len(expected_keywords)) + 1))

        # NDCG = DCG / IDCG
        return dcg / idcg if idcg > 0 else 0.0

    def _calculate_korean_metrics(
        self,
        search_results: Dict[str, Dict[str, Any]],
        expected_keywords: Optional[Dict[str, List[str]]] = None
    ) -> KoreanMetrics:
        """한국어 이해도 관련 지표를 계산합니다."""

        if not search_results:
            return KoreanMetrics()

        # 키워드 정확도 (expected_keywords가 있는 경우)
        keyword_precision = 0.0
        keyword_recall = 0.0
        keyword_f1 = 0.0

        if expected_keywords:
            precisions = []
            recalls = []

            for query, result in search_results.items():
                if query not in expected_keywords or not result['results']:
                    continue

                expected = set(expected_keywords[query])
                found_keywords = set()

                for r in result['results']:
                    content = r.get('content', '').lower()
                    for keyword in expected:
                        if keyword.lower() in content:
                            found_keywords.add(keyword)

                # Precision: 찾은 키워드 중 정확한 비율
                prec = len(found_keywords) / len(expected) if expected else 0.0
                # Recall: 전체 키워드 중 찾은 비율
                rec = len(found_keywords) / len(expected) if expected else 0.0

                precisions.append(prec)
                recalls.append(rec)

            keyword_precision = mean(precisions) if precisions else 0.0
            keyword_recall = mean(recalls) if recalls else 0.0
            keyword_f1 = (2 * keyword_precision * keyword_recall) / (keyword_precision + keyword_recall) \
                if (keyword_precision + keyword_recall) > 0 else 0.0

        # 도메인 특화성 평가
        domain_scores = []
        for result in search_results.values():
            if not result['results']:
                continue

            for r in result['results']:
                content = r.get('content', '').lower()
                found_count = sum(1 for kw in self.korean_keywords if kw in content)
                domain_score = found_count / len(self.korean_keywords)
                domain_scores.append(domain_score)

        domain_specificity = mean(domain_scores) if domain_scores else 0.0

        # 의미적 일관성 (유사도 기반)
        coherence_scores = []
        for result in search_results.values():
            if result['results']:
                avg_sim = mean([r.get('similarity', 0) for r in result['results']])
                coherence_scores.append(avg_sim)

        semantic_coherence = mean(coherence_scores) if coherence_scores else 0.0

        return KoreanMetrics(
            keyword_precision=keyword_precision,
            keyword_recall=keyword_recall,
            keyword_f1=keyword_f1,
            domain_specificity=domain_specificity,
            semantic_coherence=semantic_coherence
        )

    def calculate_model_comparison(self, model_results: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """여러 모델의 결과를 비교합니다."""

        if not model_results:
            return {}

        # 각 모델의 지표 추출
        model_metrics = {}
        for model_name, result in model_results.items():
            if 'metrics' in result:
                model_metrics[model_name] = result['metrics']

        if not model_metrics:
            return {'error': 'No valid model metrics found'}

        # 비교 지표 계산
        comparison = {
            'total_models': len(model_metrics),
            'rankings': {}
        }

        # 각 지표별 순위 계산
        metrics_to_rank = [
            ('avg_search_time_ms', False),  # 낮을수록 좋음
            ('avg_similarity', True),       # 높을수록 좋음
            ('success_rate', True),         # 높을수록 좋음
            ('korean_understanding_score', True)  # 높을수록 좋음
        ]

        for metric_name, higher_is_better in metrics_to_rank:
            values = {}
            for model_name, metrics in model_metrics.items():
                if metric_name in metrics:
                    values[model_name] = metrics[metric_name]

            if values:
                sorted_models = sorted(values.items(), key=lambda x: x[1], reverse=higher_is_better)
                comparison['rankings'][metric_name] = sorted_models

        return comparison

    def to_dict(self, metrics: ComprehensiveMetrics) -> Dict[str, Any]:
        """메트릭을 딕셔너리로 변환"""
        result = asdict(metrics)
        return result

    def print_metrics(self, metrics: ComprehensiveMetrics, model_name: str = "Unknown"):
        """메트릭을 보기 좋게 출력"""
        print(f"\n{'='*80}")
        print(f"📊 {model_name} 성능 메트릭")
        print(f"{'='*80}")

        # 기본 통계
        print(f"\n[기본 통계]")
        print(f"  총 쿼리: {metrics.total_queries}")
        print(f"  성공한 쿼리: {metrics.successful_queries}")
        print(f"  성공률: {metrics.success_rate:.2%}")
        print(f"  평균 결과 수: {metrics.avg_result_count:.2f}")

        # Latency 메트릭
        if metrics.latency_metrics:
            lm = metrics.latency_metrics
            print(f"\n[Latency 메트릭]")
            print(f"  평균: {lm.avg_latency_ms:.2f}ms")
            print(f"  중앙값: {lm.median_latency_ms:.2f}ms")
            print(f"  P50: {lm.p50_latency_ms:.2f}ms")
            print(f"  P95: {lm.p95_latency_ms:.2f}ms")
            print(f"  P99: {lm.p99_latency_ms:.2f}ms")
            print(f"  최소: {lm.min_latency_ms:.2f}ms")
            print(f"  최대: {lm.max_latency_ms:.2f}ms")

        # 유사도 메트릭
        print(f"\n[유사도 메트릭]")
        print(f"  평균: {metrics.avg_similarity:.4f}")
        print(f"  최소: {metrics.min_similarity:.4f}")
        print(f"  최대: {metrics.max_similarity:.4f}")
        print(f"  표준편차: {metrics.stddev_similarity:.4f}")

        # 표준 메트릭
        if metrics.standard_metrics:
            sm = metrics.standard_metrics
            print(f"\n[정보 검색 표준 메트릭]")
            print(f"  Precision@1: {sm.precision_at_1:.4f}")
            print(f"  Precision@3: {sm.precision_at_3:.4f}")
            print(f"  Precision@5: {sm.precision_at_5:.4f}")
            print(f"  Recall@1: {sm.recall_at_1:.4f}")
            print(f"  Recall@3: {sm.recall_at_3:.4f}")
            print(f"  Recall@5: {sm.recall_at_5:.4f}")
            print(f"  F1@1: {sm.f1_at_1:.4f}")
            print(f"  F1@3: {sm.f1_at_3:.4f}")
            print(f"  F1@5: {sm.f1_at_5:.4f}")
            print(f"  MRR: {sm.mrr:.4f}")
            print(f"  NDCG@3: {sm.ndcg_at_3:.4f}")
            print(f"  NDCG@5: {sm.ndcg_at_5:.4f}")
            print(f"  Hit Rate@1: {sm.hit_rate_at_1:.4f}")
            print(f"  Hit Rate@3: {sm.hit_rate_at_3:.4f}")
            print(f"  Hit Rate@5: {sm.hit_rate_at_5:.4f}")

        # 한국어 메트릭
        if metrics.korean_metrics:
            km = metrics.korean_metrics
            print(f"\n[한국어 이해도 메트릭]")
            print(f"  키워드 Precision: {km.keyword_precision:.4f}")
            print(f"  키워드 Recall: {km.keyword_recall:.4f}")
            print(f"  키워드 F1: {km.keyword_f1:.4f}")
            print(f"  도메인 특화성: {km.domain_specificity:.4f}")
            print(f"  의미적 일관성: {km.semantic_coherence:.4f}")

        print(f"{'='*80}\n")
