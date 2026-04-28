"""Elasticsearch indexer for document indexing."""
from typing import List, Dict, Optional
from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk
import logging

logger = logging.getLogger(__name__)


class ElasticsearchIndexer:
    """Handler for indexing documents in Elasticsearch."""
    
    def __init__(self, host: str = "localhost", port: int = 9200, 
                 index_name: str = "logistics_documents", timeout: int = 30,
                 max_retries: int = 3):
        """
        Initialize Elasticsearch client.
        
        Args:
            host: Elasticsearch host
            port: Elasticsearch port
            index_name: Name of the index
            timeout: Request timeout in seconds
            max_retries: Maximum number of retries
        """
        self.host = host
        self.port = port
        self.index_name = index_name
        self.timeout = timeout
        
        try:
            self.client = Elasticsearch(
                [f"{host}:{port}"],
                timeout=timeout,
                max_retries=max_retries,
                retry_on_timeout=True
            )
            # Test connection
            if not self.client.ping():
                raise ConnectionError("Failed to connect to Elasticsearch")
            logger.info(f"Connected to Elasticsearch at {host}:{port}")
        except Exception as e:
            logger.error(f"Error connecting to Elasticsearch: {str(e)}")
            raise
    
    def create_index(self, mapping: Dict, force: bool = False):
        """
        Create Elasticsearch index with specified mapping.
        
        Args:
            mapping: Index mapping dictionary
            force: If True, delete existing index first
        """
        try:
            if force and self.client.indices.exists(index=self.index_name):
                self.client.indices.delete(index=self.index_name)
                logger.info(f"Deleted existing index: {self.index_name}")
            
            if not self.client.indices.exists(index=self.index_name):
                self.client.indices.create(index=self.index_name, body=mapping)
                logger.info(f"Created index: {self.index_name}")
            else:
                logger.info(f"Index {self.index_name} already exists")
        except Exception as e:
            logger.error(f"Error creating index: {str(e)}")
            raise
    
    def index_document_chunks(self, chunks: List[Dict]) -> int:
        """
        Index multiple document chunks using bulk API.
        
        Args:
            chunks: List of chunk dictionaries ready for indexing
        
        Returns:
            Number of successfully indexed chunks
        """
        if not chunks:
            return 0
        
        def generate_actions():
            for chunk in chunks:
                yield {
                    "_index": self.index_name,
                    "_source": chunk
                }
        
        try:
            success_count = 0
            failed_count = 0
            
            for ok, response in bulk(self.client, generate_actions(), 
                                     raise_on_error=False):
                if ok:
                    success_count += 1
                else:
                    failed_count += 1
                    logger.warning(f"Failed to index chunk: {response}")
            
            logger.info(f"Indexed {success_count} chunks, {failed_count} failed")
            return success_count
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
            query = {
                "query": {
                    "bool": {
                        "must": [
                            {"term": {"company_id": company_id}},
                            {"term": {"document_id": document_id}}
                        ]
                    }
                }
            }
            
            response = self.client.delete_by_query(
                index=self.index_name,
                body=query
            )
            
            deleted_count = response.get("deleted", 0)
            logger.info(f"Deleted {deleted_count} chunks for document {document_id}")
            return deleted_count
        except Exception as e:
            logger.error(f"Error deleting document: {str(e)}")
            raise
    
    def search(self, query: Dict, size: int = 10) -> List[Dict]:
        """
        Execute search query.
        
        Args:
            query: Elasticsearch query dictionary
            size: Maximum number of results
        
        Returns:
            List of search hits
        """
        try:
            response = self.client.search(
                index=self.index_name,
                body=query,
                size=size
            )
            return response.get("hits", {}).get("hits", [])
        except Exception as e:
            logger.error(f"Error executing search: {str(e)}")
            raise
    
    def health_check(self) -> bool:
        """
        Check Elasticsearch cluster health.
        
        Returns:
            True if healthy, False otherwise
        """
        try:
            health = self.client.cluster.health()
            status = health.get("status")
            return status in ["green", "yellow"]
        except Exception as e:
            logger.error(f"Health check failed: {str(e)}")
            return False

