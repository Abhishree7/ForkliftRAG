"""Hybrid retriever combining keyword and semantic search."""
from typing import List, Dict, Optional
from src.retrieval.keyword_search import KeywordSearch
from src.retrieval.semantic_search import SemanticSearch
from src.indexing.metadata_handler import MetadataHandler
import logging

logger = logging.getLogger(__name__)


class HybridRetriever:
    """Hybrid retriever using reciprocal rank fusion (RRF)."""
    
    def __init__(self, keyword_search: KeywordSearch, semantic_search: SemanticSearch):
        """
        Initialize hybrid retriever.
        
        Args:
            keyword_search: KeywordSearch instance
            semantic_search: SemanticSearch instance
        """
        self.keyword_search = keyword_search
        self.semantic_search = semantic_search
        self.metadata_handler = MetadataHandler()
    
    def search(self, query: str, company_id: str, query_type: str = "hybrid",
               filters: Optional[Dict] = None, max_results: int = 5) -> List[Dict]:
        """
        Execute hybrid search combining keyword and semantic results.
        
        Args:
            query: Search query string
            company_id: UUID of the company
            query_type: Type of search ('keyword', 'semantic', or 'hybrid')
            filters: Optional filters
            max_results: Maximum number of results to return
        
        Returns:
            List of citations sorted by relevance
        """
        if query_type == "keyword":
            hits = self.keyword_search.search(query, company_id, filters, size=max_results * 2)
        elif query_type == "semantic":
            hits = self.semantic_search.search(query, company_id, filters, size=max_results * 2)
        else:  # hybrid
            # Execute both searches in parallel (simulated here)
            keyword_hits = self.keyword_search.search(query, company_id, filters, size=10)
            semantic_hits = self.semantic_search.search(query, company_id, filters, size=10)
            
            # Combine and re-rank using RRF
            hits = self._reciprocal_rank_fusion(keyword_hits, semantic_hits, k=60)
        
        # Convert hits to citations
        citations = []
        seen = set()
        
        for hit in hits[:max_results]:
            citation = self.metadata_handler.extract_citation_from_hit(hit)
            
            # Deduplicate by document_id + page_number
            key = (citation["document_id"], citation["page_number"])
            if key not in seen:
                citations.append(citation)
                seen.add(key)
        
        logger.info(f"Hybrid search returned {len(citations)} unique citations")
        return citations
    
    def _reciprocal_rank_fusion(self, keyword_hits: List[Dict], 
                                semantic_hits: List[Dict], k: int = 60) -> List[Dict]:
        """
        Combine search results using Reciprocal Rank Fusion (RRF).
        
        Args:
            keyword_hits: Results from keyword search
            semantic_hits: Results from semantic search
            k: RRF constant (typically 60)
        
        Returns:
            Combined and re-ranked hits
        """
        # Create score dictionary
        scores = {}
        
        # Add keyword search scores
        for rank, hit in enumerate(keyword_hits, start=1):
            # Use a combination of document_id and page_number as unique key
            source = hit.get("_source", {})
            doc_id = f"{source.get('document_id', '')}_{source.get('page_number', 0)}"
            if doc_id not in scores:
                scores[doc_id] = {"score": 0.0, "hit": hit}
            scores[doc_id]["score"] += 1.0 / (k + rank)
        
        # Add semantic search scores
        for rank, hit in enumerate(semantic_hits, start=1):
            # Use a combination of document_id and page_number as unique key
            source = hit.get("_source", {})
            doc_id = f"{source.get('document_id', '')}_{source.get('page_number', 0)}"
            if doc_id not in scores:
                scores[doc_id] = {"score": 0.0, "hit": hit}
            scores[doc_id]["score"] += 1.0 / (k + rank)
        
        # Sort by combined score
        sorted_hits = sorted(scores.values(), key=lambda x: x["score"], reverse=True)
        
        # Update _score in hits for consistency
        for item in sorted_hits:
            item["hit"]["_score"] = item["score"]
        
        return [item["hit"] for item in sorted_hits]

