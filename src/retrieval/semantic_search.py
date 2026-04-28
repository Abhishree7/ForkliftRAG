"""Semantic search using dense vector embeddings with Qdrant."""
from typing import List, Dict, Optional
from sentence_transformers import SentenceTransformer
from src.indexing.qdrant_indexer import QdrantIndexer
from src.indexing.metadata_handler import MetadataHandler
import logging

logger = logging.getLogger(__name__)

# BGE-M3 retrieval query prefix (recommended by BAAI)
_QUERY_PREFIX = "Represent this query for retrieval: "


class SemanticSearch:
    """Semantic search using dense vector embeddings."""

    def __init__(self, indexer: QdrantIndexer,
                 model_name: str = "BAAI/bge-m3",
                 device: str = "cpu"):
        """
        Initialize semantic search.

        Args:
            indexer: QdrantIndexer instance
            model_name: Name of the embedding model (default: BGE-M3)
            device: Device to run model on ('cpu' or 'cuda')
        """
        self.indexer = indexer
        self.device = device
        self.model_name = model_name
        self.metadata_handler = MetadataHandler()
        self.embedding_dim = 1024  # BGE-M3 dense embedding dimension

        try:
            self.model = SentenceTransformer(model_name, device=device)
            logger.info(f"Loaded semantic model: {model_name} (dim={self.embedding_dim})")
        except Exception as e:
            logger.error(f"Error loading semantic model: {str(e)}")
            raise

    def encode_query(self, query: str) -> List[float]:
        """
        Encode query text into a dense vector.

        Args:
            query: Search query string

        Returns:
            Dense vector embedding as a list of floats
        """
        try:
            vec = self.model.encode(
                _QUERY_PREFIX + query,
                normalize_embeddings=True,
            )
            return vec.tolist()
        except Exception as e:
            logger.error(f"Error encoding query: {str(e)}")
            raise
    
    def search(self, query: str, company_id: str, filters: Optional[Dict] = None,
               size: int = 10) -> List[Dict]:
        """
        Execute semantic search using dense vector similarity.
        
        Args:
            query: Search query string
            company_id: UUID of the company (for data isolation)
            filters: Optional filters (document_types, equipment_types, date_range)
            size: Maximum number of results
        
        Returns:
            List of search hits
        """
        # Encode query
        query_embedding = self.encode_query(query)
        
        # Build filter
        filter_condition = self.metadata_handler.build_qdrant_filter(company_id, filters)
        
        try:
            hits = self.indexer.search_vectors(
                query_vector=query_embedding,
                filter_condition=filter_condition,
                limit=size
            )
            logger.info(f"Semantic search returned {len(hits)} results for query: {query[:50]}")
            return hits
        except Exception as e:
            logger.error(f"Error in semantic search: {str(e)}")
            raise
