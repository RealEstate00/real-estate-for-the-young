#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
임베딩 생성 모듈
청크를 벡터 임베딩으로 변환합니다.
"""

import json
import numpy as np
from pathlib import Path
from typing import List, Dict, Any, Optional
import logging
from sentence_transformers import SentenceTransformer
import openai
from openai import OpenAI
import os
from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()

logger = logging.getLogger(__name__)

class EmbeddingGenerator:
    """임베딩 생성 클래스 (한국어 최적화)"""

    # 한국어 지원 임베딩 모델 추천
    KOREAN_MODELS = {
        'multilingual-mini': 'sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2',  # 384dim, 빠름
        'multilingual-e5-large': 'intfloat/multilingual-e5-large',  # 1024dim, 고품질
        'multilingual-e5-base': 'intfloat/multilingual-e5-base',  # 768dim, 균형
        'korean-roberta': 'jhgan/ko-sroberta-multitask',  # 768dim, 한국어 특화
    }

    def __init__(self,
                 model_name: Optional[str] = None,
                 use_openai: bool = False,
                 openai_model: str = "text-embedding-3-small",
                 korean_optimized: bool = True):
        """
        초기화

        Args:
            model_name: 사용할 모델 이름 (None이면 한국어 최적화 모델 자동 선택)
            use_openai: OpenAI API 사용 여부
            openai_model: OpenAI 임베딩 모델
            korean_optimized: 한국어 최적화 모델 사용 여부
        """
        self.use_openai = use_openai
        self.openai_model = openai_model

        # 모델 선택
        if model_name is None and korean_optimized and not use_openai:
            # 한국어 최적화 모델 자동 선택
            model_name = self.KOREAN_MODELS['multilingual-e5-base']
            logger.info("한국어 최적화 모델 자동 선택")

        self.model_name = model_name or self.KOREAN_MODELS['multilingual-mini']

        # 모델 초기화
        if use_openai:
            self.client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
            self.model = None
            logger.info(f"OpenAI 임베딩 모델 초기화: {openai_model}")
        else:
            try:
                self.model = SentenceTransformer(self.model_name)
                self.client = None
                logger.info(f"로컬 임베딩 모델 초기화: {self.model_name}")
                logger.info(f"임베딩 차원: {self.model.get_sentence_embedding_dimension()}")
            except Exception as e:
                logger.error(f"모델 로딩 실패: {str(e)}")
                logger.info("기본 모델로 폴백")
                self.model = SentenceTransformer(self.KOREAN_MODELS['multilingual-mini'])
                self.model_name = self.KOREAN_MODELS['multilingual-mini']
    
    def generate_embedding(self, text: str) -> List[float]:
        """단일 텍스트의 임베딩 생성"""
        if not text.strip():
            return []
        
        try:
            if self.use_openai:
                response = self.client.embeddings.create(
                    model=self.openai_model,
                    input=text
                )
                return response.data[0].embedding
            else:
                embedding = self.model.encode(text, convert_to_tensor=False)
                return embedding.tolist()
        except Exception as e:
            logger.error(f"임베딩 생성 중 오류 발생: {str(e)}")
            return []
    
    def generate_batch_embeddings(self, texts: List[str], batch_size: int = 32) -> List[List[float]]:
        """배치 임베딩 생성"""
        if not texts:
            return []
        
        embeddings = []
        
        if self.use_openai:
            # OpenAI는 배치 처리 지원
            try:
                response = self.client.embeddings.create(
                    model=self.openai_model,
                    input=texts
                )
                embeddings = [data.embedding for data in response.data]
            except Exception as e:
                logger.error(f"OpenAI 배치 임베딩 생성 중 오류: {str(e)}")
                # 개별 처리로 폴백
                for text in texts:
                    embedding = self.generate_embedding(text)
                    embeddings.append(embedding)
        else:
            # Sentence Transformers 배치 처리
            try:
                embeddings = self.model.encode(texts, convert_to_tensor=False, batch_size=batch_size)
                embeddings = embeddings.tolist()
            except Exception as e:
                logger.error(f"로컬 배치 임베딩 생성 중 오류: {str(e)}")
                # 개별 처리로 폴백
                for text in texts:
                    embedding = self.generate_embedding(text)
                    embeddings.append(embedding)
        
        return embeddings
    
    def process_chunks(self, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """청크들에 임베딩 추가"""
        if not chunks:
            return []
        
        # 텍스트 추출
        texts = [chunk.get('content', '') for chunk in chunks]
        
        # 배치 임베딩 생성
        logger.info(f"{len(texts)}개 청크의 임베딩 생성 중...")
        embeddings = self.generate_batch_embeddings(texts)
        
        # 청크에 임베딩 추가
        processed_chunks = []
        for i, chunk in enumerate(chunks):
            processed_chunk = chunk.copy()
            processed_chunk['embedding'] = embeddings[i] if i < len(embeddings) else []
            processed_chunk['embedding_model'] = self.openai_model if self.use_openai else self.model_name
            processed_chunk['embedding_dimension'] = len(embeddings[i]) if i < len(embeddings) and embeddings[i] else 0
            processed_chunks.append(processed_chunk)
        
        return processed_chunks
    
    def process_chunk_files(self, input_dir: str, output_dir: str) -> List[List[Dict[str, Any]]]:
        """청크 파일들에 임베딩 추가"""
        input_path = Path(input_dir)
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        json_files = list(input_path.glob("*_chunks.json"))
        logger.info(f"임베딩 처리할 파일 수: {len(json_files)}")
        
        all_processed_chunks = []
        
        for json_file in json_files:
            logger.info(f"임베딩 생성 중: {json_file.name}")
            
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    chunks = json.load(f)
                
                # 청크들에 임베딩 추가
                processed_chunks = self.process_chunks(chunks)
                all_processed_chunks.append(processed_chunks)
                
                # 결과 저장
                output_file = output_path / f"{json_file.stem}_embedded.json"
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(processed_chunks, f, ensure_ascii=False, indent=2)
                
                logger.info(f"저장 완료: {output_file}")
                
            except Exception as e:
                logger.error(f"파일 처리 중 오류 발생 {json_file.name}: {str(e)}")
                continue
        
        return all_processed_chunks

class EmbeddingAnalyzer:
    """임베딩 분석 클래스"""
    
    @staticmethod
    def analyze_embeddings(processed_chunks: List[List[Dict[str, Any]]]) -> Dict[str, Any]:
        """임베딩 분석"""
        all_chunks = []
        for chunks in processed_chunks:
            all_chunks.extend(chunks)
        
        if not all_chunks:
            return {}
        
        # 임베딩 차원 분석
        embedding_dims = [chunk.get('embedding_dimension', 0) for chunk in all_chunks]
        valid_embeddings = [dim for dim in embedding_dims if dim > 0]
        
        # 청크 타입별 분석
        chunk_types = {}
        for chunk in all_chunks:
            chunk_type = chunk.get('chunk_type', 'unknown')
            if chunk_type not in chunk_types:
                chunk_types[chunk_type] = 0
            chunk_types[chunk_type] += 1
        
        # 토큰 수 분석
        token_counts = [chunk.get('metadata', {}).get('token_count', 0) for chunk in all_chunks]
        
        analysis = {
            'total_chunks': len(all_chunks),
            'valid_embeddings': len(valid_embeddings),
            'embedding_dimension': valid_embeddings[0] if valid_embeddings else 0,
            'chunk_types': chunk_types,
            'token_stats': {
                'min': min(token_counts) if token_counts else 0,
                'max': max(token_counts) if token_counts else 0,
                'avg': sum(token_counts) / len(token_counts) if token_counts else 0
            }
        }
        
        return analysis

def main():
    """메인 함수"""
    # 경로 설정
    base_dir = Path(__file__).parent.parent.parent.parent
    input_dir = base_dir / "data" / "vector_db" / "chunks"
    output_dir = base_dir / "data" / "vector_db" / "embeddings"
    
    print(f"입력 디렉토리: {input_dir}")
    print(f"출력 디렉토리: {output_dir}")
    
    # 임베딩 생성기 초기화 (OpenAI 사용 여부에 따라)
    use_openai = os.getenv('OPENAI_API_KEY') is not None
    if use_openai:
        print("OpenAI 임베딩 모델 사용")
        generator = EmbeddingGenerator(use_openai=True)
    else:
        print("로컬 Sentence Transformers 모델 사용")
        generator = EmbeddingGenerator(use_openai=False)
    
    # 청크 파일들 처리
    processed_chunks = generator.process_chunk_files(str(input_dir), str(output_dir))
    
    # 분석 결과 출력
    analyzer = EmbeddingAnalyzer()
    analysis = analyzer.analyze_embeddings(processed_chunks)
    
    print(f"\n=== 임베딩 생성 완료 ===")
    print(f"총 청크 수: {analysis.get('total_chunks', 0)}")
    print(f"유효한 임베딩 수: {analysis.get('valid_embeddings', 0)}")
    print(f"임베딩 차원: {analysis.get('embedding_dimension', 0)}")
    print(f"청크 타입별 분포: {analysis.get('chunk_types', {})}")
    
    token_stats = analysis.get('token_stats', {})
    print(f"토큰 수 통계: 최소 {token_stats.get('min', 0)}, 최대 {token_stats.get('max', 0)}, 평균 {token_stats.get('avg', 0):.1f}")

if __name__ == "__main__":
    main()
