import pytest
from unittest.mock import Mock, MagicMock
from src.retrieval.hybrid_retriever import HybridRetriever

@pytest.fixture
def mock_keyword_search():
    return Mock()

@pytest.fixture
def mock_semantic_search():
    return Mock()

@pytest.fixture
def hybrid_retriever(mock_keyword_search, mock_semantic_search):
    return HybridRetriever(mock_keyword_search, mock_semantic_search)

def test_search_hybrid_strategy(hybrid_retriever, mock_keyword_search, mock_semantic_search):
    # Setup mocks
    mock_keyword_search.search.return_value = [
        {"_source": {"document_id": "doc1", "page_number": 1}, "score": 10.0}
    ]
    mock_semantic_search.search.return_value = [
        {"_source": {"document_id": "doc2", "page_number": 1}, "score": 0.9}
    ]
    
    # Execute
    results = hybrid_retriever.search("test query", "company_1", query_type="hybrid")
    
    # Verify
    assert len(results) == 2
    mock_keyword_search.search.assert_called_once()
    mock_semantic_search.search.assert_called_once()

def test_search_keyword_only(hybrid_retriever, mock_keyword_search, mock_semantic_search):
    mock_keyword_search.search.return_value = []
    
    hybrid_retriever.search("test", "company_1", query_type="keyword")
    
    mock_keyword_search.search.assert_called_once()
    mock_semantic_search.search.assert_not_called()

def test_search_semantic_only(hybrid_retriever, mock_keyword_search, mock_semantic_search):
    mock_semantic_search.search.return_value = []
    
    hybrid_retriever.search("test", "company_1", query_type="semantic")
    
    mock_semantic_search.search.assert_called_once()
    mock_keyword_search.search.assert_not_called()

def test_deduplication(hybrid_retriever, mock_keyword_search, mock_semantic_search):
    # Both return same doc
    hit = {"_source": {"document_id": "doc1", "page_number": 1}, "score": 1.0}
    mock_keyword_search.search.return_value = [hit]
    mock_semantic_search.search.return_value = [hit]
    
    results = hybrid_retriever.search("test", "company_1")
    
    assert len(results) == 1
    assert results[0]["document_id"] == "doc1"
