# backend/services/vector_db/jina/test_vector_db.py
"""
Vector DB Validation and Testing Script
ChromaDB 생성 검증 및 기본 테스트
"""

from pathlib import Path
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
import time
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# =============================================================================
# 1. Load Vector DB
# =============================================================================

def load_vector_db(persist_directory: str):
    """
    Load existing ChromaDB from disk
    
    Args:
        persist_directory: Path to ChromaDB directory
        
    Returns:
        Loaded Chroma vector database
    """
    logger.info(f"Loading vector DB from: {persist_directory}")
    
    # Initialize same embedding model used during creation
    embeddings = HuggingFaceEmbeddings(
        model_name="jhgan/ko-sbert-nli",
        model_kwargs={'device': 'cpu'},
        encode_kwargs={'normalize_embeddings': True}
    )
    
    # Load ChromaDB
    vector_db = Chroma(
        persist_directory=persist_directory,
        embedding_function=embeddings,
        collection_name="housing_data"
    )
    
    logger.info("Vector DB loaded successfully")
    return vector_db


# =============================================================================
# 2. Validation Tests
# =============================================================================

def test_collection_info(vector_db):
    """Test 1: Check collection information"""
    print("\n" + "=" * 80)
    print("Test 1: Collection Information")
    print("=" * 80)
    
    collection = vector_db._collection
    count = collection.count()
    
    print(f"Collection name: {collection.name}")
    print(f"Total documents: {count}")
    
    if count > 0:
        print("Status: PASS")
        return True
    else:
        print("Status: FAIL - No documents found")
        return False


def test_basic_search(vector_db):
    """Test 2: Basic similarity search"""
    print("\n" + "=" * 80)
    print("Test 2: Basic Similarity Search")
    print("=" * 80)
    
    test_query = "강남"
    print(f"Query: '{test_query}'")
    
    try:
        results = vector_db.similarity_search(test_query, k=3)
        
        if results:
            print(f"Results found: {len(results)}")
            print("\nTop result:")
            print(f"  Title: {results[0].metadata.get('주택명', 'N/A')}")
            print(f"  Address: {results[0].metadata.get('지번주소', 'N/A')[:60]}...")
            print("Status: PASS")
            return True
        else:
            print("Status: FAIL - No results returned")
            return False
            
    except Exception as e:
        print(f"Status: FAIL - Error: {e}")
        return False


def test_multiple_queries(vector_db):
    """Test 3: Multiple diverse queries"""
    print("\n" + "=" * 80)
    print("Test 3: Multiple Query Test")
    print("=" * 80)
    
    test_cases = [
        "강남 주택",
        "지하철역 근처",
        "공원",
        "마포구",
    ]
    
    passed = 0
    
    for query in test_cases:
        results = vector_db.similarity_search(query, k=3)
        status = "PASS" if results else "FAIL"
        print(f"  '{query}': {status} ({len(results)} results)")
        if results:
            passed += 1
    
    print(f"\nPassed: {passed}/{len(test_cases)}")
    return passed == len(test_cases)


def test_search_performance(vector_db):
    """Test 4: Search performance benchmark"""
    print("\n" + "=" * 80)
    print("Test 4: Search Performance")
    print("=" * 80)
    
    query = "서울 주택"
    num_trials = 10
    
    times = []
    for _ in range(num_trials):
        start = time.time()
        vector_db.similarity_search(query, k=5)
        times.append((time.time() - start) * 1000)  # Convert to ms
    
    avg_time = sum(times) / len(times)
    min_time = min(times)
    max_time = max(times)
    
    print(f"Trials: {num_trials}")
    print(f"Average time: {avg_time:.2f}ms")
    print(f"Min time: {min_time:.2f}ms")
    print(f"Max time: {max_time:.2f}ms")
    
    # Consider < 100ms as good performance
    if avg_time < 100:
        print("Status: PASS (Good performance)")
        return True
    elif avg_time < 200:
        print("Status: PASS (Acceptable performance)")
        return True
    else:
        print("Status: WARNING (Slow performance)")
        return False


def test_metadata_retrieval(vector_db):
    """Test 5: Metadata retrieval"""
    print("\n" + "=" * 80)
    print("Test 5: Metadata Retrieval")
    print("=" * 80)
    
    results = vector_db.similarity_search("주택", k=1)
    
    if results:
        metadata = results[0].metadata
        required_fields = ['주택명', '지번주소', '시군구']
        
        print("Checking required metadata fields:")
        all_present = True
        for field in required_fields:
            present = field in metadata
            status = "OK" if present else "MISSING"
            print(f"  {field}: {status}")
            if not present:
                all_present = False
        
        if all_present:
            print("Status: PASS")
            return True
        else:
            print("Status: FAIL - Missing required fields")
            return False
    else:
        print("Status: FAIL - No results to check metadata")
        return False


# =============================================================================
# 3. Main Test Runner
# =============================================================================

def run_all_tests():
    """Run all validation tests"""
    
    # Setup paths
    base_path = Path(__file__).parent.parent.parent.parent
    persist_directory = str(base_path / "data" / "vector_db" / "chroma")
    
    print("=" * 80)
    print("CHROMADB VALIDATION TEST SUITE")
    print("=" * 80)
    print(f"DB Location: {persist_directory}")
    print("=" * 80)
    
    # Check if DB exists
    if not Path(persist_directory).exists():
        print(f"\nERROR: ChromaDB not found at {persist_directory}")
        print("Please run create_chroma_db.py first!")
        return
    
    # Load DB
    try:
        vector_db = load_vector_db(persist_directory)
    except Exception as e:
        print(f"\nERROR: Failed to load ChromaDB: {e}")
        return
    
    # Run tests
    results = []
    results.append(("Collection Info", test_collection_info(vector_db)))
    results.append(("Basic Search", test_basic_search(vector_db)))
    results.append(("Multiple Queries", test_multiple_queries(vector_db)))
    results.append(("Search Performance", test_search_performance(vector_db)))
    results.append(("Metadata Retrieval", test_metadata_retrieval(vector_db)))
    
    # Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "PASS" if result else "FAIL"
        print(f"  {test_name}: {status}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\nStatus: ALL TESTS PASSED")
    else:
        print(f"\nStatus: {total - passed} TESTS FAILED")
    
    print("=" * 80)


if __name__ == "__main__":
    run_all_tests()