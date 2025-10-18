#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
PostgreSQL + pgvector 저장 모듈
임베딩된 청크들을 PostgreSQL에 저장합니다.
"""

import json
import psycopg
import numpy as np
from pathlib import Path
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime
import os
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()

logger = logging.getLogger(__name__)

class PostgreSQLVectorStore:
    """PostgreSQL 벡터 저장소 클래스"""
    
    def __init__(self, 
                 host: str = None,
                 port: int = None,
                 database: str = None,
                 user: str = None,
                 password: str = None):
        # 환경 변수에서 설정 가져오기
        self.host = host or os.getenv('PG_HOST', 'localhost')
        self.port = port or int(os.getenv('PG_PORT', 5432))
        self.database = database or os.getenv('PG_DB', 'rey')
        self.user = user or os.getenv('PG_USER', 'postgres')
        self.password = password or os.getenv('PG_PASSWORD', 'post1234')
        
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
    
    def create_tables(self):
        """테이블 생성"""
        if not self.connection:
            self.connect()
        
        try:
            with self.connection.cursor() as cur:
                # pgvector 확장 활성화
                cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
                
                # 문서 테이블
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS documents (
                        document_id VARCHAR(255) PRIMARY KEY,
                        title VARCHAR(500),
                        file_name VARCHAR(500),
                        metadata JSONB,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                """)
                
                # 섹션 테이블
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS sections (
                        section_id VARCHAR(255) PRIMARY KEY,
                        document_id VARCHAR(255) REFERENCES documents(document_id),
                        title VARCHAR(500),
                        level INTEGER,
                        page_range JSONB,
                        metadata JSONB,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                """)
                
                # 청크 테이블 (벡터 포함)
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS chunks (
                        chunk_id VARCHAR(255) PRIMARY KEY,
                        document_id VARCHAR(255) REFERENCES documents(document_id),
                        section_id VARCHAR(255) REFERENCES sections(section_id),
                        content TEXT,
                        chunk_type VARCHAR(100),
                        block_ids JSONB,
                        embedding VECTOR(384),  -- 기본 차원, 필요시 조정
                        metadata JSONB,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                """)
                
                # 벡터 검색을 위한 인덱스 생성
                cur.execute("""
                    CREATE INDEX IF NOT EXISTS chunks_embedding_idx 
                    ON chunks USING ivfflat (embedding vector_cosine_ops) 
                    WITH (lists = 100);
                """)
                
                # 텍스트 검색을 위한 인덱스 생성
                cur.execute("""
                    CREATE INDEX IF NOT EXISTS chunks_content_idx 
                    ON chunks USING gin (to_tsvector('korean', content));
                """)
                
                # 메타데이터 검색을 위한 인덱스 생성
                cur.execute("""
                    CREATE INDEX IF NOT EXISTS chunks_metadata_idx 
                    ON chunks USING gin (metadata);
                """)
                
                self.connection.commit()
                logger.info("테이블 생성 완료")
                
        except Exception as e:
            logger.error(f"테이블 생성 중 오류: {str(e)}")
            self.connection.rollback()
            raise
    
    def insert_document(self, document_data: Dict[str, Any]) -> bool:
        """문서 삽입"""
        try:
            with self.connection.cursor() as cur:
                cur.execute("""
                    INSERT INTO documents (document_id, title, file_name, metadata)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (document_id) DO UPDATE SET
                        title = EXCLUDED.title,
                        file_name = EXCLUDED.file_name,
                        metadata = EXCLUDED.metadata,
                        updated_at = CURRENT_TIMESTAMP;
                """, (
                    document_data['document_id'],
                    document_data['title'],
                    document_data.get('file_name', ''),
                    json.dumps(document_data.get('metadata', {}))
                ))
                return True
        except Exception as e:
            logger.error(f"문서 삽입 중 오류: {str(e)}")
            return False
    
    def insert_section(self, section_data: Dict[str, Any]) -> bool:
        """섹션 삽입"""
        try:
            with self.connection.cursor() as cur:
                cur.execute("""
                    INSERT INTO sections (section_id, document_id, title, level, page_range, metadata)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (section_id) DO UPDATE SET
                        document_id = EXCLUDED.document_id,
                        title = EXCLUDED.title,
                        level = EXCLUDED.level,
                        page_range = EXCLUDED.page_range,
                        metadata = EXCLUDED.metadata;
                """, (
                    section_data['section_id'],
                    section_data['document_id'],
                    section_data['title'],
                    section_data['level'],
                    json.dumps(section_data.get('page_range', {})),
                    json.dumps(section_data.get('metadata', {}))
                ))
                return True
        except Exception as e:
            logger.error(f"섹션 삽입 중 오류: {str(e)}")
            return False
    
    def insert_chunk(self, chunk_data: Dict[str, Any]) -> bool:
        """청크 삽입"""
        try:
            with self.connection.cursor() as cur:
                # 임베딩 벡터 처리
                embedding = chunk_data.get('embedding', [])
                if not embedding:
                    logger.warning(f"청크 {chunk_data.get('chunk_id')}에 임베딩이 없습니다.")
                    return False
                
                # 벡터 차원 확인 및 조정
                embedding_dim = len(embedding)
                if embedding_dim != 384:  # 기본 차원과 다르면 테이블 구조 조정 필요
                    logger.warning(f"임베딩 차원이 예상과 다릅니다: {embedding_dim}")
                
                cur.execute("""
                    INSERT INTO chunks (
                        chunk_id, document_id, section_id, content, chunk_type, 
                        block_ids, embedding, metadata
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (chunk_id) DO UPDATE SET
                        document_id = EXCLUDED.document_id,
                        section_id = EXCLUDED.section_id,
                        content = EXCLUDED.content,
                        chunk_type = EXCLUDED.chunk_type,
                        block_ids = EXCLUDED.block_ids,
                        embedding = EXCLUDED.embedding,
                        metadata = EXCLUDED.metadata;
                """, (
                    chunk_data['chunk_id'],
                    chunk_data['document_id'],
                    chunk_data['section_id'],
                    chunk_data['content'],
                    chunk_data['chunk_type'],
                    json.dumps(chunk_data.get('block_ids', [])),
                    embedding,
                    json.dumps(chunk_data.get('metadata', {}))
                ))
                return True
        except Exception as e:
            logger.error(f"청크 삽입 중 오류: {str(e)}")
            return False
    
    def process_embedded_files(self, input_dir: str) -> Dict[str, Any]:
        """임베딩된 파일들을 PostgreSQL에 저장"""
        input_path = Path(input_dir)
        json_files = list(input_path.glob("*_embedded.json"))
        
        logger.info(f"저장할 파일 수: {len(json_files)}")
        
        # 데이터베이스 연결 및 테이블 생성
        self.connect()
        self.create_tables()
        
        stats = {
            'total_files': len(json_files),
            'documents_inserted': 0,
            'sections_inserted': 0,
            'chunks_inserted': 0,
            'errors': 0
        }
        
        try:
            for json_file in json_files:
                logger.info(f"저장 중: {json_file.name}")
                
                try:
                    with open(json_file, 'r', encoding='utf-8') as f:
                        chunks_data = json.load(f)
                    
                    if not chunks_data:
                        continue
                    
                    # 문서 정보 추출 (첫 번째 청크에서)
                    first_chunk = chunks_data[0]
                    document_id = first_chunk.get('document_id', '')
                    
                    # 문서 삽입
                    document_data = {
                        'document_id': document_id,
                        'title': document_id.replace('doc_', '').replace('_', ' '),
                        'file_name': json_file.name,
                        'metadata': {
                            'source_file': str(json_file),
                            'chunk_count': len(chunks_data),
                            'created_at': datetime.now().isoformat()
                        }
                    }
                    
                    if self.insert_document(document_data):
                        stats['documents_inserted'] += 1
                    
                    # 청크별로 섹션과 청크 삽입
                    current_section_id = None
                    for chunk_data in chunks_data:
                        section_id = chunk_data.get('section_id', '')
                        
                        # 새 섹션인 경우 섹션 삽입
                        if section_id != current_section_id:
                            section_data = {
                                'section_id': section_id,
                                'document_id': document_id,
                                'title': section_id.replace('section_', ''),
                                'level': 0,
                                'metadata': {}
                            }
                            
                            if self.insert_section(section_data):
                                stats['sections_inserted'] += 1
                            
                            current_section_id = section_id
                        
                        # 청크 삽입
                        if self.insert_chunk(chunk_data):
                            stats['chunks_inserted'] += 1
                    
                    logger.info(f"저장 완료: {json_file.name}")
                    
                except Exception as e:
                    logger.error(f"파일 처리 중 오류 {json_file.name}: {str(e)}")
                    stats['errors'] += 1
                    continue
            
            self.connection.commit()
            logger.info("모든 데이터 저장 완료")
            
        except Exception as e:
            logger.error(f"데이터 저장 중 오류: {str(e)}")
            self.connection.rollback()
            stats['errors'] += 1
        
        finally:
            self.disconnect()
        
        return stats

def main():
    """메인 함수"""
    # 경로 설정
    base_dir = Path(__file__).parent.parent.parent.parent
    input_dir = base_dir / "data" / "vector_db" / "embeddings"
    
    print(f"입력 디렉토리: {input_dir}")
    
    # PostgreSQL 벡터 저장소 초기화
    store = PostgreSQLVectorStore()
    
    # 임베딩된 파일들 저장
    stats = store.process_embedded_files(str(input_dir))
    
    print(f"\n=== PostgreSQL 저장 완료 ===")
    print(f"처리된 파일 수: {stats['total_files']}")
    print(f"삽입된 문서 수: {stats['documents_inserted']}")
    print(f"삽입된 섹션 수: {stats['sections_inserted']}")
    print(f"삽입된 청크 수: {stats['chunks_inserted']}")
    print(f"오류 수: {stats['errors']}")

if __name__ == "__main__":
    main()