#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
벡터 검색 및 검색 모듈
PostgreSQL + pgvector를 사용한 유사도 검색을 제공합니다.
"""

import psycopg
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
import logging
from sentence_transformers import SentenceTransformer
import openai
from openai import OpenAI
import os
from dotenv import load_dotenv
from datetime import datetime

# 환경 변수 로드
load_dotenv()

logger = logging.getLogger(__name__)

class VectorRetriever:
    """벡터 검색 클래스"""
    
    def __init__(self, 
                 host: str = None,
                 port: int = None,
                 database: str = None,
                 user: str = None,
                 password: str = None,
                 embedding_model: str = None,
                 use_openai: bool = False):
        # 데이터베이스 설정
        self.host = host or os.getenv('PG_HOST', 'localhost')
        self.port = port or int(os.getenv('PG_PORT', 5432))
        self.database = database or os.getenv('PG_DB', 'rey')
        self.user = user or os.getenv('PG_USER', 'postgres')
        self.password = password or os.getenv('PG_PASSWORD', 'post1234')
        
        # 임베딩 모델 설정
        self.use_openai = use_openai
        self.embedding_model = embedding_model
        
        if use_openai:
            self.client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
            logger.info("OpenAI 임베딩 모델 사용")
        else:
            model_name = embedding_model or "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
            self.model = SentenceTransformer(model_name)
            logger.info(f"로컬 임베딩 모델 사용: {model_name}")
        
        self.connection = None
    
    def connect(self):
        """데이터베이스 연결"""
        try:
            self.connection = psycopg.connect(
                host=self.host,
                port=self.port,
                database=self.database,
                user=self.user,
                password=self.password
            )
            logger.info("PostgreSQL 연결 성공")
        except Exception as e:
            logger.error(f"PostgreSQL 연결 실패: {str(e)}")
            raise
    
    def disconnect(self):
        """데이터베이스 연결 해제"""
        if self.connection:
            self.connection.close()
            logger.info("PostgreSQL 연결 해제")
    
    def generate_query_embedding(self, query: str) -> List[float]:
        """쿼리 임베딩 생성"""
        if not query.strip():
            return []
        
        try:
            if self.use_openai:
                response = self.client.embeddings.create(
                    model="text-embedding-3-small",
                    input=query
                )
                return response.data[0].embedding
            else:
                embedding = self.model.encode(query, convert_to_tensor=False)
                return embedding.tolist()
        except Exception as e:
            logger.error(f"쿼리 임베딩 생성 중 오류: {str(e)}")
            return []
    
    def vector_search(self, 
                     query: str, 
                     limit: int = 10, 
                     similarity_threshold: float = 0.7,
                     document_ids: List[str] = None,
                     chunk_types: List[str] = None) -> List[Dict[str, Any]]:
        """벡터 유사도 검색"""
        if not self.connection:
            self.connect()
        
        # 쿼리 임베딩 생성
        query_embedding = self.generate_query_embedding(query)
        if not query_embedding:
            return []
        
        try:
            with self.connection.cursor() as cur:
                # 기본 쿼리
                base_query = """
                    SELECT 
                        c.chunk_id,
                        c.document_id,
                        c.section_id,
                        c.content,
                        c.chunk_type,
                        c.metadata,
                        d.title as document_title,
                        s.title as section_title,
                        s.level as section_level,
                        1 - (c.embedding <=> %s) as similarity
                    FROM chunks c
                    JOIN documents d ON c.document_id = d.document_id
                    JOIN sections s ON c.section_id = s.section_id
                    WHERE 1 - (c.embedding <=> %s) > %s
                """
                
                params = [query_embedding, query_embedding, similarity_threshold]
                
                # 필터 조건 추가
                if document_ids:
                    placeholders = ','.join(['%s'] * len(document_ids))
                    base_query += f" AND c.document_id IN ({placeholders})"
                    params.extend(document_ids)
                
                if chunk_types:
                    placeholders = ','.join(['%s'] * len(chunk_types))
                    base_query += f" AND c.chunk_type IN ({placeholders})"
                    params.extend(chunk_types)
                
                # 정렬 및 제한
                base_query += " ORDER BY similarity DESC LIMIT %s"
                params.append(limit)
                
                cur.execute(base_query, params)
                results = cur.fetchall()
                
                # 결과 포맷팅
                formatted_results = []
                for row in results:
                    formatted_results.append({
                        'chunk_id': row[0],
                        'document_id': row[1],
                        'section_id': row[2],
                        'content': row[3],
                        'chunk_type': row[4],
                        'metadata': row[5],
                        'document_title': row[6],
                        'section_title': row[7],
                        'section_level': row[8],
                        'similarity': float(row[9])
                    })
                
                return formatted_results
                
        except Exception as e:
            logger.error(f"벡터 검색 중 오류: {str(e)}")
            return []
    
    def hybrid_search(self, 
                     query: str, 
                     limit: int = 10,
                     vector_weight: float = 0.7,
                     text_weight: float = 0.3) -> List[Dict[str, Any]]:
        """하이브리드 검색 (벡터 + 텍스트)"""
        if not self.connection:
            self.connect()
        
        # 벡터 검색
        vector_results = self.vector_search(query, limit=limit*2)
        
        # 텍스트 검색
        text_results = self.text_search(query, limit=limit*2)
        
        # 결과 통합 및 점수 계산
        combined_results = {}
        
        # 벡터 검색 결과 추가
        for result in vector_results:
            chunk_id = result['chunk_id']
            combined_results[chunk_id] = {
                **result,
                'vector_score': result['similarity'],
                'text_score': 0.0,
                'combined_score': result['similarity'] * vector_weight
            }
        
        # 텍스트 검색 결과 추가/업데이트
        for result in text_results:
            chunk_id = result['chunk_id']
            text_score = result.get('text_score', 0.0)
            
            if chunk_id in combined_results:
                # 기존 결과 업데이트
                combined_results[chunk_id]['text_score'] = text_score
                combined_results[chunk_id]['combined_score'] = (
                    combined_results[chunk_id]['vector_score'] * vector_weight +
                    text_score * text_weight
                )
            else:
                # 새 결과 추가
                combined_results[chunk_id] = {
                    **result,
                    'vector_score': 0.0,
                    'text_score': text_score,
                    'combined_score': text_score * text_weight
                }
        
        # 점수순 정렬 및 제한
        sorted_results = sorted(
            combined_results.values(),
            key=lambda x: x['combined_score'],
            reverse=True
        )
        
        return sorted_results[:limit]
    
    def text_search(self, 
                   query: str, 
                   limit: int = 10,
                   document_ids: List[str] = None) -> List[Dict[str, Any]]:
        """텍스트 검색 (PostgreSQL full-text search)"""
        if not self.connection:
            self.connect()
        
        try:
            with self.connection.cursor() as cur:
                # 기본 쿼리
                base_query = """
                    SELECT 
                        c.chunk_id,
                        c.document_id,
                        c.section_id,
                        c.content,
                        c.chunk_type,
                        c.metadata,
                        d.title as document_title,
                        s.title as section_title,
                        s.level as section_level,
                        ts_rank(to_tsvector('korean', c.content), plainto_tsquery('korean', %s)) as text_score
                    FROM chunks c
                    JOIN documents d ON c.document_id = d.document_id
                    JOIN sections s ON c.section_id = s.section_id
                    WHERE to_tsvector('korean', c.content) @@ plainto_tsquery('korean', %s)
                """
                
                params = [query, query]
                
                # 필터 조건 추가
                if document_ids:
                    placeholders = ','.join(['%s'] * len(document_ids))
                    base_query += f" AND c.document_id IN ({placeholders})"
                    params.extend(document_ids)
                
                # 정렬 및 제한
                base_query += " ORDER BY text_score DESC LIMIT %s"
                params.append(limit)
                
                cur.execute(base_query, params)
                results = cur.fetchall()
                
                # 결과 포맷팅
                formatted_results = []
                for row in results:
                    formatted_results.append({
                        'chunk_id': row[0],
                        'document_id': row[1],
                        'section_id': row[2],
                        'content': row[3],
                        'chunk_type': row[4],
                        'metadata': row[5],
                        'document_title': row[6],
                        'section_title': row[7],
                        'section_level': row[8],
                        'text_score': float(row[9])
                    })
                
                return formatted_results
                
        except Exception as e:
            logger.error(f"텍스트 검색 중 오류: {str(e)}")
            return []
    
    def get_document_context(self, chunk_id: str, context_window: int = 2) -> Dict[str, Any]:
        """청크의 문서 맥락 정보 가져오기"""
        if not self.connection:
            self.connect()
        
        try:
            with self.connection.cursor() as cur:
                # 청크 정보 조회
                cur.execute("""
                    SELECT 
                        c.chunk_id,
                        c.document_id,
                        c.section_id,
                        c.content,
                        c.chunk_type,
                        c.metadata,
                        d.title as document_title,
                        s.title as section_title,
                        s.level as section_level
                    FROM chunks c
                    JOIN documents d ON c.document_id = d.document_id
                    JOIN sections s ON c.section_id = s.section_id
                    WHERE c.chunk_id = %s
                """, (chunk_id,))
                
                chunk_result = cur.fetchone()
                if not chunk_result:
                    return {}
                
                chunk_info = {
                    'chunk_id': chunk_result[0],
                    'document_id': chunk_result[1],
                    'section_id': chunk_result[2],
                    'content': chunk_result[3],
                    'chunk_type': chunk_result[4],
                    'metadata': chunk_result[5],
                    'document_title': chunk_result[6],
                    'section_title': chunk_result[7],
                    'section_level': chunk_result[8]
                }
                
                # 같은 섹션의 다른 청크들 조회
                cur.execute("""
                    SELECT chunk_id, content, chunk_type
                    FROM chunks
                    WHERE section_id = %s
                    ORDER BY chunk_id
                """, (chunk_result[2],))
                
                section_chunks = cur.fetchall()
                
                # 현재 청크의 위치 찾기
                current_index = -1
                for i, (cid, _, _) in enumerate(section_chunks):
                    if cid == chunk_id:
                        current_index = i
                        break
                
                # 맥락 청크들 선택
                context_chunks = []
                start_idx = max(0, current_index - context_window)
                end_idx = min(len(section_chunks), current_index + context_window + 1)
                
                for i in range(start_idx, end_idx):
                    if i != current_index:  # 현재 청크 제외
                        context_chunks.append({
                            'chunk_id': section_chunks[i][0],
                            'content': section_chunks[i][1],
                            'chunk_type': section_chunks[i][2]
                        })
                
                chunk_info['context_chunks'] = context_chunks
                return chunk_info
                
        except Exception as e:
            logger.error(f"문서 맥락 조회 중 오류: {str(e)}")
            return {}
    
    def get_statistics(self) -> Dict[str, Any]:
        """저장소 통계 정보 조회"""
        if not self.connection:
            self.connect()
        
        try:
            with self.connection.cursor() as cur:
                # 기본 통계
                cur.execute("""
                    SELECT 
                        COUNT(DISTINCT d.document_id) as document_count,
                        COUNT(DISTINCT s.section_id) as section_count,
                        COUNT(c.chunk_id) as chunk_count,
                        AVG(array_length(c.embedding, 1)) as avg_embedding_dim
                    FROM documents d
                    LEFT JOIN sections s ON d.document_id = s.document_id
                    LEFT JOIN chunks c ON s.section_id = c.section_id
                """)
                
                stats = cur.fetchone()
                
                # 청크 타입별 통계
                cur.execute("""
                    SELECT chunk_type, COUNT(*) as count
                    FROM chunks
                    GROUP BY chunk_type
                    ORDER BY count DESC
                """)
                
                chunk_types = cur.fetchall()
                
                return {
                    'document_count': stats[0] or 0,
                    'section_count': stats[1] or 0,
                    'chunk_count': stats[2] or 0,
                    'avg_embedding_dimension': float(stats[3]) if stats[3] else 0,
                    'chunk_types': {row[0]: row[1] for row in chunk_types}
                }
                
        except Exception as e:
            logger.error(f"통계 조회 중 오류: {str(e)}")
            return {}

def main():
    """메인 함수 - 테스트용"""
    # 검색기 초기화
    retriever = VectorRetriever(use_openai=os.getenv('OPENAI_API_KEY') is not None)
    
    try:
        # 연결 테스트
        retriever.connect()
        
        # 통계 조회
        stats = retriever.get_statistics()
        print("=== 저장소 통계 ===")
        print(f"문서 수: {stats.get('document_count', 0)}")
        print(f"섹션 수: {stats.get('section_count', 0)}")
        print(f"청크 수: {stats.get('chunk_count', 0)}")
        print(f"평균 임베딩 차원: {stats.get('avg_embedding_dimension', 0)}")
        print(f"청크 타입별 분포: {stats.get('chunk_types', {})}")
        
        # 검색 테스트
        test_query = "청년 주택 지원"
        print(f"\n=== 검색 테스트: '{test_query}' ===")
        
        # 벡터 검색
        vector_results = retriever.vector_search(test_query, limit=5)
        print(f"벡터 검색 결과: {len(vector_results)}개")
        for i, result in enumerate(vector_results[:3]):
            print(f"{i+1}. {result['document_title']} - {result['section_title']}")
            print(f"   유사도: {result['similarity']:.3f}")
            print(f"   내용: {result['content'][:100]}...")
            print()
        
        # 하이브리드 검색
        hybrid_results = retriever.hybrid_search(test_query, limit=5)
        print(f"하이브리드 검색 결과: {len(hybrid_results)}개")
        for i, result in enumerate(hybrid_results[:3]):
            print(f"{i+1}. {result['document_title']} - {result['section_title']}")
            print(f"   벡터 점수: {result.get('vector_score', 0):.3f}")
            print(f"   텍스트 점수: {result.get('text_score', 0):.3f}")
            print(f"   종합 점수: {result.get('combined_score', 0):.3f}")
            print(f"   내용: {result['content'][:100]}...")
            print()
        
    except Exception as e:
        logger.error(f"테스트 중 오류: {str(e)}")
    finally:
        retriever.disconnect()

if __name__ == "__main__":
    main()
