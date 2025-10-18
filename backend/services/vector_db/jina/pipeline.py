#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
전체 파이프라인 모듈
PDF → 텍스트 → 구조화 → 청킹 → 임베딩 → 저장 → 검색의 전체 워크플로우를 관리합니다.
"""

import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
import os
from dotenv import load_dotenv

# 로컬 모듈 import
from .extractor import PDFOCRProcessor
from .normalizer import TextNormalizer
# from .structure import DocumentStructurer  # ❌ 제거: normalizer에서 섹션 감지 수행
from .chunker import DocumentChunker
from .embedding import EmbeddingGenerator
from .store_pg import PostgreSQLVectorStore
from .retriever import VectorRetriever
from .qa_checks import QualityChecker

# 환경 변수 로드
load_dotenv()

logger = logging.getLogger(__name__)

class DocumentProcessingPipeline:
    """문서 처리 파이프라인 클래스"""
    
    def __init__(self, 
                 base_dir: str = None,
                 use_openai: bool = None,
                 embedding_model: str = None):
        self.base_dir = Path(base_dir) if base_dir else Path(__file__).parent.parent.parent.parent
        
        # 설정
        self.use_openai = use_openai if use_openai is not None else os.getenv('OPENAI_API_KEY') is not None
        self.embedding_model = embedding_model or "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
        
        # 디렉토리 설정
        self.dirs = {
            'pdf_input': self.base_dir / "backend" / "data" / "vector_db" / "finance_support_pdf",
            'raw_json': self.base_dir / "backend" / "data" / "vector_db" / "raw_json",
            'normalized': self.base_dir / "backend" / "data" / "vector_db" / "normalized",
            # 'structured': self.base_dir / "backend" / "data" / "vector_db" / "structured",  # ❌ 제거
            'chunks': self.base_dir / "backend" / "data" / "vector_db" / "chunks",
            'embeddings': self.base_dir / "backend" / "data" / "vector_db" / "embeddings"
        }
        
        # 각 단계별 처리기 초기화
        self.extractor = PDFOCRProcessor(str(self.dirs['pdf_input']), str(self.dirs['raw_json']))
        self.normalizer = TextNormalizer()
        # self.structurer = DocumentStructurer()  # ❌ 제거: normalizer가 섹션 감지 수행
        self.chunker = DocumentChunker(chunk_size=500, chunk_overlap=50, min_chunk_size=100)
        self.embedder = EmbeddingGenerator(
            model_name=self.embedding_model,
            use_openai=self.use_openai
        )
        self.store = PostgreSQLVectorStore()
        self.retriever = VectorRetriever(use_openai=self.use_openai, embedding_model=self.embedding_model)
        self.quality_checker = QualityChecker()
        
        # 디렉토리 생성
        for dir_path in self.dirs.values():
            dir_path.mkdir(parents=True, exist_ok=True)
    
    def run_full_pipeline(self) -> Dict[str, Any]:
        """전체 파이프라인 실행"""
        logger.info("=== 문서 처리 파이프라인 시작 ===")
        
        pipeline_stats = {
            'start_time': datetime.now().isoformat(),
            'steps': {},
            'errors': []
        }
        
        try:
            # 1. PDF 추출
            logger.info("1단계: PDF 텍스트 추출")
            pdf_results = self.extractor.process_all_pdfs()
            self.extractor.save_combined_results(pdf_results)
            pipeline_stats['steps']['extraction'] = {
                'status': 'completed',
                'files_processed': len(pdf_results),
                'successful_files': len([r for r in pdf_results if "error" not in r])
            }
            
            # 2. 텍스트 정규화
            logger.info("2단계: 텍스트 정규화")
            normalized_results = self.normalizer.process_json_files(
                str(self.dirs['raw_json']), 
                str(self.dirs['normalized'])
            )
            pipeline_stats['steps']['normalization'] = {
                'status': 'completed',
                'files_processed': len(normalized_results)
            }
            
            # 3. 청킹 (구조화 단계 제거 - normalizer가 이미 섹션 감지 수행)
            logger.info("3단계: 문서 청킹")
            # normalized 파일을 직접 청킹
            chunked_docs = []
            for norm_file in Path(self.dirs['normalized']).glob('*_normalized.json'):
                with open(norm_file, 'r', encoding='utf-8') as f:
                    normalized_doc = json.load(f)

                chunks = self.chunker.chunk_document(normalized_doc)
                chunks_dict = [chunk.to_dict() for chunk in chunks]

                # 저장
                output_file = self.dirs['chunks'] / f"{norm_file.stem}_chunks.json"
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(chunks_dict, f, ensure_ascii=False, indent=2)

                chunked_docs.append(chunks_dict)
            total_chunks = sum(len(chunks) for chunks in chunked_docs)
            pipeline_stats['steps']['chunking'] = {
                'status': 'completed',
                'total_chunks': total_chunks
            }
            
            # 5. 임베딩 생성
            logger.info("5단계: 임베딩 생성")
            embedded_docs = self.embedder.process_chunk_files(
                str(self.dirs['chunks']), 
                str(self.dirs['embeddings'])
            )
            pipeline_stats['steps']['embedding'] = {
                'status': 'completed',
                'model_used': self.embedding_model,
                'use_openai': self.use_openai
            }
            
            # 6. PostgreSQL 저장
            logger.info("6단계: PostgreSQL 저장")
            store_stats = self.store.process_embedded_files(str(self.dirs['embeddings']))
            pipeline_stats['steps']['storage'] = {
                'status': 'completed',
                'documents_inserted': store_stats['documents_inserted'],
                'sections_inserted': store_stats['sections_inserted'],
                'chunks_inserted': store_stats['chunks_inserted']
            }
            
            pipeline_stats['end_time'] = datetime.now().isoformat()
            pipeline_stats['status'] = 'completed'
            
            logger.info("=== 파이프라인 완료 ===")
            
        except Exception as e:
            logger.error(f"파이프라인 실행 중 오류: {str(e)}")
            pipeline_stats['errors'].append(str(e))
            pipeline_stats['status'] = 'failed'
            pipeline_stats['end_time'] = datetime.now().isoformat()
        
        return pipeline_stats
    
    def search_documents(self, 
                        query: str, 
                        search_type: str = "hybrid",
                        limit: int = 10,
                        quality_check: bool = True) -> Dict[str, Any]:
        """문서 검색"""
        logger.info(f"문서 검색: '{query}' (타입: {search_type})")
        
        try:
            # 검색 실행
            if search_type == "vector":
                results = self.retriever.vector_search(query, limit=limit)
            elif search_type == "text":
                results = self.retriever.text_search(query, limit=limit)
            else:  # hybrid
                results = self.retriever.hybrid_search(query, limit=limit)
            
            # 품질 검사
            quality_report = None
            if quality_check and results:
                quality_report = self.quality_checker.generate_quality_report(results)
            
            return {
                'query': query,
                'search_type': search_type,
                'results': results,
                'quality_report': quality_report,
                'total_results': len(results),
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"검색 중 오류: {str(e)}")
            return {
                'query': query,
                'search_type': search_type,
                'results': [],
                'error': str(e),
                'total_results': 0,
                'timestamp': datetime.now().isoformat()
            }
    
    def get_document_context(self, chunk_id: str) -> Dict[str, Any]:
        """문서 맥락 정보 조회"""
        try:
            context = self.retriever.get_document_context(chunk_id)
            return {
                'chunk_id': chunk_id,
                'context': context,
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"문서 맥락 조회 중 오류: {str(e)}")
            return {
                'chunk_id': chunk_id,
                'context': {},
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def get_system_statistics(self) -> Dict[str, Any]:
        """시스템 통계 조회"""
        try:
            db_stats = self.retriever.get_statistics()
            
            # 파일 시스템 통계
            file_stats = {}
            for stage, dir_path in self.dirs.items():
                if dir_path.exists():
                    files = list(dir_path.glob("*.json"))
                    file_stats[stage] = {
                        'file_count': len(files),
                        'total_size': sum(f.stat().st_size for f in files)
                    }
            
            return {
                'database_stats': db_stats,
                'file_stats': file_stats,
                'pipeline_config': {
                    'use_openai': self.use_openai,
                    'embedding_model': self.embedding_model,
                    'base_dir': str(self.base_dir)
                },
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"통계 조회 중 오류: {str(e)}")
            return {
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def run_quality_assessment(self) -> Dict[str, Any]:
        """전체 시스템 품질 평가"""
        logger.info("시스템 품질 평가 시작")
        
        try:
            # 테스트 쿼리들
            test_queries = [
                "청년 주택 지원",
                "월세 지원 금액",
                "신청 자격 조건",
                "서울시 주택 정책",
                "임차보증금 지원"
            ]
            
            assessment_results = {
                'test_queries': test_queries,
                'query_results': [],
                'overall_quality': 0.0,
                'timestamp': datetime.now().isoformat()
            }
            
            total_quality_score = 0.0
            
            for query in test_queries:
                # 검색 실행
                search_result = self.search_documents(query, quality_check=True)
                
                # 품질 점수 추출
                quality_score = 0.0
                if search_result.get('quality_report'):
                    quality_score = search_result['quality_report']['overall_score']
                    total_quality_score += quality_score
                
                assessment_results['query_results'].append({
                    'query': query,
                    'results_count': search_result['total_results'],
                    'quality_score': quality_score,
                    'has_quality_report': search_result.get('quality_report') is not None
                })
            
            # 전체 품질 점수 계산
            if test_queries:
                assessment_results['overall_quality'] = total_quality_score / len(test_queries)
            
            logger.info(f"품질 평가 완료 - 전체 점수: {assessment_results['overall_quality']:.2f}")
            
            return assessment_results
            
        except Exception as e:
            logger.error(f"품질 평가 중 오류: {str(e)}")
            return {
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }

def main():
    """메인 함수"""
    # 파이프라인 초기화
    pipeline = DocumentProcessingPipeline()
    
    print("=== 문서 처리 파이프라인 ===")
    print(f"기본 디렉토리: {pipeline.base_dir}")
    print(f"OpenAI 사용: {pipeline.use_openai}")
    print(f"임베딩 모델: {pipeline.embedding_model}")
    
    # 사용자 선택
    print("\n실행할 작업을 선택하세요:")
    print("1. 전체 파이프라인 실행")
    print("2. 검색 테스트")
    print("3. 시스템 통계 조회")
    print("4. 품질 평가")
    
    choice = input("선택 (1-4): ").strip()
    
    if choice == "1":
        # 전체 파이프라인 실행
        print("\n=== 전체 파이프라인 실행 ===")
        stats = pipeline.run_full_pipeline()
        
        print(f"상태: {stats['status']}")
        print(f"시작 시간: {stats['start_time']}")
        print(f"종료 시간: {stats['end_time']}")
        
        for step, step_stats in stats['steps'].items():
            print(f"\n{step}: {step_stats['status']}")
            for key, value in step_stats.items():
                if key != 'status':
                    print(f"  {key}: {value}")
        
        if stats['errors']:
            print(f"\n오류: {stats['errors']}")
    
    elif choice == "2":
        # 검색 테스트
        print("\n=== 검색 테스트 ===")
        query = input("검색 쿼리를 입력하세요: ").strip()
        if query:
            result = pipeline.search_documents(query, quality_check=True)
            
            print(f"\n검색 결과: {result['total_results']}개")
            for i, doc in enumerate(result['results'][:5]):
                print(f"\n{i+1}. {doc['document_title']} - {doc['section_title']}")
                print(f"   유사도: {doc.get('similarity', 0):.3f}")
                print(f"   내용: {doc['content'][:100]}...")
            
            if result.get('quality_report'):
                print(f"\n품질 점수: {result['quality_report']['overall_score']:.2f}")
    
    elif choice == "3":
        # 시스템 통계
        print("\n=== 시스템 통계 ===")
        stats = pipeline.get_system_statistics()
        
        if 'error' in stats:
            print(f"오류: {stats['error']}")
        else:
            print("데이터베이스 통계:")
            db_stats = stats['database_stats']
            print(f"  문서 수: {db_stats.get('document_count', 0)}")
            print(f"  섹션 수: {db_stats.get('section_count', 0)}")
            print(f"  청크 수: {db_stats.get('chunk_count', 0)}")
            
            print("\n파일 시스템 통계:")
            for stage, file_stats in stats['file_stats'].items():
                print(f"  {stage}: {file_stats['file_count']}개 파일, {file_stats['total_size']:,} bytes")
    
    elif choice == "4":
        # 품질 평가
        print("\n=== 품질 평가 ===")
        assessment = pipeline.run_quality_assessment()
        
        if 'error' in assessment:
            print(f"오류: {assessment['error']}")
        else:
            print(f"전체 품질 점수: {assessment['overall_quality']:.2f}")
            print("\n쿼리별 결과:")
            for result in assessment['query_results']:
                print(f"  {result['query']}: {result['results_count']}개 결과, 품질 {result['quality_score']:.2f}")
    
    else:
        print("잘못된 선택입니다.")

if __name__ == "__main__":
    main()
