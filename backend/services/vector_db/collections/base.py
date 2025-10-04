"""
Base collection class for vector database
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Union
import logging

logger = logging.getLogger(__name__)


class BaseCollection(ABC):
    """Base class for vector database collections"""
    
    def __init__(self, client, embedder, collection_name: str):
        self.client = client
        self.embedder = embedder
        self.collection_name = collection_name
        self.collection = None
        
    def _get_collection(self):
        """Get or create the collection"""
        if self.collection is None:
            self.collection = self.client.get_or_create_collection(
                name=self.collection_name,
                metadata=self.get_collection_metadata()
            )
        return self.collection
    
    @abstractmethod
    def get_collection_metadata(self) -> Dict[str, Any]:
        """Get metadata for the collection"""
        pass
    
    @abstractmethod
    def prepare_document(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare a document for storage"""
        pass
    
    def add_documents(
        self, 
        documents: List[Dict[str, Any]], 
        batch_size: int = 32
    ) -> None:
        """Add documents to the collection"""
        collection = self._get_collection()
        
        # Process documents in batches
        for i in range(0, len(documents), batch_size):
            batch = documents[i:i + batch_size]
            
            # Prepare batch data
            ids = []
            embeddings = []
            metadatas = []
            documents_text = []
            
            for doc in batch:
                prepared_doc = self.prepare_document(doc)
                
                ids.append(prepared_doc['id'])
                embeddings.append(prepared_doc['embedding'])
                metadatas.append(prepared_doc['metadata'])
                documents_text.append(prepared_doc['document'])
            
            # Add to collection
            try:
                collection.add(
                    ids=ids,
                    embeddings=embeddings,
                    metadatas=metadatas,
                    documents=documents_text
                )
                logger.info(f"Added batch of {len(batch)} documents to {self.collection_name}")
                
            except Exception as e:
                logger.error(f"Failed to add batch to {self.collection_name}: {e}")
                raise
    
    def search_similar(
        self, 
        query: str, 
        n_results: int = 10,
        where: Optional[Dict[str, Any]] = None,
        where_document: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Search for similar documents"""
        collection = self._get_collection()
        
        try:
            # Generate query embedding
            query_embedding = self.embedder.encode(query)
            
            # Search
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                where=where,
                where_document=where_document,
                include=['metadatas', 'documents', 'distances']
            )
            
            # Format results
            formatted_results = []
            for i in range(len(results['ids'][0])):
                distance = results['distances'][0][i]
                
                # Convert cosine distance to cosine similarity
                # Cosine distance = 1 - cosine similarity
                # Therefore: cosine similarity = 1 - cosine distance
                # But ChromaDB might return squared cosine distance, so we need to handle both cases
                
                if distance <= 2.0:  # Normal cosine distance range [0, 2]
                    similarity = 1 - distance
                else:  # Might be squared distance or other metric
                    similarity = max(0, 1 - distance)  # Ensure non-negative
                
                # Clamp similarity to valid range [-1, 1] for cosine similarity
                similarity = max(-1.0, min(1.0, similarity))
                
                result = {
                    'id': results['ids'][0][i],
                    'document': results['documents'][0][i],
                    'metadata': results['metadatas'][0][i],
                    'distance': distance,
                    'similarity': similarity
                }
                formatted_results.append(result)
            
            return formatted_results
            
        except Exception as e:
            logger.error(f"Failed to search in {self.collection_name}: {e}")
            raise
    
    def get_document(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific document by ID"""
        collection = self._get_collection()
        
        try:
            results = collection.get(
                ids=[doc_id],
                include=['metadatas', 'documents']
            )
            
            if results['ids']:
                return {
                    'id': results['ids'][0],
                    'document': results['documents'][0],
                    'metadata': results['metadatas'][0]
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get document {doc_id} from {self.collection_name}: {e}")
            raise
    
    def delete_documents(self, doc_ids: List[str]) -> None:
        """Delete documents by IDs"""
        collection = self._get_collection()
        
        try:
            collection.delete(ids=doc_ids)
            logger.info(f"Deleted {len(doc_ids)} documents from {self.collection_name}")
            
        except Exception as e:
            logger.error(f"Failed to delete documents from {self.collection_name}: {e}")
            raise
    
    def count(self) -> int:
        """Get the number of documents in the collection"""
        collection = self._get_collection()
        return collection.count()
    
    def clear(self) -> None:
        """Clear all documents from the collection"""
        try:
            # Check if collection exists first
            existing_collections = self.client.list_collections()
            if self.collection_name in existing_collections:
                self.client.delete_collection(self.collection_name)
                self.collection = None
                logger.info(f"Cleared collection {self.collection_name}")
            else:
                logger.info(f"Collection {self.collection_name} does not exist, nothing to clear")
        except Exception as e:
            logger.warning(f"Failed to clear collection {self.collection_name}: {e}")
            # Don't raise exception for clearing non-existent collection
            pass
