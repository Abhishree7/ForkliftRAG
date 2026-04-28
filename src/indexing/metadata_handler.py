"""Metadata handler for document metadata management."""
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


class MetadataHandler:
    """Handler for managing document metadata."""
    
    @staticmethod
    def prepare_chunk_for_indexing(chunk: Dict, embedding: List[float]) -> Dict:
        """
        Prepare a chunk for indexing in Qdrant.
        
        Args:
            chunk: Chunk dictionary with metadata
            embedding: Dense vector embedding
        
        Returns:
            Document ready for indexing (with embedding separate for Qdrant)
        """
        # Qdrant stores vector separately from payload
        indexed_chunk = {
            "document_id": chunk.get("document_id"),
            "company_id": chunk.get("company_id"),
            "document_name": chunk.get("document_name"),
            "document_type": chunk.get("document_type"),
            "page_number": chunk.get("page_number"),
            "section_title": chunk.get("section_title", "Section"),
            "chunk_text": chunk.get("chunk_text"),
            "upload_timestamp": chunk.get("upload_timestamp"),
            "chunk_embedding": embedding  # Keep for Qdrant indexer to extract
        }
        return indexed_chunk
    
    @staticmethod
    def extract_citation_from_hit(hit: Dict) -> Dict:
        """
        Extract citation information from Qdrant search hit.
        
        Args:
            hit: Qdrant search hit (in Elasticsearch-like format)
        
        Returns:
            Citation dictionary
        """
        source = hit.get("_source", {})
        score = hit.get("_score", 0.0)
        
        # Normalize score to 0.0-1.0 range (Qdrant cosine similarity is 0-1)
        normalized_score = min(1.0, max(0.0, score))
        
        excerpt = source.get("chunk_text", "")
        if len(excerpt) > 500:
            excerpt = excerpt[:500] + "..."
        
        return {
            "document_id": source.get("document_id"),
            "document_name": source.get("document_name"),
            "document_type": source.get("document_type"),
            "page_number": source.get("page_number"),
            "section_title": source.get("section_title", "Section"),
            "relevance_score": normalized_score,
            "excerpt": excerpt
        }
    
    @staticmethod
    def build_qdrant_filter(company_id: str, filters: Optional[Dict] = None):
        """
        Build Qdrant filter condition.
        
        Args:
            company_id: UUID of the company
            filters: Optional filters (document_types, date_range)
        
        Returns:
            Qdrant Filter object
        """
        from qdrant_client.models import Filter, FieldCondition, MatchValue, Range
        
        must_conditions = [
            FieldCondition(key="company_id", match=MatchValue(value=company_id))
        ]
        
        if filters:
            if filters.get("document_types"):
                # Qdrant supports matching any value in a list
                from qdrant_client.models import MatchAny
                must_conditions.append(
                    FieldCondition(
                        key="document_type",
                        match=MatchAny(any=filters["document_types"])
                    )
                )
            
            if filters.get("date_range"):
                date_range = filters["date_range"]
                range_params = {}
                if date_range.get("start"):
                    range_params["gte"] = date_range["start"]
                if date_range.get("end"):
                    range_params["lte"] = date_range["end"]
                
                if range_params:
                    must_conditions.append(
                        FieldCondition(
                            key="upload_timestamp",
                            range=Range(**range_params)
                        )
                    )
        
        return Filter(must=must_conditions) if must_conditions else None
