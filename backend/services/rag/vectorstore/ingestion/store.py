#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
pgvector 저장 모듈
임베딩된 데이터를 PostgreSQL의 pgvector 테이블에 저장
"""

import sys
import logging
import psycopg2
from psycopg2.extras import execute_batch
from typing import List, Dict, Any, Optional
from pathlib import Path
from datetime import datetime

# 프로젝트 루트 경로 추가
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

from backend.services.rag.models.config import EmbeddingModelType, get_model_config

logger = logging.getLogger(__name__)


class PgVectorStore:
    """pgvector 저장소 클래스"""

    def __init__(
        self,
        db_config: Optional[Dict[str, str]] = None
    ):
        """
        Args:
            db_config: DB 연결 정보 {'host', 'port', 'database', 'user', 'password'}
        """
        if db_config is None:
            # 기본 설정 (환경변수나 config 파일에서 가져올 수 있음)
            import os
            db_config = {
                'host': os.getenv('PG_HOST', 'localhost'),
                'port': os.getenv('PG_PORT', '5432'),
                'database': os.getenv('PG_DB', 'rey'),
                'user': os.getenv('PG_USER', 'postgres'),
                'password': os.getenv('PG_PASSWORD', 'post1234')
            }

        self.db_config = db_config
        self.conn = None
        self.cursor = None

        logger.info(f"PgVectorStore initialized for DB: {db_config['database']}")

    def connect(self):
        """데이터베이스 연결"""
        if self.conn is None or self.conn.closed:
            try:
                self.conn = psycopg2.connect(**self.db_config)
                self.cursor = self.conn.cursor()
                logger.info("Connected to PostgreSQL")
            except Exception as e:
                logger.error(f"Database connection failed: {e}")
                raise

    def disconnect(self):
        """데이터베이스 연결 종료"""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
        logger.info("Disconnected from PostgreSQL")

    def ensure_model_exists(self, model_type: EmbeddingModelType) -> int:
        """
        임베딩 모델이 DB에 등록되어 있는지 확인하고 model_id 반환

        Args:
            model_type: 임베딩 모델 타입

        Returns:
            model_id
        """
        self.connect()

        config = get_model_config(model_type)

        # 모델이 이미 존재하는지 확인
        self.cursor.execute(
            "SELECT id FROM vector_db.embedding_models WHERE model_name = %s",
            (config.model_name,)
        )
        result = self.cursor.fetchone()

        if result:
            model_id = result[0]
            logger.info(f"Model already exists: {config.display_name} (ID: {model_id})")
        else:
            # 모델 정보 삽입 (schema.sql에 이미 초기 데이터가 있으면 중복 방지)
            self.cursor.execute("""
                INSERT INTO vector_db.embedding_models
                (model_name, display_name, dimension, max_seq_length, pooling_mode, notes)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (model_name) DO NOTHING
                RETURNING id
            """, (
                config.model_name,
                config.display_name,
                config.dimension,
                config.max_seq_length,
                config.pooling_mode,
                config.notes
            ))

            result = self.cursor.fetchone()
            if result:
                model_id = result[0]
            else:
                # ON CONFLICT로 인해 INSERT가 실행되지 않은 경우 다시 SELECT
                self.cursor.execute(
                    "SELECT id FROM vector_db.embedding_models WHERE model_name = %s",
                    (config.model_name,)
                )
                model_id = self.cursor.fetchone()[0]

            self.conn.commit()
            logger.info(f"Model registered: {config.display_name} (ID: {model_id})")

        return model_id

    def insert_documents_with_embeddings(
        self,
        documents: List[Dict[str, Any]],
        model_type: EmbeddingModelType,
        source_type: str = "finance_support",
        batch_size: int = 100
    ) -> int:
        """
        문서와 임베딩을 pgvector에 저장 (모델별 테이블)

        Args:
            documents: 문서 리스트 [{'id', 'source', 'content', 'embedding'}]
            model_type: 사용된 임베딩 모델
            source_type: 데이터 소스 타입
            batch_size: 배치 크기

        Returns:
            저장된 문서 수
        """
        self.connect()

        # 모델별 테이블 이름 매핑
        table_mapping = {
            EmbeddingModelType.MULTILINGUAL_E5_SMALL: 'embeddings_e5_small',
            EmbeddingModelType.KAKAOBANK_DEBERTA: 'embeddings_kakaobank',
            EmbeddingModelType.QWEN_EMBEDDING: 'embeddings_qwen3',
            EmbeddingModelType.EMBEDDING_GEMMA: 'embeddings_gemma',
        }

        embedding_table = table_mapping.get(model_type)
        if not embedding_table:
            raise ValueError(f"Unknown model type: {model_type}")

        inserted_count = 0

        try:
            for i in range(0, len(documents), batch_size):
                batch = documents[i:i + batch_size]

                for doc in batch:
                    # 1. document_sources 삽입
                    self.cursor.execute("""
                        INSERT INTO vector_db.document_sources (source_type, source_id, metadata)
                        VALUES (%s, %s, %s)
                        RETURNING id
                    """, (
                        source_type,
                        doc.get('source', ''),
                        psycopg2.extras.Json({
                            'original_id': doc.get('id', ''),
                            'source_file': doc.get('source', '')
                        })
                    ))
                    source_id = self.cursor.fetchone()[0]

                    # 2. document_chunks 삽입
                    self.cursor.execute("""
                        INSERT INTO vector_db.document_chunks
                        (source_id, chunk_index, content, chunk_type, token_count, metadata)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        RETURNING id
                    """, (
                        source_id,
                        0,  # 이미 청크된 데이터이므로 0
                        doc.get('content', ''),
                        'text',
                        len(doc.get('content', '').split()),  # 간단한 토큰 수 계산
                        psycopg2.extras.Json({
                            'original_id': doc.get('id', ''),
                            'source': doc.get('source', '')
                        })
                    ))
                    chunk_id = self.cursor.fetchone()[0]

                    # 3. 모델별 임베딩 테이블에 삽입
                    embedding = doc.get('embedding', [])
                    if embedding:
                        # pgvector 형식으로 변환
                        embedding_str = '[' + ','.join(map(str, embedding)) + ']'

                        # 동적 테이블 이름 사용
                        self.cursor.execute(f"""
                            INSERT INTO vector_db.{embedding_table} (chunk_id, embedding)
                            VALUES (%s, %s::vector)
                        """, (chunk_id, embedding_str))

                    inserted_count += 1

                # 배치 커밋
                self.conn.commit()
                logger.info(f"Inserted {min(i + batch_size, len(documents))}/{len(documents)} documents")

            logger.info(f"Successfully inserted {inserted_count} documents with {model_type.value}")

        except Exception as e:
            self.conn.rollback()
            logger.error(f"Error inserting documents: {e}")
            raise

        return inserted_count

    def create_vector_index(self, model_type: EmbeddingModelType, lists: int = 100):
        """
        벡터 인덱스 생성 (더 이상 사용 안 함 - 스키마에서 자동 생성됨)

        모델별 테이블 구조로 변경되면서 HNSW 인덱스가 schema.sql에서 자동 생성됩니다.
        이 메서드는 하위 호환성을 위해 남겨두되, 아무 작업도 하지 않습니다.

        Args:
            model_type: 임베딩 모델
            lists: (사용 안 함)
        """
        config = get_model_config(model_type)
        logger.info(f"Vector index for {config.display_name} already created in schema.sql")
        # 인덱스는 이미 schema.sql에서 생성되므로 아무 작업 안 함
        pass

    def search_similar(
        self,
        query_embedding: List[float],
        model_type: EmbeddingModelType,
        top_k: int = 5,
        min_similarity: float = 0.0
    ) -> List[Dict[str, Any]]:
        """
        유사도 검색

        Args:
            query_embedding: 쿼리 임베딩 벡터
            model_type: 사용할 모델
            top_k: 반환할 결과 수
            min_similarity: 최소 유사도

        Returns:
            검색 결과 리스트
        """
        self.connect()

        config = get_model_config(model_type)

        # 벡터 문자열 생성
        query_embedding_str = '[' + ','.join(map(str, query_embedding)) + ']'

        try:
            # SQL 함수 사용
            self.cursor.execute(
                """
                SELECT chunk_id, content, similarity, metadata
                FROM search_similar_chunks(%s::vector, %s, %s, %s)
                """,
                (query_embedding_str, config.model_name, top_k, min_similarity)
            )

            results = []
            for row in self.cursor.fetchall():
                results.append({
                    'chunk_id': row[0],
                    'content': row[1],
                    'similarity': float(row[2]),
                    'metadata': row[3]
                })

            logger.info(f"Found {len(results)} similar documents")
            return results

        except Exception as e:
            logger.error(f"Error searching: {e}")
            raise

    def get_statistics(self) -> Dict[str, Any]:
        """데이터베이스 통계 조회"""
        self.connect()

        try:
            # 모델별 임베딩 수
            self.cursor.execute("""
                SELECT
                    em.display_name,
                    COUNT(ce.id) as embedding_count,
                    em.dimension
                FROM vector_db.embedding_models em
                LEFT JOIN vector_db.chunk_embeddings ce ON em.id = ce.model_id
                GROUP BY em.id, em.display_name, em.dimension
                ORDER BY embedding_count DESC
            """)

            model_stats = []
            for row in self.cursor.fetchall():
                model_stats.append({
                    'model_name': row[0],
                    'embedding_count': row[1],
                    'dimension': row[2]
                })

            # 전체 통계
            self.cursor.execute("SELECT COUNT(*) FROM vector_db.document_sources")
            total_sources = self.cursor.fetchone()[0]

            self.cursor.execute("SELECT COUNT(*) FROM vector_db.document_chunks")
            total_chunks = self.cursor.fetchone()[0]

            self.cursor.execute("SELECT COUNT(*) FROM vector_db.chunk_embeddings")
            total_embeddings = self.cursor.fetchone()[0]

            return {
                'total_sources': total_sources,
                'total_chunks': total_chunks,
                'total_embeddings': total_embeddings,
                'model_statistics': model_stats
            }

        except Exception as e:
            logger.error(f"Error getting statistics: {e}")
            raise

    def __enter__(self):
        """Context manager 진입"""
        self.connect()
        return self

    def execute_query(self, query: str, params: tuple = None):
        """SQL 쿼리를 실행하고 결과를 반환합니다."""
        if not self.conn:
            raise Exception("데이터베이스에 연결되지 않았습니다.")
        
        try:
            with self.conn.cursor() as cursor:
                cursor.execute(query, params)
                if query.strip().upper().startswith('SELECT'):
                    return cursor.fetchall()
                else:
                    self.conn.commit()
                    return cursor.rowcount
        except Exception as e:
            logger.error(f"쿼리 실행 오류: {e}")
            raise

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager 종료"""
        self.disconnect()


if __name__ == "__main__":
    # 테스트
    logging.basicConfig(level=logging.INFO)

    with PgVectorStore() as store:
        # 통계 조회
        stats = store.get_statistics()
        print("\n=== Database Statistics ===")
        print(f"Total sources: {stats['total_sources']}")
        print(f"Total chunks: {stats['total_chunks']}")
        print(f"Total embeddings: {stats['total_embeddings']}")
        print("\nModel Statistics:")
        for model_stat in stats['model_statistics']:
            print(f"  {model_stat['model_name']}: {model_stat['embedding_count']} embeddings ({model_stat['dimension']} dim)")
