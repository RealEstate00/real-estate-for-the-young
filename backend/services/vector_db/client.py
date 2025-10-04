"""
ChromaDB client for vector database operations
"""

import logging
from pathlib import Path
from typing import Optional, Dict, Any, List
import chromadb
from chromadb.config import Settings

from .config import vector_db_config

logger = logging.getLogger(__name__)


class VectorDBClient:
    """ChromaDB client wrapper"""
    
    def __init__(self, persist_directory: Optional[Path] = None):
        self.persist_directory = persist_directory or vector_db_config.persist_directory
        self.client = None
        self._ensure_directory()
        
    def _ensure_directory(self) -> None:
        """Ensure the persist directory exists"""
        self.persist_directory.mkdir(parents=True, exist_ok=True)
        
    def connect(self) -> None:
        """Connect to ChromaDB"""
        try:
            logger.info(f"Connecting to ChromaDB at {self.persist_directory}")
            
            self.client = chromadb.PersistentClient(
                path=str(self.persist_directory),
                settings=Settings(
                    anonymized_telemetry=False,
                    allow_reset=True
                )
            )
            
            logger.info("Successfully connected to ChromaDB")
            
        except Exception as e:
            logger.error(f"Failed to connect to ChromaDB: {e}")
            raise
    
    def disconnect(self) -> None:
        """Disconnect from ChromaDB"""
        if self.client:
            self.client = None
            logger.info("Disconnected from ChromaDB")
    
    def get_or_create_collection(
        self, 
        name: str, 
        metadata: Optional[Dict[str, Any]] = None,
        embedding_function = None
    ):
        """Get existing collection or create new one"""
        if self.client is None:
            self.connect()
        
        try:
            # Try to get existing collection
            collection = self.client.get_collection(
                name=name,
                embedding_function=embedding_function
            )
            logger.info(f"Retrieved existing collection: {name}")
            
        except Exception:
            # Create new collection if it doesn't exist
            collection = self.client.create_collection(
                name=name,
                metadata=metadata or {},
                embedding_function=embedding_function
            )
            logger.info(f"Created new collection: {name}")
        
        return collection
    
    def delete_collection(self, name: str) -> None:
        """Delete a collection"""
        if self.client is None:
            self.connect()
        
        try:
            self.client.delete_collection(name=name)
            logger.info(f"Deleted collection: {name}")
        except Exception as e:
            logger.error(f"Failed to delete collection {name}: {e}")
            raise
    
    def list_collections(self) -> List[str]:
        """List all collections"""
        if self.client is None:
            self.connect()
        
        try:
            collections = self.client.list_collections()
            collection_names = [col.name for col in collections]
            logger.info(f"Found {len(collection_names)} collections")
            return collection_names
        except Exception as e:
            logger.error(f"Failed to list collections: {e}")
            raise
    
    def reset_database(self) -> None:
        """Reset the entire database (use with caution!)"""
        if self.client is None:
            self.connect()
        
        try:
            self.client.reset()
            logger.warning("Database has been reset - all data deleted!")
        except Exception as e:
            logger.error(f"Failed to reset database: {e}")
            raise
    
    def get_database_info(self) -> Dict[str, Any]:
        """Get database information"""
        if self.client is None:
            self.connect()
        
        try:
            collections = self.list_collections()
            
            info = {
                "persist_directory": str(self.persist_directory),
                "collections": collections,
                "total_collections": len(collections)
            }
            
            # Get collection details
            collection_details = {}
            for col_name in collections:
                try:
                    col = self.client.get_collection(col_name)
                    collection_details[col_name] = {
                        "count": col.count(),
                        "metadata": col.metadata
                    }
                except Exception as e:
                    collection_details[col_name] = {"error": str(e)}
            
            info["collection_details"] = collection_details
            
            return info
            
        except Exception as e:
            logger.error(f"Failed to get database info: {e}")
            raise
    
    def __enter__(self):
        """Context manager entry"""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.disconnect()
