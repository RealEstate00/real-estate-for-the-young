"""
Housing Vector Database Test
임베딩 품질 및 데이터 로딩 테스트
"""

import logging
import pandas as pd
from pathlib import Path
from typing import List, Dict, Any
import sys

# 현재 모듈 import
from .chromadb import HousingVectorDB, VectorConfig, KoreanEmbedder

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# ============================================================================
# 1. 데이터 로딩 테스트
# ============================================================================

def test_data_loading():
    """CSV 데이터 로딩 테스트"""
    print("\n" + "=" * 80)
    print("1. DATA LOADING TEST")
    print("=" * 80)
    
    try:
        # 벡터DB 인스턴스 생성
        db = HousingVectorDB()
        
        # 설정 확인
        config = db.config
        print(f"✓ Chunk Size: {config.chunk_size}")
        print(f"✓ Chunk Overlap: {config.chunk_overlap}")
        print(f"✓ Embedding Model: {config.embedding_model}")
        
        # CSV 파일 존재 확인
        csv_path = config.default_csv_path
        if not Path(csv_path).exists():
            print(f"❌ CSV file not found: {csv_path}")
            return False
        
        # 데이터 로딩
        print(f"\n📁 Loading data from: {csv_path}")
        db.clear_database()  # 기존 데이터 클리어
        db.load_csv_data(csv_path)
        
        # 결과 확인
        info = db.get_info()
        stats = db.get_statistics()
        
        print(f"✅ Successfully loaded {stats['total_count']} document chunks")
        print(f"✓ Collection: {info['housing_collection']['name']}")
        print(f"✓ Document count: {info['housing_collection']['count']}")
        
        if stats.get('chunks_info'):
            print(f"✓ Chunk distribution: {stats['chunks_info']}")
        
        return True
        
    except Exception as e:
        print(f"❌ Data loading failed: {e}")
        logger.exception("Data loading test failed")
        return False


# ============================================================================
# 2. 임베딩 품질 테스트
# ============================================================================

def test_embedding_quality():
    """임베딩 품질 테스트"""
    print("\n" + "=" * 80)
    print("2. EMBEDDING QUALITY TEST")
    print("=" * 80)
    
    try:
        # 임베더 생성
        embedder = KoreanEmbedder()
        embedder.load_model()
        
        # 테스트 텍스트들
        test_texts = [
            "청년주택 서울 강남구",
            "신혼부부 주택 마포구", 
            "육아 친화적 주택",
            "지하철역 근처 주택",
            "공원 인근 주택"
        ]
        
        print("📊 Testing embedding similarity...")
        
        # 임베딩 생성
        embeddings = []
        for text in test_texts:
            embedding = embedder.encode_text(text)
            embeddings.append(embedding)
            print(f"✓ '{text}' -> embedding shape: {len(embedding)}")
        
        # 유사도 계산 (코사인 유사도)
        import numpy as np
        
        print(f"\n📈 Similarity Matrix:")
        print("    ", end="")
        for i, text in enumerate(test_texts):
            print(f"{i:>6}", end="")
        print()
        
        for i, emb1 in enumerate(embeddings):
            print(f"{i}: ", end="")
            for j, emb2 in enumerate(embeddings):
                # 코사인 유사도 계산
                similarity = np.dot(emb1, emb2) / (np.linalg.norm(emb1) * np.linalg.norm(emb2))
                print(f"{similarity:>6.3f}", end="")
            print(f"  ({test_texts[i][:15]}...)")
        
        # 관련성 테스트
        print(f"\n🔍 Relevance Tests:")
        청년_신혼_sim = np.dot(embeddings[0], embeddings[1]) / (np.linalg.norm(embeddings[0]) * np.linalg.norm(embeddings[1]))
        지하철_공원_sim = np.dot(embeddings[3], embeddings[4]) / (np.linalg.norm(embeddings[3]) * np.linalg.norm(embeddings[4]))
        
        print(f"✓ '청년주택' vs '신혼부부주택' 유사도: {청년_신혼_sim:.3f}")
        print(f"✓ '지하철역' vs '공원' 유사도: {지하철_공원_sim:.3f}")
        
        if 청년_신혼_sim > 0.5:
            print("✅ 주택 유형 간 유사도가 적절합니다")
        else:
            print("⚠️  주택 유형 간 유사도가 낮습니다")
        
        return True
        
    except Exception as e:
        print(f"❌ Embedding quality test failed: {e}")
        logger.exception("Embedding quality test failed")
        return False


# ============================================================================
# 3. 문서 분할 테스트
# ============================================================================

def test_text_chunking():
    """문서 분할 테스트"""
    print("\n" + "=" * 80)
    print("3. TEXT CHUNKING TEST")
    print("=" * 80)
    
    try:
        embedder = KoreanEmbedder()
        
        # 테스트용 긴 텍스트
        long_text = """
        주택명: 서울시 청년주택 강남센터 
        주소: 서울특별시 강남구 테헤란로 123번길 45 
        지역: 강남구 
        동: 역삼동 
        특성: 테마: 청년, 지하철: 2호선 강남역 도보 5분, 자격요건: 만 19-39세 무주택자, 
        마트: 이마트 도보 3분, 병원: 강남세브란스병원 차량 10분, 학교: 역삼초등학교 도보 7분, 
        시설: 피트니스센터, 스터디룸, 카페라운지, 세탁실, 주차장, 카페: 스타벅스 도보 2분
        이 주택은 청년들을 위한 특별한 공간으로 설계되었습니다. 현대적인 시설과 편의성을 갖춘 
        원룸형 주택으로, 직장인과 대학생 모두에게 적합합니다. 지하철역과 가까워 교통이 편리하며, 
        주변에 다양한 편의시설이 위치해 있어 생활하기 매우 편리합니다.
        """
        
        print(f"📄 Original text length: {len(long_text)} characters")
        
        # 텍스트 분할
        chunks = embedder.split_text(long_text.strip())
        
        print(f"✂️  Split into {len(chunks)} chunks")
        print(f"✓ Chunk size setting: {embedder.config.chunk_size}")
        print(f"✓ Chunk overlap setting: {embedder.config.chunk_overlap}")
        
        # 각 청크 정보 출력
        for i, chunk in enumerate(chunks):
            print(f"\n📝 Chunk {i+1} (length: {len(chunk)}):")
            print(f"   {chunk[:100]}..." if len(chunk) > 100 else f"   {chunk}")
        
        # 청크 크기 검증
        oversized_chunks = [i for i, chunk in enumerate(chunks) if len(chunk) > embedder.config.chunk_size + 50]
        if oversized_chunks:
            print(f"⚠️  Oversized chunks found: {oversized_chunks}")
        else:
            print("✅ All chunks are within size limits")
        
        return True
        
    except Exception as e:
        print(f"❌ Text chunking test failed: {e}")
        logger.exception("Text chunking test failed")
        return False


# ============================================================================
# 4. 간단한 유사도 검색 테스트
# ============================================================================

def test_similarity_search():
    """유사도 검색 테스트 (품질 확인용)"""
    print("\n" + "=" * 80)
    print("4. SIMILARITY SEARCH TEST")
    print("=" * 80)
    
    try:
        # 벡터DB 로드
        db = HousingVectorDB()
        
        # 데이터가 있는지 확인
        info = db.get_info()
        if not info.get('housing_collection') or info['housing_collection']['count'] == 0:
            print("⚠️  No data in vector database. Please run data loading test first.")
            return False
        
        # ChromaDB 직접 접근하여 간단한 검색 테스트
        collection = db.collection.get_collection()
        
        # 테스트 쿼리들
        test_queries = [
            "청년주택",
            "강남구 주택", 
            "지하철역 근처",
            "신혼부부"
        ]
        
        print("🔍 Testing similarity search...")
        
        for query in test_queries:
            print(f"\n📋 Query: '{query}'")
            
            # 쿼리 임베딩 생성
            query_embedding = db.embedder.encode_text(query)
            
            # 검색 실행
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=3,
                include=['metadatas', 'documents', 'distances']
            )
            
            if results['ids'][0]:
                print(f"   Found {len(results['ids'][0])} results:")
                for i in range(len(results['ids'][0])):
                    distance = results['distances'][0][i]
                    similarity = 1 - distance  # 거리를 유사도로 변환
                    metadata = results['metadatas'][0][i]
                    document = results['documents'][0][i]
                    
                    print(f"   [{i+1}] Similarity: {similarity:.3f}")
                    print(f"       주택명: {metadata.get('주택명', 'N/A')}")
                    print(f"       지역: {metadata.get('시군구', 'N/A')} {metadata.get('동명', 'N/A')}")
                    print(f"       청크: {metadata.get('chunk_id', 0)}/{metadata.get('total_chunks', 1)}")
                    print(f"       내용: {document[:80]}...")
            else:
                print("   No results found")
        
        print("\n✅ Similarity search test completed")
        return True
        
    except Exception as e:
        print(f"❌ Similarity search test failed: {e}")
        logger.exception("Similarity search test failed")
        return False


# ============================================================================
# 5. 대화형 테스트
# ============================================================================

def interactive_test():
    """대화형 테스트 모드"""
    print("\n" + "=" * 80)
    print("5. INTERACTIVE TEST MODE")
    print("=" * 80)
    print("Commands:")
    print("  - 'load': Load CSV data")
    print("  - 'info': Show database info")
    print("  - 'stats': Show statistics")
    print("  - 'search <query>': Search for housing")
    print("  - 'clear': Clear database")
    print("  - 'quit': Exit")
    print("=" * 80)
    
    db = HousingVectorDB()
    
    while True:
        try:
            user_input = input("\n> ").strip()
            
            if not user_input:
                continue
            
            if user_input.lower() in ['quit', 'exit', 'q']:
                print("Goodbye!")
                break
            
            elif user_input.lower() == 'load':
                print("Loading CSV data...")
                db.load_csv_data()
                print("✅ Data loaded successfully")
            
            elif user_input.lower() == 'info':
                info = db.get_info()
                print(f"📊 Database Info:")
                for key, value in info.items():
                    print(f"   {key}: {value}")
            
            elif user_input.lower() == 'stats':
                stats = db.get_statistics()
                print(f"📈 Statistics:")
                for key, value in stats.items():
                    if isinstance(value, dict) and len(value) > 5:
                        print(f"   {key}: {dict(list(value.items())[:5])}... (showing top 5)")
                    else:
                        print(f"   {key}: {value}")
            
            elif user_input.lower().startswith('search '):
                query = user_input[7:].strip()
                if query:
                    # 간단한 검색 실행
                    collection = db.collection.get_collection()
                    query_embedding = db.embedder.encode_text(query)
                    
                    results = collection.query(
                        query_embeddings=[query_embedding],
                        n_results=3,
                        include=['metadatas', 'documents', 'distances']
                    )
                    
                    if results['ids'][0]:
                        print(f"🔍 Search results for '{query}':")
                        for i in range(len(results['ids'][0])):
                            distance = results['distances'][0][i]
                            similarity = 1 - distance
                            metadata = results['metadatas'][0][i]
                            
                            print(f"   [{i+1}] {metadata.get('주택명', 'N/A')} (similarity: {similarity:.3f})")
                            print(f"       {metadata.get('시군구', 'N/A')} {metadata.get('동명', 'N/A')}")
                    else:
                        print("No results found")
                else:
                    print("Please provide a search query")
            
            elif user_input.lower() == 'clear':
                db.clear_database()
                print("✅ Database cleared")
            
            else:
                print(f"Unknown command: {user_input}")
                
        except KeyboardInterrupt:
            print("\nGoodbye!")
            break
        except Exception as e:
            print(f"Error: {e}")


# ============================================================================
# 6. 전체 테스트 실행
# ============================================================================

def run_all_tests():
    """모든 테스트 실행"""
    print("🚀 Running all Housing Vector Database tests...")
    
    tests = [
        ("Data Loading", test_data_loading),
        ("Embedding Quality", test_embedding_quality),
        ("Text Chunking", test_text_chunking),
        ("Similarity Search", test_similarity_search)
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
            results[test_name] = False
    
    # 결과 요약
    print("\n" + "=" * 80)
    print("TEST RESULTS SUMMARY")
    print("=" * 80)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{test_name:<20}: {status}")
        if result:
            passed += 1
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Vector database is working correctly.")
    else:
        print("⚠️  Some tests failed. Please check the logs above.")
    
    return passed == total


# ============================================================================
# 7. 메인 실행부
# ============================================================================

def main():
    """메인 함수"""
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == 'all':
            run_all_tests()
        elif command == 'load':
            test_data_loading()
        elif command == 'embedding':
            test_embedding_quality()
        elif command == 'chunk':
            test_text_chunking()
        elif command == 'search':
            test_similarity_search()
        elif command == 'interactive':
            interactive_test()
        else:
            print(f"Unknown command: {command}")
            print("Available commands: all, load, embedding, chunk, search, interactive")
    else:
        # 기본: 대화형 모드
        interactive_test()


if __name__ == "__main__":
    main()
