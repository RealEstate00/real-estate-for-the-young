"""
다중 모델 임베딩 생성기

5개 모델로 문서를 임베딩하여 벡터 데이터베이스에 저장합니다.
"""

import time
import logging
from typing import List, Dict, Any
from pathlib import Path

from ..config import EmbeddingModelType
from ..ingest_data import DataIngestionPipeline
from ..storage.ingestion.store import PgVectorStore

logger = logging.getLogger(__name__)


class MultiModelEmbedder:
    """5개 모델로 데이터를 임베딩하는 클래스"""

    def __init__(self, data_file_path: str, db_config: Dict[str, str] = None, models_to_use: List[EmbeddingModelType] = None):
        self.data_file_path = data_file_path

        # 사용할 모델 지정 (기본값: 모든 모델)
        if models_to_use is None:
            # 5개 모델 정의
            self.models = [
                EmbeddingModelType.MULTILINGUAL_E5_SMALL,  # 384차원
                EmbeddingModelType.KAKAOBANK_DEBERTA,      # 768차원
                EmbeddingModelType.QWEN_EMBEDDING,         # 1024차원
                EmbeddingModelType.EMBEDDING_GEMMA         # 768차원
            ]
        else:
            self.models = models_to_use
        
        # 데이터베이스 설정
        self.db_config = db_config or {
            'host': 'localhost',
            'port': '5432',
            'database': 'rey',
            'user': 'postgres',
            'password': 'post1234'
        }
        
        self.results = {}
    
    def embed_all_models(self) -> Dict[str, Any]:
        """5개 모델로 모두 임베딩을 생성합니다."""
        
        logger.info("🚀 5개 모델 데이터 임베딩 시작")
        
        for i, model_type in enumerate(self.models, 1):
            logger.info(f"📊 [{i}/{len(self.models)}] {model_type.value} 임베딩 생성 중...")
            
            try:
                self._embed_single_model(model_type)
                logger.info(f"✅ {model_type.value} 임베딩 생성 완료")
                
            except Exception as e:
                logger.error(f"❌ {model_type.value} 임베딩 생성 실패: {e}")
                self.results[model_type.value] = {"error": str(e)}
                continue
        
        return self.results
    
    def _embed_single_model(self, model_type: EmbeddingModelType):
        """단일 모델로 임베딩을 생성합니다."""
        
        start_time = time.time()
        
        try:
            # 1. 기존 임베딩 삭제
            self._clear_model_embeddings(model_type)
            
            # 2. 파이프라인 실행
            pipeline = DataIngestionPipeline(db_config=self.db_config)
            stats = pipeline.run_full_pipeline(
                json_path=self.data_file_path,
                model_type=model_type,
                source_type="finance_support",
                chunk_size=512,
                chunk_overlap=50,
                batch_size=32
            )
            
            end_time = time.time()
            
            # 3. 결과 확인
            embedding_count = self._get_embedding_count(model_type)
            
            # 4. 결과 저장
            self.results[model_type.value] = {
                "status": "success",
                "embedding_time": end_time - start_time,
                "embedding_count": embedding_count,
                "pipeline_stats": stats
            }
            
            logger.info(f"임베딩 생성 완료: {embedding_count}개, {end_time - start_time:.2f}초")
            
        except Exception as e:
            end_time = time.time()
            self.results[model_type.value] = {
                "status": "error",
                "embedding_time": end_time - start_time,
                "error": str(e)
            }
            raise
    
    def _clear_model_embeddings(self, model_type: EmbeddingModelType):
        """특정 모델의 기존 임베딩을 삭제합니다 (모델별 테이블)."""

        # 모델별 테이블 이름 매핑
        from ..config import EmbeddingModelType
        table_mapping = {
            EmbeddingModelType.MULTILINGUAL_E5_SMALL: 'embeddings_e5_small',
            EmbeddingModelType.KAKAOBANK_DEBERTA: 'embeddings_kakaobank',
            EmbeddingModelType.QWEN_EMBEDDING: 'embeddings_qwen3',
            EmbeddingModelType.EMBEDDING_GEMMA: 'embeddings_gemma',
        }

        embedding_table = table_mapping.get(model_type)
        if not embedding_table:
            logger.warning(f"알 수 없는 모델 타입: {model_type}")
            return

        store = PgVectorStore()
        try:
            store.connect()

            # 해당 모델 테이블의 모든 임베딩 삭제
            delete_query = f"DELETE FROM vector_db.{embedding_table}"
            store.execute_query(delete_query)

            logger.info(f"{model_type.value} 기존 데이터 정리 완료")

        except Exception as e:
            logger.warning(f"기존 데이터 정리 실패: {e}")
        finally:
            store.disconnect()
    
    def _get_embedding_count(self, model_type: EmbeddingModelType) -> int:
        """특정 모델의 임베딩 개수를 조회합니다 (모델별 테이블)."""

        # 모델별 테이블 이름 매핑
        table_mapping = {
            EmbeddingModelType.MULTILINGUAL_E5_SMALL: 'embeddings_e5_small',
            EmbeddingModelType.KAKAOBANK_DEBERTA: 'embeddings_kakaobank',
            EmbeddingModelType.QWEN_EMBEDDING: 'embeddings_qwen3',
            EmbeddingModelType.EMBEDDING_GEMMA: 'embeddings_gemma',
        }

        embedding_table = table_mapping.get(model_type)
        if not embedding_table:
            logger.error(f"알 수 없는 모델 타입: {model_type}")
            return 0

        store = PgVectorStore()
        try:
            store.connect()

            count_query = f"SELECT COUNT(*) FROM vector_db.{embedding_table}"
            result = store.execute_query(count_query)
            return result[0][0] if result else 0

        except Exception as e:
            logger.error(f"임베딩 개수 조회 실패: {e}")
            return 0
        finally:
            store.disconnect()
    
    def get_summary(self) -> str:
        """임베딩 결과 요약을 반환합니다."""
        
        successful = [k for k, v in self.results.items() if v.get("status") == "success"]
        failed = [k for k, v in self.results.items() if v.get("status") == "error"]
        
        summary = f"""
🏆 임베딩 생성 결과 요약
{'='*50}
✅ 성공한 모델: {len(successful)}개
❌ 실패한 모델: {len(failed)}개

성공한 모델들:
{chr(10).join(f'  - {model}' for model in successful)}

실패한 모델들:
{chr(10).join(f'  - {model}' for model in failed)}
"""
        return summary
