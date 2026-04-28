import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch
from src.api.routes import router, _services

# Create a FastAPI app for testing
app = FastAPI()
app.include_router(router)
client = TestClient(app)

@pytest.fixture
def mock_services():
    # Create mocks
    mock_retriever = Mock()
    mock_llm = Mock()
    mock_cache = Mock()
    
    # Setup default behaviors
    mock_retriever.search.return_value = [
        {
            "document_id": "doc1",
            "page_number": 1,
            "document_name": "Test Doc",
            "section_title": "Test Section",
            "excerpt": "Test content"
        }
    ]
    mock_llm.generate_response.return_value = "Test response"
    mock_cache.get.return_value = None
    
    # Patch the global _services dict
    with patch.dict(_services, {
        'retriever': mock_retriever,
        'llm_handler': mock_llm,
        'cache': mock_cache
    }, clear=True):
        yield {
            'retriever': mock_retriever,
            'llm_handler': mock_llm,
            'cache': mock_cache
        }

def test_search_endpoint_success(mock_services):
    payload = {
        "query": "test query",
        "company_id": "123e4567-e89b-12d3-a456-426614174000",
        "query_type": "hybrid"
    }
    
    response = client.post("/api/v1/search", json=payload)
    
    assert response.status_code == 200
    data = response.json()
    assert data["response"] == "Test response"
    assert len(data["citations"]) == 1
    assert data["metadata"]["cache_hit"] is False

def test_search_endpoint_cache_hit(mock_services):
    # Setup cache hit
    mock_services['cache'].get.return_value = {
        "response": "Cached response",
        "citations": [],
        "metadata": {"cache_hit": True}
    }
    
    payload = {
        "query": "test query",
        "company_id": "123e4567-e89b-12d3-a456-426614174000"
    }
    
    response = client.post("/api/v1/search", json=payload)
    
    assert response.status_code == 200
    assert response.json()["response"] == "Cached response"
    mock_services['retriever'].search.assert_not_called()

def test_search_endpoint_no_results(mock_services):
    mock_services['retriever'].search.return_value = []
    
    payload = {
        "query": "impossible query",
        "company_id": "123e4567-e89b-12d3-a456-426614174000"
    }
    
    response = client.post("/api/v1/search", json=payload)
    
    assert response.status_code == 404
    assert "No documents found" in response.json()["detail"]["error"]

def test_search_endpoint_validation_error():
    # Invalid UUID
    payload = {
        "query": "test",
        "company_id": "invalid-uuid"
    }
    
    response = client.post("/api/v1/search", json=payload)
    
    assert response.status_code == 422

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
