import pytest
from unittest.mock import Mock, patch
from src.generation.llm_handler import LLMHandler

@pytest.fixture
def mock_anthropic():
    with patch('src.generation.llm_handler.Anthropic') as mock:
        yield mock

def test_initialization_no_api_key(mock_anthropic):
    with patch.dict('os.environ', {}, clear=True):
        with pytest.raises(ValueError, match="Anthropic API key not provided"):
            LLMHandler(api_key=None)

def test_generate_response(mock_anthropic):
    # Setup
    handler = LLMHandler(api_key="test-key")
    mock_client = mock_anthropic.return_value
    
    mock_message = Mock()
    mock_message.content = [Mock(text="Generated answer")]
    mock_client.messages.create.return_value = mock_message
    
    citations = [
        {
            "document_name": "Doc A",
            "page_number": 1,
            "section_title": "Intro",
            "excerpt": "This is context."
        }
    ]
    
    # Execute
    response = handler.generate_response("question?", citations)
    
    # Verify
    assert response == "Generated answer"
    mock_client.messages.create.assert_called_once()
    call_args = mock_client.messages.create.call_args[1]
    assert "This is context" in call_args["messages"][0]["content"]

def test_generate_response_error(mock_anthropic):
    handler = LLMHandler(api_key="test-key")
    mock_client = mock_anthropic.return_value
    mock_client.messages.create.side_effect = Exception("API Error")
    
    with pytest.raises(Exception, match="API Error"):
        handler.generate_response("q", [])
