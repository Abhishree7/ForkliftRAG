# RAG System for Logistics Professionals

A Retrieval-Augmented Generation (RAG) system designed specifically for logistics professionals to query manuals, SOPs, safety guidelines, and shipping protocols using natural language queries.

## Features

- **Hybrid Search**: Combines keyword (BM25) and semantic (dense vector) search for accurate results
- **Natural Language Queries**: Query documents using natural language, not just exact keywords
- **Source Citations**: Every response includes citations with document name, page number, and section title
- **Data Isolation**: Complete privacy and isolation between different logistics companies
- **Low Latency**: Fast response times with Redis caching (< 500ms p95)
- **Multiple Formats**: Supports PDF, DOCX, and TXT documents

## Architecture

The system consists of the following modules:

- **Document Ingestion**: Parses and stores documents (PDF, DOCX, TXT)
- **Indexing**: Indexes document chunks in Qdrant with embeddings
- **Retrieval**: Hybrid search combining keyword and semantic approaches
- **Generation**: Claude 3.5 Sonnet powered response generation
- **Caching**: Redis-based caching for improved latency
- **API**: FastAPI REST API for querying

See [SYSTEM_DESIGN.md](SYSTEM_DESIGN.md) for detailed architecture documentation.

## Prerequisites

- Python 3.9+
- Qdrant (vector database)
- Redis 6.x
- Anthropic API key (for Claude 3.5 Sonnet)
- LlamaParse API key (for PDF parsing)

## Installation

### 1. Clone the Repository

```bash
git clone <repository-url>
cd Unisco.RAG
```

### 2. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 3. Set Up Qdrant

Install and start Qdrant:

```bash
# Using Docker
docker run -d --name qdrant -p 6333:6333 -p 6334:6334 qdrant/qdrant

# Or install locally
# Follow instructions at https://qdrant.tech/documentation/quick-start/
```

Verify Qdrant is running:

```bash
curl http://localhost:6333/health
```

### 4. Set Up Redis

Install and start Redis:

```bash
# Using Docker
docker run -d --name redis -p 6379:6379 redis:7-alpine

# Or install locally
# macOS: brew install redis
# Linux: sudo apt-get install redis-server
```

Verify Redis is running:

```bash
redis-cli ping
# Should return: PONG
```

### 5. Configure Environment Variables

Create a `.env` file (optional, or set environment variables):

```bash
export ANTHROPIC_API_KEY="your-anthropic-api-key-here"
export LLAMA_PARSE_API_KEY="your-llama-parse-api-key-here"  # Required for PDF parsing
export REDIS_PASSWORD=""  # Optional, if Redis has password
```

**Note:** Get your LlamaParse API key from [LlamaIndex Cloud](https://cloud.llamaindex.ai/). LlamaParse API key is **required** for PDF parsing.

### 6. Configure the System

Edit `config/config.yaml` to adjust settings:

- Qdrant host/port
- Redis host/port
- Anthropic model and parameters
- LlamaParse API settings
- Document storage path
- API host/port

## Usage

### 1. Start the API Server

```bash
cd src/api
python main.py
```

Or using uvicorn directly:

```bash
uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload
```

The API will be available at `http://localhost:8000`

### 2. Ingest Documents

Use the provided ingestion script:

```bash
python ingest_document.py <file_path> <company_id> [--document-type <type>]
```

**Example:**

```bash
# Generate a company UUID first
COMPANY_ID=$(python -c "import uuid; print(uuid.uuid4())")

# Ingest a document
python ingest_document.py "AI & Robotics - UNIS Documentation.pdf" $COMPANY_ID --document-type manual
```

**Document Types:**
- `manual` (default)
- `sop` (Standard Operating Procedure)
- `safety_guideline`
- `shipping_protocol`

**Note:** The first time you run this, it will download the BGE-M3 embedding model (~1.2GB), which may take a few minutes.

### 3. Query the System

#### Using cURL

```bash
curl -X POST "http://localhost:8000/api/v1/search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "How do I safely operate a forklift?",
    "company_id": "your-company-uuid-here",
    "query_type": "hybrid",
    "max_results": 5
  }'
```

#### Using Python

```python
import requests

url = "http://localhost:8000/api/v1/search"
payload = {
    "query": "How do I safely operate a forklift?",
    "company_id": "your-company-uuid-here",
    "query_type": "hybrid",
    "max_results": 5
}

response = requests.post(url, json=payload)
result = response.json()

print("Response:", result["response"])
print("\nCitations:")
for citation in result["citations"]:
    print(f"- {citation['document_name']}, Page {citation['page_number']}")
```

#### Example Response

```json
{
  "query": "How do I safely operate a forklift?",
  "response": "To safely operate a forklift, follow these key procedures: 1) Conduct a pre-operation inspection...",
  "citations": [
    {
      "document_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
      "document_name": "Forklift Operations Manual 2024",
      "document_type": "manual",
      "page_number": 45,
      "section_title": "Section 3: Safe Operation Procedures",
      "relevance_score": 0.92,
      "excerpt": "Pre-operation inspection must include: brakes, steering mechanism..."
    }
  ],
  "metadata": {
    "total_documents_searched": 12,
    "search_time_ms": 234.5,
    "cache_hit": false,
    "query_type_used": "hybrid"
  }
}
```

### 4. Submit Feedback

```bash
curl -X POST "http://localhost:8000/api/v1/feedback" \
  -H "Content-Type: application/json" \
  -d '{
    "response_id": "response-uuid-here",
    "helpful": true,
    "comments": "Very helpful response"
  }'
```

## API Endpoints

### POST `/api/v1/search`

Search for information in logistics documents.

**Request Body:**
```json
{
  "query": "string (required, 1-500 chars)",
  "query_type": "hybrid|keyword|semantic (optional, default: hybrid)",
  "company_id": "string (required, UUID)",
  "max_results": "integer (optional, 1-20, default: 5)",
  "filters": {
    "document_types": ["manual", "sop", "safety_guideline", "shipping_protocol"],
    "date_range": {
      "start": "2024-01-01T00:00:00Z",
      "end": "2024-12-31T23:59:59Z"
    }
  }
}
```

**Response:**
- `200 OK`: Search results with citations
- `400 Bad Request`: Invalid input
- `404 Not Found`: No documents match query
- `500 Internal Server Error`: System error

### POST `/api/v1/feedback`

Submit feedback on a response.

**Request Body:**
```json
{
  "response_id": "string (required, UUID)",
  "helpful": "boolean (required)",
  "user_id": "string (optional, UUID)",
  "comments": "string (optional, max 1000 chars)"
}
```

### GET `/health`

Health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:45.123Z"
}
```

## API Documentation

Once the server is running, visit:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Configuration

### config/config.yaml

Main configuration file with settings for:
- Qdrant connection
- Anthropic API settings
- Redis cache settings
- Document storage
- API server settings

### Environment Variables

- `ANTHROPIC_API_KEY`: Required - Anthropic API key for Claude 3.5 Sonnet
- `REDIS_PASSWORD`: Optional - Redis password if authentication enabled

## Project Structure

```
rag_logistics_system/
├── src/
│   ├── document_ingestion/
│   │   ├── parser.py          # Document parsing (PDF, DOCX, TXT)
│   │   └── storage.py         # Document storage handler
│   ├── indexing/
│   │   ├── qdrant_indexer.py
│   │   └── metadata_handler.py
│   ├── retrieval/
│   │   ├── keyword_search.py
│   │   ├── semantic_search.py
│   │   └── hybrid_retriever.py
│   ├── generation/
│   │   ├── llm_handler.py
│   │   └── response_formatter.py
│   ├── caching/
│   │   └── redis_cache.py
│   └── api/
│       ├── main.py            # FastAPI application
│       └── routes.py          # API endpoints
├── config/
│   ├── config.yaml            # Configuration file
│   └── logging.yaml           # Logging configuration
├── documents/                 # Document storage (created automatically)
├── logs/                      # Log files (created automatically)
├── requirements.txt
├── README.md
└── SYSTEM_DESIGN.md
```

## Testing

Run tests (when implemented):

```bash
pytest tests/
```

## Performance Targets

- **Search Response Time**: < 500ms (p95)
- **Cache Hit Response Time**: < 50ms (p95)
- **Document Ingestion**: < 30 seconds per MB
- **API Throughput**: 100 requests/second

## Troubleshooting

### Qdrant Connection Error

```bash
# Check if Qdrant is running
curl http://localhost:9200

# Check Qdrant logs
docker logs elasticsearch
```

### Redis Connection Error

```bash
# Check if Redis is running
redis-cli ping

# Check Redis logs
docker logs redis
```

### Anthropic API Error

- Verify `ANTHROPIC_API_KEY` is set correctly
- Check API quota and billing
- Verify network connectivity

### Document Not Found

- Ensure documents are ingested and indexed
- Check company_id matches the ingested documents
- Verify Qdrant collection contains data

## License

[Add your license here]

## Contributing

[Add contribution guidelines here]

## Support

[Add support contact information here]

