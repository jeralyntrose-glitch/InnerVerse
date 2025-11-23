"""
Shared API Dependencies
FastAPI dependency injection for common resources
"""
from typing import Generator, Optional
from fastapi import Depends, HTTPException, Header, Request, status
from functools import lru_cache

from ..core.config import Settings, get_settings
from ..core.database import get_db_connection, get_db_cursor
from ..core.security import check_rate_limit, get_client_ip
from ..core.logging import setup_logging
from ..services.knowledge_graph_manager import KnowledgeGraphManager

logger = setup_logging(__name__)


# Dependency for getting settings
def get_app_settings() -> Settings:
    """Get application settings"""
    return get_settings()


# Dependency for database connection
def get_db():
    """Get database connection from pool"""
    with get_db_connection() as conn:
        yield conn


# Dependency for knowledge graph manager
@lru_cache()
def get_kg_manager() -> KnowledgeGraphManager:
    """
    Get or create knowledge graph manager singleton
    Cached to ensure single instance across app
    """
    settings = get_settings()
    return KnowledgeGraphManager(settings.KNOWLEDGE_GRAPH_PATH)


# Dependency for Pinecone client
@lru_cache()
def get_pinecone_client():
    """Get Pinecone client (singleton)"""
    from pinecone import Pinecone
    settings = get_settings()
    
    if not settings.PINECONE_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Pinecone not configured"
        )
    
    pc = Pinecone(api_key=settings.PINECONE_API_KEY)
    return pc


# Dependency for Pinecone index
def get_pinecone_index():
    """Get Pinecone index"""
    pc = get_pinecone_client()
    settings = get_settings()
    return pc.Index(settings.PINECONE_INDEX)


# Dependency for OpenAI client
@lru_cache()
def get_openai_client():
    """Get OpenAI client (singleton)"""
    import openai
    settings = get_settings()
    
    if not settings.OPENAI_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="OpenAI not configured"
        )
    
    openai.api_key = settings.OPENAI_API_KEY
    return openai


# Dependency for Anthropic client
@lru_cache()
def get_anthropic_client():
    """Get Anthropic client (singleton)"""
    import anthropic
    settings = get_settings()
    
    if not settings.ANTHROPIC_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Anthropic API not configured"
        )
    
    return anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)


# Dependency for rate limiting (optional)
async def optional_rate_limit(request: Request):
    """Apply rate limiting if enabled"""
    settings = get_settings()
    if settings.RATE_LIMIT_ENABLED:
        await check_rate_limit(request)


# Dependency for API key validation (optional)
async def validate_api_key_header(
    x_api_key: Optional[str] = Header(None),
    settings: Settings = Depends(get_app_settings)
) -> bool:
    """
    Validate API key from header (optional dependency)
    Only use for protected endpoints
    """
    # TODO: Implement proper API key validation against database
    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required"
        )
    return True


# Helper to get request metadata
def get_request_metadata(request: Request) -> dict:
    """Extract useful metadata from request"""
    return {
        "client_ip": get_client_ip(request),
        "user_agent": request.headers.get("user-agent", "unknown"),
        "method": request.method,
        "path": request.url.path,
        "query_params": dict(request.query_params),
    }

