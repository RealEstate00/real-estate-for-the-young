"""
Housing ChromaDB - All-in-One Vector Database
주택 데이터 벡터DB 통합 모듈 (로드-분할-임베딩-저장)
"""

import hashlib
import logging
import pandas as pd
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
from tqdm import tqdm

# External dependencies
import chromadb
from chromadb.config import Settings # ChromaDB 설정
from sentence_transformers import SentenceTransformer # 임베딩 모델
from langchain.text_splitter import RecursiveCharacterTextSplitter # 문서 분할

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# ============================================================================
# 1. 설정 (Configuration)
# ============================================================================

class VectorConfig:
    """벡터 데이터베이스 설정"""
    
    def __init__(self):
        # 프로젝트 루트 경로 설정 (Streamlit 호환)
        import sys
        from pathlib import Path
        
        # 현재 파일 위치에서 프로젝트 루트 찾기
        current_file = Path(__file__)
        # chromadb.py -> inha -> vector_db -> services -> backend -> project_root
        # 실제로는 6단계 위가 아니라 5단계 위가 정확
        self.project_root = current_file.parent.parent.parent.parent.parent
        
        # ChromaDB 설정 (절대 경로)
        self.persist_directory = self.project_root / "backend" / "data" / "chroma_db" / "inha"
        
        # 임베딩 모델 설정
        self.embedding_model = "jhgan/ko-sbert-nli"
        
        # 컬렉션 설정
        self.housing_collection_name = "housing_embeddings"
        
        # 성능 설정
        self.batch_size = 32
        self.max_results = 50
        
        # 디바이스 설정
        self.device: Optional[str] = None
        
        # CSV 파일 경로 (절대 경로)
        self.default_csv_path = self.project_root / "backend" / "data" / "raw" / "for_vectorDB" / "housing_vector_data.csv"
        
        # 문서 분할 설정
        self.chunk_size = 500
        self.chunk_overlap = 50
        
        # 테마 키워드
        self.theme_keywords = ["청년", "신혼", "육아", "시니어", "예술", "반려동물", "여성안심"]
        
        # 지역 키워드 패턴
        self.location_patterns = ["구", "동", "시", "군"]
        self.station_pattern = "역"


# ============================================================================
# 2. 임베딩 (Korean Embeddings)
# ============================================================================

class KoreanEmbedder:
    """한국어 임베딩 처리 클래스"""
    
    def __init__(self, model_name: str = None, config: VectorConfig = None):
        self.config = config or VectorConfig()
        self.model_name = model_name or self.config.embedding_model
        self.model = None
        
        # 문서 분할기 초기화 - 줄바꿈, 문장부호, 쉼표, 공백 기준
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.config.chunk_size,
            chunk_overlap=self.config.chunk_overlap,
            separators=["\n\n", "\n", ".", "!", "?", ",", " ", ""]
        )
        
    def load_model(self) -> None:
        """임베딩 모델 로드"""
        if self.model is None:
            logger.info(f"Loading embedding model: {self.model_name}")
            self.model = SentenceTransformer(self.model_name)
            logger.info("Embedding model loaded successfully")
    
    def is_loaded(self) -> bool:
        """모델 로드 상태 확인"""
        return self.model is not None
    
    def encode_text(self, text: Union[str, List[str]]) -> Union[List[float], List[List[float]]]:
        """텍스트를 임베딩으로 변환"""
        if not self.is_loaded():
            self.load_model()
        
        is_single = isinstance(text, str)
        if is_single:
            text = [text]
        
        embeddings = self.model.encode(
            text, 
            convert_to_tensor=False, 
            normalize_embeddings=True
        ).tolist()
        
        return embeddings[0] if is_single else embeddings
    
    def create_housing_text(self, housing_data: Dict[str, Any]) -> str:
        """주택 데이터를 검색용 텍스트로 변환"""
        parts = []
        
        if housing_data.get('주택명'):
            parts.append(f"주택명: {housing_data['주택명']}")
        if housing_data.get('도로명주소'):
            parts.append(f"주소: {housing_data['도로명주소']}")
        if housing_data.get('시군구'):
            parts.append(f"지역: {housing_data['시군구']}")
        if housing_data.get('동명'):
            parts.append(f"동: {housing_data['동명']}")
        if housing_data.get('태그'):
            parts.append(f"특성: {housing_data['태그']}")
        
        return " ".join(parts)
    
    def split_text(self, text: str) -> List[str]:
        """텍스트를 청크로 분할"""
        if not text or len(text.strip()) == 0:
            return [text]
        
        # 짧은 텍스트는 분할하지 않음
        if len(text) <= self.config.chunk_size:
            return [text]
        
        # 긴 텍스트는 분할
        chunks = self.text_splitter.split_text(text)
        logger.debug(f"Split text into {len(chunks)} chunks")
        return chunks
    
    def parse_tags(self, tags_string: str) -> Dict[str, str]:
        """태그 문자열을 구조화된 메타데이터로 파싱"""
        parsed = {}
        if not tags_string:
            return parsed
        
        tag_parts = tags_string.split(', ')
        key_mapping = {
            '테마': 'theme', '지하철': 'subway', '자격요건': 'requirements',
            '마트': 'mart', '병원': 'hospital', '학교': 'school',
            '시설': 'facilities', '카페': 'cafe'
        }
        
        for part in tag_parts:
            if ':' in part:
                key, value = part.split(':', 1)
                key, value = key.strip(), value.strip()
                english_key = key_mapping.get(key, key)
                parsed[english_key] = value
        
        return parsed
    
    def validate_housing_data(self, housing_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """주택 데이터 검증 및 정리"""
        valid_data = []
        
        for i, record in enumerate(housing_data):
            try:
                # 필수 필드 확인
                if not record.get('주택명'):
                    logger.warning(f"Record {i}: Missing 주택명, skipping")
                    continue
                
                # 문자열 필드 정리
                for field in ['주택명', '지번주소', '도로명주소', '시군구', '동명', '태그']:
                    if pd.isna(record.get(field)):
                        record[field] = ''
                    else:
                        record[field] = str(record[field]).strip()
                
                valid_data.append(record)
                
            except Exception as e:
                logger.warning(f"Record {i}: Validation error - {e}, skipping")
                continue
        
        logger.info(f"Validated {len(valid_data)} out of {len(housing_data)} records")
        return valid_data


# ============================================================================
# 3. ChromaDB 컬렉션 관리 (Collections)
# ============================================================================

class HousingCollection:
    """주택 데이터 컬렉션 관리"""
    
    def __init__(self, embedder: KoreanEmbedder = None, config: VectorConfig = None):
        self.config = config or VectorConfig()
        self.embedder = embedder or KoreanEmbedder(config=self.config)
        self.client = None
        self.collection = None
        
        # 디렉토리 생성
        self.config.persist_directory.mkdir(parents=True, exist_ok=True)
    
    def connect(self) -> None:
        """ChromaDB 연결"""
        if self.client is None:
            logger.info(f"Connecting to ChromaDB at {self.config.persist_directory}")
            self.client = chromadb.PersistentClient(
                path=str(self.config.persist_directory),
                settings=Settings(anonymized_telemetry=False, allow_reset=True)
            )
            logger.info("Connected to ChromaDB")
    
    def disconnect(self) -> None:
        """ChromaDB 연결 해제"""
        if self.client:
            self.client = None
            self.collection = None
            logger.info("Disconnected from ChromaDB")
    
    def get_collection(self):
        """컬렉션 가져오기 또는 생성"""
        if self.collection is None:
            self.connect()
            try:
                self.collection = self.client.get_collection(self.config.housing_collection_name)
                logger.info(f"Retrieved existing collection: {self.config.housing_collection_name}")
            except:
                # 커스텀 임베딩 함수 생성
                from chromadb.utils import embedding_functions
                embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
                    model_name=self.config.embedding_model
                )
                
                self.collection = self.client.create_collection(
                    name=self.config.housing_collection_name,
                    metadata={
                        "description": "Housing data embeddings with text chunking",
                        "model": self.config.embedding_model,
                        "chunk_size": self.config.chunk_size,
                        "chunk_overlap": self.config.chunk_overlap
                    },
                    embedding_function=embedding_function
                )
                logger.info(f"Created new collection: {self.config.housing_collection_name}")
        return self.collection
    
    def prepare_document(self, housing_data: Dict[str, Any], chunk_id: int = 0) -> Dict[str, Any]:
        """주택 데이터를 벡터DB 문서로 준비 (청킹 지원)"""
        # 고유 ID 생성 (청크 ID 포함)
        base_id = f"{housing_data.get('주택명', '')}-{housing_data.get('도로명주소', '')}"
        doc_id = hashlib.md5(f"{base_id}-chunk-{chunk_id}".encode('utf-8')).hexdigest()
        
        # 텍스트 생성 및 분할
        document_text = self.embedder.create_housing_text(housing_data)
        text_chunks = self.embedder.split_text(document_text)
        
        # 해당 청크 선택 (청크가 없으면 원본 텍스트)
        if chunk_id < len(text_chunks):
            chunk_text = text_chunks[chunk_id]
        else:
            chunk_text = document_text
        
        # 임베딩 생성
        embedding = self.embedder.encode_text(chunk_text)
        
        # 메타데이터 준비
        metadata = {
            "주택명": housing_data.get('주택명', ''),
            "지번주소": housing_data.get('지번주소', ''),
            "도로명주소": housing_data.get('도로명주소', ''),
            "시군구": housing_data.get('시군구', ''),
            "동명": housing_data.get('동명', ''),
            "태그": housing_data.get('태그', ''),
            "chunk_id": chunk_id,
            "total_chunks": len(text_chunks)
        }
        
        # 태그 파싱 추가
        metadata.update(self.embedder.parse_tags(housing_data.get('태그', '')))
        
        return {
            'id': doc_id,
            'embedding': embedding,
            'metadata': metadata,
            'document': chunk_text
        }
    
    def add_documents(self, documents: List[Dict[str, Any]], batch_size: int = None) -> None:
        """문서들을 벡터DB에 추가 (청킹 지원)"""
        collection = self.get_collection()
        batch_size = batch_size or self.config.batch_size
        
        logger.info(f"Adding {len(documents)} documents to vector database with chunking")
        
        # 모든 청크 준비
        all_chunks = []
        for doc in documents:
            # 텍스트 분할하여 청크 개수 확인
            document_text = self.embedder.create_housing_text(doc)
            text_chunks = self.embedder.split_text(document_text)
            
            # 각 청크에 대해 문서 준비
            for chunk_id in range(len(text_chunks)):
                chunk_doc = self.prepare_document(doc, chunk_id)
                all_chunks.append(chunk_doc)
        
        logger.info(f"Total chunks to process: {len(all_chunks)}")
        
        # 배치 단위로 처리
        for i in range(0, len(all_chunks), batch_size):
            batch = all_chunks[i:i + batch_size]
            
            # 배치 데이터 준비
            ids, embeddings, metadatas, documents_text = [], [], [], []
            
            for chunk in batch:
                ids.append(chunk['id'])
                embeddings.append(chunk['embedding'])
                metadatas.append(chunk['metadata'])
                documents_text.append(chunk['document'])
            
            # 컬렉션에 추가
            try:
                collection.add(
                    ids=ids,
                    embeddings=embeddings,
                    metadatas=metadatas,
                    documents=documents_text
                )
            except Exception as e:
                logger.error(f"Failed to add batch: {e}")
                continue
        
        logger.info(f"Successfully loaded {collection.count()} document chunks")
    
    def count(self) -> int:
        """컬렉션 내 문서 수 반환"""
        collection = self.get_collection()
        return collection.count()
    
    def clear(self) -> None:
        """컬렉션 초기화"""
        self.connect()
        try:
            existing_collections = [col.name for col in self.client.list_collections()]
            if self.config.housing_collection_name in existing_collections:
                self.client.delete_collection(self.config.housing_collection_name)
                self.collection = None
                logger.info(f"Cleared collection: {self.config.housing_collection_name}")
            else:
                logger.info("Collection does not exist, nothing to clear")
        except Exception as e:
            logger.warning(f"Failed to clear collection: {e}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """컬렉션 통계 정보"""
        collection = self.get_collection()
        
        try:
            all_docs = collection.get(include=['metadatas'])
            
            if not all_docs['metadatas']:
                return {"total_count": 0}
            
            # 통계 분석
            districts, themes, chunks_info = {}, {}, {}
            
            for metadata in all_docs['metadatas']:
                # 지역 통계
                district = metadata.get('시군구', '')
                if district:
                    districts[district] = districts.get(district, 0) + 1
                
                # 테마 통계
                theme = metadata.get('theme', '')
                if theme:
                    for part in theme.split():
                        themes[part] = themes.get(part, 0) + 1
                
                # 청크 통계
                chunk_id = metadata.get('chunk_id', 0)
                total_chunks = metadata.get('total_chunks', 1)
                chunks_info[f"chunk_{chunk_id}"] = chunks_info.get(f"chunk_{chunk_id}", 0) + 1
            
            return {
                "total_count": len(all_docs['metadatas']),
                "districts": dict(sorted(districts.items(), key=lambda x: x[1], reverse=True)),
                "themes": dict(sorted(themes.items(), key=lambda x: x[1], reverse=True)),
                "chunks_info": chunks_info
            }
            
        except Exception as e:
            logger.error(f"Failed to get statistics: {e}")
            raise


# ============================================================================
# 4. 메인 벡터DB 클래스 (Main Vector Database)
# ============================================================================

class HousingVectorDB:
    """주택 벡터DB 올인원 클래스 - 로드/분할/임베딩/저장"""
    
    def __init__(self):
        self.config = VectorConfig()
        self.embedder = KoreanEmbedder(config=self.config)
        self.collection = HousingCollection(self.embedder, self.config)

    def load_csv_data(self, csv_path: str = None) -> None:
        """CSV 파일에서 주택 데이터 로드 및 청킹"""
        csv_path = csv_path or self.config.default_csv_path
        logger.info(f"Loading data from {csv_path}")
        
        # CSV 읽기
        df = pd.read_csv(csv_path)
        df = df.dropna(subset=['주택명'])
        housing_data = df.to_dict('records')
        
        # 데이터 검증 및 정리
        valid_data = self.embedder.validate_housing_data(housing_data)
        
        # 벡터DB에 로드 (청킹 포함)
        self.add_documents(valid_data)
    
    def add_documents(self, documents: List[Dict[str, Any]], batch_size: int = None) -> None:
        """문서들을 벡터DB에 추가 (청킹 지원)"""
        batch_size = batch_size or self.config.batch_size
        
        # 임베딩 모델 로드
        if not self.embedder.is_loaded():
            self.embedder.load_model()
        
        logger.info(f"Adding {len(documents)} documents to vector database with chunking")
        
        with tqdm(total=len(documents), desc="Processing documents") as pbar:
            # 배치 단위로 처리
            for i in range(0, len(documents), batch_size):
                batch = documents[i:i + batch_size]
                
                try:
                    self.collection.add_documents(batch, batch_size=len(batch))
                    pbar.update(len(batch))
                except Exception as e:
                    logger.error(f"Failed to add batch: {e}")
                    pbar.update(len(batch))
        
        logger.info(f"Successfully loaded {self.collection.count()} document chunks")
    
    def get_info(self) -> Dict[str, Any]:
        """데이터베이스 정보"""
        self.collection.connect()
        collections = [col.name for col in self.collection.client.list_collections()]
        
        info = {
            "persist_directory": str(self.config.persist_directory),
            "embedding_model": self.config.embedding_model,
            "chunk_size": self.config.chunk_size,
            "chunk_overlap": self.config.chunk_overlap,
            "collections": collections,
            "total_collections": len(collections)
        }
        
        if self.config.housing_collection_name in collections:
            info["housing_collection"] = {
                "name": self.config.housing_collection_name,
                "count": self.collection.count()
            }
        
        return info
    
    def get_statistics(self) -> Dict[str, Any]:
        """데이터베이스 통계 정보"""
        return self.collection.get_statistics()
    
    def clear_database(self) -> None:
        """데이터베이스 초기화"""
        self.collection.clear()
        logger.info("Database cleared successfully")


# ============================================================================
# 5. 편의 함수들 (Utility Functions)
# ============================================================================

def create_housing_vector_db(csv_path: str = None) -> HousingVectorDB:
    """주택 벡터DB 생성 편의 함수"""
    db = HousingVectorDB()
    if csv_path:
        db.load_csv_data(csv_path)
    return db

def get_default_config() -> VectorConfig:
    """기본 설정 반환"""
    return VectorConfig()


# ============================================================================
# 6. 메인 실행부 (Main Execution)
# ============================================================================

if __name__ == "__main__":
    # 기본 로깅 설정
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 벡터DB 생성 및 테스트
    print("=" * 80)
    print("Housing Vector Database - All-in-One")
    print("=" * 80)
    
    try:
        # 벡터DB 인스턴스 생성
        db = HousingVectorDB()
        
        # 정보 출력
        info = db.get_info()
        print(f"✓ Persist Directory: {info['persist_directory']}")
        print(f"✓ Embedding Model: {info['embedding_model']}")
        print(f"✓ Chunk Size: {info['chunk_size']}")
        print(f"✓ Chunk Overlap: {info['chunk_overlap']}")
        
        # CSV 데이터 로드 (파일이 있는 경우)
        config = get_default_config()
        if Path(config.default_csv_path).exists():
            print(f"\n📁 Loading CSV data from: {config.default_csv_path}")
            db.load_csv_data()
            
            # 통계 출력
            stats = db.get_statistics()
            print(f"✓ Total document chunks: {stats['total_count']}")
            if stats.get('districts'):
                print(f"✓ Top districts: {list(stats['districts'].keys())[:3]}")
        else:
            print(f"\n⚠️  CSV file not found: {config.default_csv_path}")
            print("   Please provide CSV data to test the vector database.")
        
        print("\n✅ Housing Vector Database initialized successfully!")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        logger.exception("Failed to initialize Housing Vector Database")
