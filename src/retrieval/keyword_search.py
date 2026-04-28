"""Keyword search using text matching with Qdrant."""
from typing import List, Dict, Optional
from src.indexing.qdrant_indexer import QdrantIndexer
from src.indexing.metadata_handler import MetadataHandler
import re
import logging

logger = logging.getLogger(__name__)


class KeywordSearch:
    """Keyword-based search using text matching."""
    
    def __init__(self, indexer: QdrantIndexer):
        """
        Initialize keyword search.
        
        Args:
            indexer: QdrantIndexer instance
        """
        self.indexer = indexer
        self.metadata_handler = MetadataHandler()
    
    def _calculate_keyword_score(self, text: str, query: str) -> float:
        """
        Calculate keyword match score (simple TF-based scoring).
        
        Args:
            text: Text to search in
            query: Search query
        
        Returns:
            Score between 0.0 and 1.0
        """
        text_lower = text.lower()
        query_terms = re.findall(r'\b\w+\b', query.lower())
        
        if not query_terms:
            return 0.0
        
        # Calculate term frequency score
        total_matches = 0
        for term in query_terms:
            # Count occurrences
            matches = len(re.findall(rf'\b{re.escape(term)}\b', text_lower))
            total_matches += matches
        
        # Normalize score (max score = number of unique terms * 2)
        max_score = len(query_terms) * 2
        score = min(1.0, total_matches / max_score) if max_score > 0 else 0.0
        
        return score
    
    def search(self, query: str, company_id: str, filters: Optional[Dict] = None, 
               size: int = 10) -> List[Dict]:
        """
        Execute keyword search using text matching.
        
        Args:
            query: Search query string
            company_id: UUID of the company (for data isolation)
            filters: Optional filters (document_types, equipment_types, date_range)
            size: Maximum number of results
        
        Returns:
            List of search hits
        """
        try:
            # Build filter
            filter_condition = self.metadata_handler.build_qdrant_filter(company_id, filters)
            
            # Get all points matching filter (with reasonable limit)
            all_hits = self.indexer.scroll_points(filter_condition, limit=1000)
            
            # Score each hit based on keyword matching
            scored_hits = []
            for hit in all_hits:
                source = hit.get("_source", {})
                chunk_text = source.get("chunk_text", "")
                section_title = source.get("section_title", "")
                document_name = source.get("document_name", "")
                
                # Calculate scores for different fields
                text_score = self._calculate_keyword_score(chunk_text, query)
                title_score = self._calculate_keyword_score(section_title, query) * 1.5  # Boost title matches
                name_score = self._calculate_keyword_score(document_name, query) * 1.2  # Boost name matches
                
                # Combined score
                combined_score = (text_score * 3 + title_score * 2 + name_score) / 6
                
                if combined_score > 0:
                    hit["_score"] = combined_score
                    scored_hits.append(hit)
            
            # Sort by score and return top N
            scored_hits.sort(key=lambda x: x.get("_score", 0.0), reverse=True)
            top_hits = scored_hits[:size]
            
            logger.info(f"Keyword search returned {len(top_hits)} results for query: {query[:50]}")
            return top_hits
        except Exception as e:
            logger.error(f"Error in keyword search: {str(e)}")
            raise
