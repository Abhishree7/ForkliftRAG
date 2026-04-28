"""API routes for RAG system."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict
from datetime import datetime
import uuid
import time
import logging

from src.retrieval.hybrid_retriever import HybridRetriever
from src.generation.llm_handler import LLMHandler
from src.generation.response_formatter import ResponseFormatter
from src.caching.redis_cache import RedisCache

logger = logging.getLogger(__name__)

router = APIRouter()

# Request/Response Models
class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=500, description="Search query")
    query_type: Optional[str] = Field("hybrid", description="Query type: natural_language, keyword, or hybrid")
    company_id: str = Field(..., description="Company UUID")
    max_results: Optional[int] = Field(5, ge=1, le=20, description="Maximum number of results")
    filters: Optional[Dict] = Field(None, description="Optional filters")
    
    @validator('query')
    def validate_query(cls, v):
        v = v.strip()
        if not v:
            raise ValueError('query cannot be empty')
        return v
    
    @validator('query_type')
    def validate_query_type(cls, v):
        if v not in ['natural_language', 'keyword', 'hybrid']:
            raise ValueError('query_type must be one of: natural_language, keyword, hybrid')
        return v
    
    @validator('company_id')
    def validate_company_id(cls, v):
        try:
            uuid.UUID(v)
        except ValueError:
            raise ValueError('company_id must be a valid UUID')
        return v


class FeedbackRequest(BaseModel):
    response_id: str = Field(..., description="Response UUID")
    helpful: bool = Field(..., description="Whether the response was helpful")
    user_id: Optional[str] = Field(None, description="User UUID")
    comments: Optional[str] = Field(None, max_length=1000, description="Optional comments")
    
    @validator('response_id')
    def validate_response_id(cls, v):
        try:
            uuid.UUID(v)
        except ValueError:
            raise ValueError('response_id must be a valid UUID')
        return v
    
    @validator('user_id')
    def validate_user_id(cls, v):
        if v is not None:
            try:
                uuid.UUID(v)
            except ValueError:
                raise ValueError('user_id must be a valid UUID')
        return v


# Store service instances (initialized in main.py)
_services = {}


@router.post("/api/v1/search", response_model=Dict)
async def search(request: SearchRequest):
    """
    Search endpoint for querying logistics documents.
    """
    start_time = time.time()
    
    # Get services from global store
    retriever = _services.get('retriever')
    llm_handler = _services.get('llm_handler')
    cache = _services.get('cache')
    
    if not retriever or not llm_handler or not cache:
        raise HTTPException(
            status_code=503,
            detail={
                "error": "Service temporarily unavailable: Services not initialized",
                "code": 503,
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
        )
    
    try:
        # Check cache first
        cached_result = cache.get(request.company_id, request.query, request.filters)
        if cached_result:
            cached_result["metadata"]["cache_hit"] = True
            return cached_result

        # Let Groq classify the query before doing any retrieval
        query_class = llm_handler.classify_query(request.query)

        if query_class == "GREETING":
            response_text = llm_handler.generate_conversational_response(request.query)
            search_time_ms = (time.time() - start_time) * 1000
            formatted_response = ResponseFormatter.format_search_response(
                query=request.query,
                response=response_text,
                citations=[],
                metadata={"total_documents_searched": 0, "search_time_ms": search_time_ms,
                          "cache_hit": False, "query_type_used": "conversational"}
            )
            cache.set(request.company_id, request.query, formatted_response, request.filters)
            return formatted_response

        if query_class == "OUT_OF_SCOPE":
            from src.generation.prompts import OUT_OF_SCOPE_MESSAGE
            search_time_ms = (time.time() - start_time) * 1000
            formatted_response = ResponseFormatter.format_search_response(
                query=request.query,
                response=OUT_OF_SCOPE_MESSAGE,
                citations=[],
                metadata={"total_documents_searched": 0, "search_time_ms": search_time_ms,
                          "cache_hit": False, "query_type_used": "out_of_scope"}
            )
            cache.set(request.company_id, request.query, formatted_response, request.filters)
            return formatted_response

        # Execute search
        citations = retriever.search(
            query=request.query,
            company_id=request.company_id,
            query_type=request.query_type,
            filters=request.filters,
            max_results=request.max_results
        )

        if not citations:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "No documents found matching the query",
                    "code": 404,
                    "details": {
                        "query": request.query,
                        "suggestion": "Try rephrasing your query or removing filters"
                    },
                    "timestamp": datetime.utcnow().isoformat() + "Z"
                }
            )

        # Generate response using LLM
        response_text = llm_handler.generate_response(request.query, citations)

        # Calculate search time
        search_time_ms = (time.time() - start_time) * 1000

        # Format response
        formatted_response = ResponseFormatter.format_search_response(
            query=request.query,
            response=response_text,
            citations=citations,
            metadata={
                "total_documents_searched": len(citations),
                "search_time_ms": search_time_ms,
                "cache_hit": False,
                "query_type_used": request.query_type
            }
        )

        # Cache result
        cache.set(request.company_id, request.query, formatted_response, request.filters)

        return formatted_response
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in search endpoint: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": f"Internal server error: {str(e)}",
                "code": 500,
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
        )


@router.post("/api/v1/feedback", response_model=Dict)
async def feedback(request: FeedbackRequest):
    """
    Feedback endpoint for user feedback on responses.
    """
    try:
        # In a production system, this would store feedback in a database
        # For now, we just validate and return success
        response = ResponseFormatter.format_feedback_response(request.response_id)
        logger.info(f"Feedback received for response {request.response_id}: helpful={request.helpful}")
        return response
    
    except Exception as e:
        logger.error(f"Error in feedback endpoint: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": f"Internal server error: {str(e)}",
                "code": 500,
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
        )


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat() + "Z"}

