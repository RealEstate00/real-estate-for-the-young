# backend/services/vector_db/jina/search_test.py
"""
Interactive Search Testing Tool
대화형 벡터DB 검색 테스트 도구
"""

from pathlib import Path
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
import sys


# =============================================================================
# 1. Vector DB Loader
# =============================================================================

def load_vector_db(persist_directory: str):
    """Load ChromaDB from disk"""
    embeddings = HuggingFaceEmbeddings(
        model_name="jhgan/ko-sbert-nli",
        model_kwargs={'device': 'cpu'},
        encode_kwargs={'normalize_embeddings': True}
    )
    
    vector_db = Chroma(
        persist_directory=persist_directory,
        embedding_function=embeddings,
        collection_name="housing_data"
    )
    
    return vector_db


# =============================================================================
# 2. Search Functions
# =============================================================================

def display_results(results, query):
    """
    Display search results in formatted output
    
    Args:
        results: List of Document objects from similarity search
        query: Original search query
    """
    if not results:
        print("\nNo results found")
        return
    
    print(f"\nFound {len(results)} results for: '{query}'")
    print("=" * 80)
    
    for i, doc in enumerate(results, 1):
        print(f"\nResult {i}:")
        print("-" * 80)
        
        # Display metadata
        print(f"Housing Name: {doc.metadata.get('주택명', 'N/A')}")
        print(f"Address: {doc.metadata.get('지번주소', 'N/A')}")
        print(f"District: {doc.metadata.get('시군구', 'N/A')}")
        print(f"Dong: {doc.metadata.get('동명', 'N/A')}")
        
        # Display tags if available
        tags = doc.metadata.get('태그', '')
        if tags:
            print(f"Tags: {tags[:100]}...")
        
        # Display content preview
        print(f"\nContent preview:")
        print(doc.page_content[:200] + "..." if len(doc.page_content) > 200 else doc.page_content)
        print("-" * 80)


def search_with_score(vector_db, query, k=5):
    """
    Search with similarity scores
    
    Args:
        vector_db: ChromaDB instance
        query: Search query
        k: Number of results
    """
    results = vector_db.similarity_search_with_score(query, k=k)
    
    print(f"\nSearch results with scores for: '{query}'")
    print("=" * 80)
    
    for i, (doc, score) in enumerate(results, 1):
        print(f"\nResult {i} (Score: {score:.4f}):")
        print(f"  Title: {doc.metadata.get('주택명', 'N/A')}")
        print(f"  Address: {doc.metadata.get('지번주소', 'N/A')[:60]}...")
        print("-" * 80)


# =============================================================================
# 3. Interactive Search Mode
# =============================================================================

def interactive_mode(vector_db):
    """Interactive search interface"""
    
    print("\n" + "=" * 80)
    print("INTERACTIVE SEARCH MODE")
    print("=" * 80)
    print("Commands:")
    print("  - Enter search query to search")
    print("  - 'score' + query: Search with similarity scores")
    print("  - 'quit' or 'exit': Exit the program")
    print("=" * 80)
    
    while True:
        try:
            print("\n")
            user_input = input("Search Query > ").strip()
            
            if not user_input:
                continue
            
            if user_input.lower() in ['quit', 'exit', 'q']:
                print("\nExiting...")
                break
            
            # Check for score command
            if user_input.lower().startswith('score '):
                query = user_input[6:].strip()
                if query:
                    k = int(input("Number of results (default 5): ") or "5")
                    search_with_score(vector_db, query, k)
            else:
                # Normal search
                query = user_input
                k = int(input("Number of results (default 5): ") or "5")
                results = vector_db.similarity_search(query, k=k)
                display_results(results, query)
                
        except KeyboardInterrupt:
            print("\n\nExiting...")
            break
        except Exception as e:
            print(f"\nError: {e}")


# =============================================================================
# 4. Batch Test Mode
# =============================================================================

def batch_test_mode(vector_db):
    """Run predefined test queries"""
    
    print("\n" + "=" * 80)
    print("BATCH TEST MODE")
    print("=" * 80)
    
    test_queries = [
        ("강남 청년주택", "Test for Gangnam youth housing"),
        ("지하철역 근처", "Test for subway proximity"),
        ("공원", "Test for park"),
        ("마포구", "Test for Mapo district"),
        ("신혼부부", "Test for newlyweds"),
    ]
    
    for query, description in test_queries:
        print(f"\n{'=' * 80}")
        print(f"Test: {description}")
        print(f"Query: '{query}'")
        print("=" * 80)
        
        results = vector_db.similarity_search(query, k=3)
        
        if results:
            print(f"Found {len(results)} results:")
            for i, doc in enumerate(results, 1):
                print(f"  [{i}] {doc.metadata.get('주택명', 'N/A')}")
                print(f"      {doc.metadata.get('시군구', 'N/A')} {doc.metadata.get('동명', 'N/A')}")
        else:
            print("No results found")
    
    print("\n" + "=" * 80)
    print("Batch test complete")
    print("=" * 80)


# =============================================================================
# 5. Main Function
# =============================================================================

def main():
    """Main entry point"""
    
    # Setup paths
    base_path = Path(__file__).parent.parent.parent.parent
    persist_directory = str(base_path / "data" / "vector_db" / "chroma")
    
    print("=" * 80)
    print("CHROMADB SEARCH TEST TOOL")
    print("=" * 80)
    print(f"DB Location: {persist_directory}")
    
    # Check if DB exists
    if not Path(persist_directory).exists():
        print(f"\nERROR: ChromaDB not found at {persist_directory}")
        print("Please run create_chroma_db.py first!")
        return
    
    # Load DB
    print("\nLoading ChromaDB...")
    try:
        vector_db = load_vector_db(persist_directory)
        print("ChromaDB loaded successfully!")
    except Exception as e:
        print(f"\nERROR: Failed to load ChromaDB: {e}")
        return
    
    # Check command line arguments
    if len(sys.argv) > 1:
        mode = sys.argv[1].lower()
        
        if mode == '--batch':
            batch_test_mode(vector_db)
        elif mode == '--help':
            print("\nUsage:")
            print("  python search_test.py           # Interactive mode")
            print("  python search_test.py --batch   # Batch test mode")
            print("  python search_test.py --help    # Show this help")
        else:
            print(f"\nUnknown option: {sys.argv[1]}")
            print("Use --help for usage information")
    else:
        interactive_mode(vector_db)


if __name__ == "__main__":
    main()