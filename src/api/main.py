"""FastAPI application main file."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import yaml
import os
import logging
from logging.config import dictConfig

from src.api.routes import router, _services
from src.indexing.qdrant_indexer import QdrantIndexer
from src.indexing.metadata_handler import MetadataHandler
from src.retrieval.keyword_search import KeywordSearch
from src.retrieval.semantic_search import SemanticSearch
from src.retrieval.hybrid_retriever import HybridRetriever
from src.generation.llm_handler import LLMHandler
from src.caching.redis_cache import RedisCache

# Load configuration
def load_config():
    """Load configuration from config.yaml with environment variable substitution."""
    import re
    config_path = os.path.join(os.path.dirname(__file__), "../../config/config.yaml")
    with open(config_path, 'r') as f:
        content = f.read()
        # Replace ${VAR} with environment variable values
        content = re.sub(r'\$\{(\w+)\}', lambda m: os.getenv(m.group(1), ''), content)
        return yaml.safe_load(content)

# Load logging configuration
def setup_logging():
    """Setup logging from logging.yaml."""
    logging_path = os.path.join(os.path.dirname(__file__), "../../config/logging.yaml")
    if os.path.exists(logging_path):
        with open(logging_path, 'r') as f:
            log_config = yaml.safe_load(f)
            dictConfig(log_config)
    else:
        # Default logging configuration
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )

# Initialize services
def initialize_services(config: dict):
    """Initialize all service dependencies."""
    # Qdrant
    qdrant_config = config.get("qdrant", {})
    indexer = QdrantIndexer(
        host=qdrant_config.get("host", "localhost"),
        port=qdrant_config.get("port", 6333),
        collection_name=qdrant_config.get("collection_name", "logistics_documents"),
        timeout=qdrant_config.get("timeout", 30)
    )
    
    # Semantic search (initialize first to get embedding dimension)
    semantic_config = config.get("semantic_search", {})
    semantic_search = SemanticSearch(
        indexer=indexer,
        model_name=semantic_config.get("model_name", "BAAI/bge-m3"),
        device=semantic_config.get("device", "cpu")
    )
    
    # Create collection if it doesn't exist (use embedding dimension from model)
    embedding_dim = semantic_search.embedding_dim  # Get dimension from loaded model
    indexer.create_collection(embedding_dim=embedding_dim)
    
    # Keyword search
    keyword_search = KeywordSearch(indexer)
    
    # Hybrid retriever
    hybrid_retriever = HybridRetriever(keyword_search, semantic_search)
    
    # LLM handler
    groq_config = config.get("groq", {})
    api_key = groq_config.get("api_key", os.getenv("GROQ_API_KEY"))
    llm_handler = LLMHandler(
        api_key=api_key,
        model=groq_config.get("model", "llama-3.3-70b-versatile"),
        temperature=groq_config.get("temperature", 0.3),
        max_tokens=groq_config.get("max_tokens", 500),
        timeout=groq_config.get("timeout", 60)
    )
    
    # Redis cache
    redis_config = config.get("redis", {})
    cache = RedisCache(
        host=redis_config.get("host", "localhost"),
        port=redis_config.get("port", 6379),
        db=redis_config.get("db", 0),
        ttl=redis_config.get("ttl", 3600),
        password=redis_config.get("password", os.getenv("REDIS_PASSWORD"))
    )
    
    # Store services
    _services['retriever'] = hybrid_retriever
    _services['llm_handler'] = llm_handler
    _services['cache'] = cache
    _services['indexer'] = indexer
    
    return _services

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

# Load configuration
config = load_config()

# Initialize FastAPI app
app = FastAPI(
    title="RAG System for Logistics Professionals",
    description="Retrieval-Augmented Generation system for querying logistics documents",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify allowed origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(router)

# Initialize services on startup
@app.on_event("startup")
async def startup_event():
    """Initialize services on application startup."""
    try:
        initialize_services(config)
        logger.info("Services initialized successfully")
    except Exception as e:
        logger.error(f"Error initializing services: {str(e)}")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on application shutdown."""
    logger.info("Shutting down application")

if __name__ == "__main__":
    import uvicorn
    api_config = config.get("api", {})
    uvicorn.run(
        "main:app",
        host=api_config.get("host", "0.0.0.0"),
        port=api_config.get("port", 8000),
        reload=True
    )

