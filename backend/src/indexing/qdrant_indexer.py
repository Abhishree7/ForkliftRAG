"""Qdrant indexer for document indexing."""
from typing import List, Dict, Optional
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue, Range
import uuid
import logging

logger = logging.getLogger(__name__)


class QdrantIndexer:
    """Handler for indexing documents in Qdrant."""
    
    def __init__(self, host: str = "localhost", port: int = 6333,
                 collection_name: str = "logistics_documents", timeout: int = 30):
        """
        Initialize Qdrant client.
        
        Args:
            host: Qdrant host
            port: Qdrant port
            collection_name: Name of the collection
            timeout: Request timeout in seconds
        """
        self.host = host
        self.port = port
        self.collection_name = collection_name
        self.timeout = timeout
        
        try:
            self.client = QdrantClient(
                host=host,
                port=port,
                timeout=timeout
            )
            # Test connection
            collections = self.client.get_collections()
            logger.info(f"Connected to Qdrant at {host}:{port}")
        except Exception as e:
            logger.error(f"Error connecting to Qdrant: {str(e)}")
            raise
    
    def create_collection(self, embedding_dim: int = 1024, force: bool = False):
        """
        Create Qdrant collection with specified vector configuration.
        
        Args:
            embedding_dim: Dimension of dense vector embeddings
            force: If True, delete existing collection first
        """
        try:
            if force:
                try:
                    self.client.delete_collection(self.collection_name)
                    logger.info(f"Deleted existing collection: {self.collection_name}")
                except Exception:
                    pass  # Collection might not exist
            
            collections = self.client.get_collections()
            collection_exists = any(
                col.name == self.collection_name 
                for col in collections.collections
            )
            
            if not collection_exists:
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=embedding_dim,
                        distance=Distance.COSINE
                    )
                )
                logger.info(f"Created collection: {self.collection_name}")
            else:
                logger.info(f"Collection {self.collection_name} already exists")
        except Exception as e:
            logger.error(f"Error creating collection: {str(e)}")
            raise
    
    def index_document_chunks(self, chunks: List[Dict]) -> int:
        """
        Index multiple document chunks.
        
        Args:
            chunks: List of chunk dictionaries ready for indexing
        
        Returns:
            Number of successfully indexed chunks
        """
        if not chunks:
            return 0
        
        try:
            points = []
            for chunk in chunks:
                # Generate unique point ID
                point_id = str(uuid.uuid4())
                
                # Extract vector and payload
                vector = chunk.pop("chunk_embedding", None)
                if vector is None:
                    logger.warning(f"Chunk missing embedding, skipping: {chunk.get('document_id')}")
                    continue
                
                # Create point with vector and payload (metadata)
                point = PointStruct(
                    id=point_id,
                    vector=vector,
                    payload=chunk
                )
                points.append(point)
            
            # Upsert points in batch
            if points:
                self.client.upsert(
                    collection_name=self.collection_name,
                    points=points
                )
                logger.info(f"Indexed {len(points)} chunks in Qdrant")
                return len(points)
            return 0
        except Exception as e:
            logger.error(f"Error indexing chunks: {str(e)}")
            raise
    
    def delete_document(self, company_id: str, document_id: str) -> int:
        """
        Delete all chunks for a specific document.
        
        Args:
            company_id: UUID of the company
            document_id: UUID of the document
        
        Returns:
            Number of deleted chunks
        """
        try:
            # Build filter
            filter_condition = Filter(
                must=[
                    FieldCondition(key="company_id", match=MatchValue(value=company_id)),
                    FieldCondition(key="document_id", match=MatchValue(value=document_id))
                ]
            )
            
            # Get points matching filter
            scroll_result = self.client.scroll(
                collection_name=self.collection_name,
                scroll_filter=filter_condition,
                limit=10000  # Adjust if needed
            )
            
            point_ids = [point.id for point in scroll_result[0]]
            
            if point_ids:
                self.client.delete(
                    collection_name=self.collection_name,
                    points_selector=point_ids
                )
                logger.info(f"Deleted {len(point_ids)} chunks for document {document_id}")
                return len(point_ids)
            return 0
        except Exception as e:
            logger.error(f"Error deleting document: {str(e)}")
            raise
    
    def search_vectors(self, query_vector: List[float], filter_condition: Optional[Filter] = None,
                      limit: int = 10) -> List[Dict]:
        """
        Execute vector similarity search.
        
        Args:
            query_vector: Query vector embedding
            filter_condition: Optional filter condition
            limit: Maximum number of results
        
        Returns:
            List of search results
        """
        try:
            search_result = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_vector,
                query_filter=filter_condition,
                limit=limit
            )
            
            # Convert Qdrant results to Elasticsearch-like format
            hits = []
            for result in search_result:
                hit = {
                    "_id": str(result.id),
                    "_score": result.score,
                    "_source": result.payload
                }
                hits.append(hit)
            
            return hits
        except Exception as e:
            logger.error(f"Error executing vector search: {str(e)}")
            raise
    
    def scroll_points(self, filter_condition: Optional[Filter] = None,
                     limit: int = 10000) -> List[Dict]:
        """
        Scroll through points with optional filter.
        
        Args:
            filter_condition: Optional filter condition
            limit: Maximum number of points to return
        
        Returns:
            List of points
        """
        try:
            scroll_result = self.client.scroll(
                collection_name=self.collection_name,
                scroll_filter=filter_condition,
                limit=limit
            )
            
            hits = []
            for point in scroll_result[0]:
                hit = {
                    "_id": str(point.id),
                    "_score": 1.0,  # Default score for filtered results
                    "_source": point.payload
                }
                hits.append(hit)
            
            return hits
        except Exception as e:
            logger.error(f"Error scrolling points: {str(e)}")
            raise
    
    def health_check(self) -> bool:
        """
        Check Qdrant service health.
        
        Returns:
            True if healthy, False otherwise
        """
        try:
            collections = self.client.get_collections()
            return True
        except Exception as e:
            logger.error(f"Health check failed: {str(e)}")
            return False


