"""Redis cache for query results."""
from typing import Optional, Dict, Any
import redis
import json
import hashlib
import logging

logger = logging.getLogger(__name__)


class RedisCache:
    """Redis cache handler for query results."""
    
    def __init__(self, host: str = "localhost", port: int = 6379, db: int = 0,
                 ttl: int = 3600, password: Optional[str] = None):
        """
        Initialize Redis cache.
        
        Args:
            host: Redis host
            port: Redis port
            db: Redis database number
            ttl: Time-to-live in seconds (default: 1 hour)
            password: Optional Redis password
        """
        self.host = host
        self.port = port
        self.db = db
        self.ttl = ttl
        
        try:
            self.client = redis.Redis(
                host=host,
                port=port,
                db=db,
                password=password,
                decode_responses=True
            )
            # Test connection
            self.client.ping()
            logger.info(f"Connected to Redis at {host}:{port}")
        except Exception as e:
            logger.error(f"Error connecting to Redis: {str(e)}")
            raise
    
    def _generate_cache_key(self, company_id: str, query: str, 
                           filters: Optional[Dict] = None) -> str:
        """
        Generate cache key from query parameters.
        
        Args:
            company_id: UUID of the company
            query: Search query
            filters: Optional filters
        
        Returns:
            Cache key string
        """
        # Create hash of query and filters
        key_data = {
            "company_id": company_id,
            "query": query.lower().strip(),
            "filters": filters or {}
        }
        key_string = json.dumps(key_data, sort_keys=True)
        query_hash = hashlib.md5(key_string.encode()).hexdigest()
        
        return f"search:{company_id}:{query_hash}"
    
    def get(self, company_id: str, query: str, 
            filters: Optional[Dict] = None) -> Optional[Dict]:
        """
        Get cached result.
        
        Args:
            company_id: UUID of the company
            query: Search query
            filters: Optional filters
        
        Returns:
            Cached result dictionary or None if not found
        """
        try:
            cache_key = self._generate_cache_key(company_id, query, filters)
            cached_value = self.client.get(cache_key)
            
            if cached_value:
                result = json.loads(cached_value)
                logger.info(f"Cache hit for query: {query[:50]}")
                return result
            else:
                logger.debug(f"Cache miss for query: {query[:50]}")
                return None
        except Exception as e:
            logger.error(f"Error getting from cache: {str(e)}")
            return None
    
    def set(self, company_id: str, query: str, result: Dict,
            filters: Optional[Dict] = None):
        """
        Cache a result.
        
        Args:
            company_id: UUID of the company
            query: Search query
            result: Result dictionary to cache
            filters: Optional filters
        """
        try:
            cache_key = self._generate_cache_key(company_id, query, filters)
            cached_value = json.dumps(result)
            
            self.client.setex(cache_key, self.ttl, cached_value)
            logger.info(f"Cached result for query: {query[:50]}")
        except Exception as e:
            logger.error(f"Error setting cache: {str(e)}")
            # Don't raise - caching failures shouldn't break the system
    
    def delete(self, company_id: str, query: str, 
               filters: Optional[Dict] = None) -> bool:
        """
        Delete cached result.
        
        Args:
            company_id: UUID of the company
            query: Search query
            filters: Optional filters
        
        Returns:
            True if deleted, False if not found
        """
        try:
            cache_key = self._generate_cache_key(company_id, query, filters)
            deleted = self.client.delete(cache_key)
            if deleted:
                logger.info(f"Deleted cache for query: {query[:50]}")
            return deleted > 0
        except Exception as e:
            logger.error(f"Error deleting from cache: {str(e)}")
            return False
    
    def clear_company_cache(self, company_id: str) -> int:
        """
        Clear all cache entries for a company.
        
        Args:
            company_id: UUID of the company
        
        Returns:
            Number of keys deleted
        """
        try:
            pattern = f"search:{company_id}:*"
            keys = self.client.keys(pattern)
            
            if keys:
                deleted = self.client.delete(*keys)
                logger.info(f"Cleared {deleted} cache entries for company {company_id}")
                return deleted
            return 0
        except Exception as e:
            logger.error(f"Error clearing company cache: {str(e)}")
            return 0
    
    def health_check(self) -> bool:
        """
        Check Redis connection health.
        
        Returns:
            True if healthy, False otherwise
        """
        try:
            return self.client.ping()
        except Exception as e:
            logger.error(f"Redis health check failed: {str(e)}")
            return False

