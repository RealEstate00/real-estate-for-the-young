"""
Data loader for housing vector database
"""

import pandas as pd
from pathlib import Path
from typing import List, Dict, Any, Optional
import logging
from tqdm import tqdm

from .client import VectorDBClient
from .embeddings.korean import KoreanEmbedder
from .collections.housing import HousingCollection
from .config import vector_db_config

logger = logging.getLogger(__name__)


class HousingDataLoader:
    """Loader for housing CSV data into vector database"""
    
    def __init__(
        self, 
        csv_path: Optional[Path] = None,
        client: Optional[VectorDBClient] = None,
        embedder: Optional[KoreanEmbedder] = None
    ):
        self.csv_path = csv_path or Path("backend/data/raw/for_vectorDB/housing_vector_data.csv")
        self.client = client or VectorDBClient()
        self.embedder = embedder or KoreanEmbedder()
        self.collection = HousingCollection(self.client, self.embedder)
        
    def load_csv_data(self) -> List[Dict[str, Any]]:
        """Load housing data from CSV file"""
        try:
            logger.info(f"Loading CSV data from {self.csv_path}")
            
            # Read CSV file
            df = pd.read_csv(self.csv_path)
            
            # Remove empty rows
            df = df.dropna(subset=['주택명'])
            
            # Convert to list of dictionaries
            housing_data = df.to_dict('records')
            
            logger.info(f"Loaded {len(housing_data)} housing records from CSV")
            return housing_data
            
        except Exception as e:
            logger.error(f"Failed to load CSV data: {e}")
            raise
    
    def validate_data(self, housing_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Validate and clean housing data"""
        valid_data = []
        
        for i, record in enumerate(housing_data):
            try:
                # Check required fields
                if not record.get('주택명'):
                    logger.warning(f"Record {i}: Missing 주택명, skipping")
                    continue
                
                # Clean string fields
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
    
    def load_to_vector_db(
        self, 
        housing_data: Optional[List[Dict[str, Any]]] = None,
        batch_size: Optional[int] = None,
        clear_existing: bool = False
    ) -> None:
        """Load housing data to vector database"""
        
        # Use provided data or load from CSV
        if housing_data is None:
            housing_data = self.load_csv_data()
        
        # Validate data
        housing_data = self.validate_data(housing_data)
        
        if not housing_data:
            logger.error("No valid housing data to load")
            return
        
        # Use configured batch size if not provided
        batch_size = batch_size or vector_db_config.batch_size
        
        try:
            # Clear existing data if requested
            if clear_existing:
                logger.info("Clearing existing housing collection")
                self.collection.clear()
            
            # Connect to database
            self.client.connect()
            
            # Load embedder model
            if not self.embedder.is_loaded():
                logger.info("Loading embedding model...")
                self.embedder.load_model()
            
            # Process data in batches with progress bar
            logger.info(f"Loading {len(housing_data)} records to vector database")
            
            with tqdm(total=len(housing_data), desc="Loading housing data") as pbar:
                for i in range(0, len(housing_data), batch_size):
                    batch = housing_data[i:i + batch_size]
                    
                    try:
                        self.collection.add_documents(batch, batch_size=len(batch))
                        pbar.update(len(batch))
                        
                    except Exception as e:
                        logger.error(f"Failed to load batch {i//batch_size + 1}: {e}")
                        # Continue with next batch
                        pbar.update(len(batch))
                        continue
            
            # Get final count
            final_count = self.collection.count()
            logger.info(f"Successfully loaded {final_count} documents to vector database")
            
        except Exception as e:
            logger.error(f"Failed to load data to vector database: {e}")
            raise
        finally:
            self.client.disconnect()
    
    def update_single_record(self, housing_record: Dict[str, Any]) -> None:
        """Update or add a single housing record"""
        try:
            self.client.connect()
            
            if not self.embedder.is_loaded():
                self.embedder.load_model()
            
            # Validate record
            validated_records = self.validate_data([housing_record])
            
            if not validated_records:
                logger.error("Invalid housing record provided")
                return
            
            # Add to collection
            self.collection.add_documents(validated_records, batch_size=1)
            logger.info("Successfully updated housing record")
            
        except Exception as e:
            logger.error(f"Failed to update housing record: {e}")
            raise
        finally:
            self.client.disconnect()
    
    def get_loading_statistics(self) -> Dict[str, Any]:
        """Get statistics about loaded data"""
        try:
            self.client.connect()
            
            # Get collection statistics
            stats = self.collection.get_housing_statistics()
            
            # Add database info
            db_info = self.client.get_database_info()
            stats['database_info'] = db_info
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get loading statistics: {e}")
            raise
        finally:
            self.client.disconnect()
    
    def preview_embeddings(self, n_samples: int = 3) -> List[Dict[str, Any]]:
        """Preview embeddings for sample data"""
        try:
            # Load sample data
            housing_data = self.load_csv_data()
            sample_data = housing_data[:n_samples]
            
            # Load embedder
            if not self.embedder.is_loaded():
                self.embedder.load_model()
            
            previews = []
            for record in sample_data:
                # Create text representation
                text = self.embedder.create_housing_text(record)
                
                # Generate embedding
                embedding = self.embedder.embed_housing_data(record)
                
                preview = {
                    'housing_name': record.get('주택명', ''),
                    'text_representation': text,
                    'embedding_dimension': len(embedding),
                    'embedding_sample': embedding[:10]  # First 10 dimensions
                }
                
                previews.append(preview)
            
            return previews
            
        except Exception as e:
            logger.error(f"Failed to preview embeddings: {e}")
            raise
