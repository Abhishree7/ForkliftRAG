"""Response formatter for API responses."""
from typing import List, Dict, Optional
from datetime import datetime
import uuid
import logging

logger = logging.getLogger(__name__)


class ResponseFormatter:
    """Formatter for API responses."""
    
    @staticmethod
    def format_search_response(query: str, response: str, citations: List[Dict],
                              metadata: Dict) -> Dict:
        """
        Format search response according to API specification.
        
        Args:
            query: Original query
            response: Generated response text
            citations: List of citation dictionaries
            metadata: Metadata dictionary (total_documents_searched, search_time_ms, etc.)
        
        Returns:
            Formatted response dictionary
        """
        # Ensure response doesn't exceed 2000 characters
        if len(response) > 2000:
            response = response[:1997] + "..."
        
        # Ensure citations have all required fields
        formatted_citations = []
        for citation in citations:
            formatted_citation = {
                "document_id": citation.get("document_id", ""),
                "document_name": citation.get("document_name", "Unknown Document"),
                "document_type": citation.get("document_type", "manual"),
                "page_number": citation.get("page_number", 1),
                "section_title": citation.get("section_title", "Section"),
                "relevance_score": round(citation.get("relevance_score", 0.0), 2),
                "excerpt": citation.get("excerpt", "")[:500]  # Max 500 chars
            }
            formatted_citations.append(formatted_citation)
        
        return {
            "query": query,
            "response": response,
            "citations": formatted_citations,
            "metadata": {
                "total_documents_searched": metadata.get("total_documents_searched", 0),
                "search_time_ms": round(metadata.get("search_time_ms", 0.0), 2),
                "cache_hit": metadata.get("cache_hit", False),
                "query_type_used": metadata.get("query_type_used", "hybrid")
            }
        }
    
    @staticmethod
    def format_error_response(error: str, code: int, details: Optional[Dict] = None) -> Dict:
        """
        Format error response.
        
        Args:
            error: Error message
            code: HTTP status code
            details: Optional error details
        
        Returns:
            Formatted error response dictionary
        """
        response = {
            "error": error,
            "code": code,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
        if details:
            response["details"] = details
        
        return response
    
    @staticmethod
    def format_feedback_response(response_id: str) -> Dict:
        """
        Format feedback response.
        
        Args:
            response_id: UUID of the response
        
        Returns:
            Formatted feedback response dictionary
        """
        return {
            "message": "Feedback recorded successfully",
            "response_id": response_id,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }

