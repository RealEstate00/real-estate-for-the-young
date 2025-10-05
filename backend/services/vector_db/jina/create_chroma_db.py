# backend/services/vector_db/jina/create_chroma_db.py
"""
ChromaDB Vector Database Creator
CSV 파일을 읽어 ChromaDB 벡터 데이터베이스 생성
"""

import pandas as pd
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document
from pathlib import Path
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# =============================================================================
# 1. ChromaDB Creator Class
# =============================================================================

class ChromaDBCreator:
    """
    CSV 데이터를 ChromaDB 벡터 데이터베이스로 변환
    """
    
    def __init__(
        self,
        csv_path: str,
        embedding_model: str = "jhgan/ko-sbert-nli",
        chunk_size: int = 500,
        chunk_overlap: int = 50,
        collection_name: str = "housing_data"
    ):
        """
        Initialize ChromaDB Creator
        
        Args:
            csv_path: Path to input CSV file
            embedding_model: Korean embedding model name
            chunk_size: Maximum chunk size for text splitting
            chunk_overlap: Overlap between chunks
            collection_name: ChromaDB collection name
        """
        self.csv_path = csv_path
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.collection_name = collection_name
        
        # -----------------------------
        # 1.1. Initialize Embedding Model
        # -----------------------------
        logger.info(f"Loading embedding model: {embedding_model}")
        self.embeddings = HuggingFaceEmbeddings(
            model_name=embedding_model,
            model_kwargs={'device': 'cpu'},
            encode_kwargs={'normalize_embeddings': True}
        )
        
        # -----------------------------
        # 1.2. Initialize Text Splitter
        # -----------------------------
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", ". ", " ", ""]
        )
    
    # =============================================================================
    # 2. Data Loading
    # =============================================================================
    
    def load_csv(self) -> pd.DataFrame:
        """
        Load CSV file
        
        Returns:
            DataFrame containing housing data
        """
        logger.info(f"Loading CSV: {self.csv_path}")
        df = pd.read_csv(self.csv_path)
        logger.info(f"Loaded {len(df)} records")
        return df
    
    # =============================================================================
    # 3. Document Creation
    # =============================================================================
    
    def create_documents(self, df: pd.DataFrame) -> list[Document]:
        """
        Convert DataFrame rows to LangChain Documents
        
        Args:
            df: Input DataFrame
            
        Returns:
            List of Document objects
        """
        documents = []
        
        for idx, row in df.iterrows():
            # Create searchable text content
            content = self._create_content(row)
            
            # Create metadata for filtering
            metadata = self._create_metadata(row, idx)
            
            # Create Document object
            doc = Document(
                page_content=content,
                metadata=metadata
            )
            documents.append(doc)
        
        logger.info(f"Created {len(documents)} documents")
        return documents
    
    def _create_content(self, row: pd.Series) -> str:
        """
        Convert CSV row to searchable text
        
        Args:
            row: DataFrame row
            
        Returns:
            Formatted text string
        """
        parts = []
        
        if pd.notna(row.get('주택명')):
            parts.append(f"주택명: {row['주택명']}")
        
        if pd.notna(row.get('지번주소')):
            parts.append(f"지번주소: {row['지번주소']}")
        
        if pd.notna(row.get('도로명주소')):
            parts.append(f"도로명주소: {row['도로명주소']}")
        
        if pd.notna(row.get('시군구')):
            parts.append(f"시군구: {row['시군구']}")
        
        if pd.notna(row.get('동명')):
            parts.append(f"동명: {row['동명']}")
        
        if pd.notna(row.get('태그')):
            parts.append(f"태그: {row['태그']}")
        
        return "\n".join(parts)
    
    def _create_metadata(self, row: pd.Series, idx: int) -> dict:
        """
        Create metadata for filtering and display
        
        Args:
            row: DataFrame row
            idx: Row index
            
        Returns:
            Metadata dictionary
        """
        metadata = {
            'row_id': int(idx),
            'source': 'housing_vector_data.csv'
        }
        
        # Add all columns as metadata (ChromaDB requires specific types)
        key_fields = ['주택명', '지번주소', '도로명주소', '시군구', '동명', '태그']
        
        for field in key_fields:
            if field in row and pd.notna(row[field]):
                metadata[field] = str(row[field])
        
        return metadata
    
    # =============================================================================
    # 4. Vector DB Creation
    # =============================================================================
    
    def create_vector_db(self, persist_directory: str = None) -> Chroma:
        """
        Create ChromaDB vector database from CSV
        
        Args:
            persist_directory: Directory to save ChromaDB data
            
        Returns:
            Chroma vector database instance
        """
        
        # -----------------------------
        # 4.1. Load CSV Data
        # -----------------------------
        df = self.load_csv()
        
        # -----------------------------
        # 4.2. Create Documents
        # -----------------------------
        documents = self.create_documents(df)
        
        # -----------------------------
        # 4.3. Split Text into Chunks
        # -----------------------------
        logger.info("Splitting documents into chunks...")
        split_docs = self.text_splitter.split_documents(documents)
        logger.info(f"Created {len(split_docs)} text chunks")
        
        # -----------------------------
        # 4.4. Create Vector DB
        # -----------------------------
        if persist_directory is None:
            persist_directory = "backend/data/vector_db/chroma"
        
        logger.info("Creating ChromaDB vector database...")
        logger.info(f"This may take a few minutes for embedding generation...")
        
        vector_db = Chroma.from_documents(
            documents=split_docs,
            embedding=self.embeddings,
            collection_name=self.collection_name,
            persist_directory=persist_directory
        )
        
        logger.info(f"✅ Vector DB saved to: {persist_directory}")
        
        return vector_db


# =============================================================================
# 5. Main Execution
# =============================================================================

def main():
    """Main execution function"""
    
    # -----------------------------
    # 5.1. Set Paths
    # -----------------------------
    base_path = Path(__file__).parent.parent.parent.parent
    csv_path = base_path / "data" / "vector_db" / "housing_vector_data.csv"
    persist_directory = base_path / "data" / "vector_db" / "chroma"
    
    print("=" * 80)
    print("ChromaDB Vector Database Creator")
    print("=" * 80)
    print(f"Input CSV: {csv_path}")
    print(f"Output DB: {persist_directory}")
    print("=" * 80)
    
    # Check if CSV exists
    if not csv_path.exists():
        print(f"\n❌ Error: CSV file not found at {csv_path}")
        print("Please run create_vector_db_csv.py first!")
        return
    
    # -----------------------------
    # 5.2. Create Vector DB
    # -----------------------------
    creator = ChromaDBCreator(
        csv_path=str(csv_path),
        collection_name="housing_data"
    )
    
    vector_db = creator.create_vector_db(str(persist_directory))
    
    # -----------------------------
    # 5.3. Test Search
    # -----------------------------
    print("\n" + "=" * 80)
    print("Test Search")
    print("=" * 80)
    
    test_queries = [
        "강남 청년주택",
        "지하철역 근처",
        "공원"
    ]
    
    for query in test_queries:
        print(f"\n🔍 Query: '{query}'")
        results = vector_db.similarity_search(query, k=3)
        
        for i, doc in enumerate(results, 1):
            print(f"\n  [{i}] {doc.metadata.get('주택명', 'N/A')}")
            print(f"      주소: {doc.metadata.get('지번주소', 'N/A')[:60]}...")
    
    print("\n" + "=" * 80)
    print("✅ ChromaDB creation complete!")
    print("=" * 80)


if __name__ == "__main__":
    main()