"""
Application Configuration
Centralized configuration management using pydantic-settings
"""
import os
from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings with validation and type safety"""
    
    # Application
    APP_NAME: str = "InnerVerse"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"
    
    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 5000
    
    # Security
    CSRF_SECRET_KEY: Optional[str] = None
    COOKIE_SECURE: bool = False
    COOKIE_SAMESITE: str = "lax"
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:5000"]
    
    # API Keys
    OPENAI_API_KEY: str
    ANTHROPIC_API_KEY: str
    PINECONE_API_KEY: str
    PINECONE_ENVIRONMENT: Optional[str] = None
    PINECONE_INDEX: str = "mbti-knowledge-v2"
    BRAVE_API_KEY: Optional[str] = None
    
    # Database
    DATABASE_URL: str
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_POOL_TIMEOUT: int = 30
    DB_POOL_RECYCLE: int = 3600
    
    # Proxy (for YouTube downloads)
    DECODO_PROXY_HOST: Optional[str] = None
    DECODO_PROXY_PORT: Optional[str] = None
    DECODO_PROXY_USER: Optional[str] = None
    DECODO_PROXY_PASS: Optional[str] = None
    
    # Rate Limiting
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_PER_HOUR: int = 100
    
    # AI Models
    CLAUDE_MODEL: str = "claude-sonnet-4-20250514"
    OPENAI_EMBEDDING_MODEL: str = "text-embedding-3-small"
    
    # File Paths
    TEMPLATE_DIR: str = "templates"
    DATA_DIR: str = "data"
    KNOWLEDGE_GRAPH_PATH: str = "data/knowledge-graph.json"
    YOUTUBE_COOKIES_PATH: str = "youtube_cookies.txt"
    
    # Caching
    USAGE_LOG_SIZE: int = 1000
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"  # json or text
    LOG_FILE: Optional[str] = None
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )
    
    def get_cors_origins(self) -> List[str]:
        """Get CORS allowed origins based on environment"""
        if self.ENVIRONMENT == "production":
            return self.ALLOWED_ORIGINS
        return ["*"] if self.DEBUG else self.ALLOWED_ORIGINS
    
    def validate_required_keys(self) -> dict:
        """Validate that all required API keys are present"""
        required = {
            "OPENAI_API_KEY": self.OPENAI_API_KEY,
            "ANTHROPIC_API_KEY": self.ANTHROPIC_API_KEY,
            "PINECONE_API_KEY": self.PINECONE_API_KEY,
            "DATABASE_URL": self.DATABASE_URL,
        }
        
        optional = {
            "PINECONE_ENVIRONMENT": self.PINECONE_ENVIRONMENT,
            "BRAVE_API_KEY": self.BRAVE_API_KEY,
            "DECODO_PROXY_HOST": self.DECODO_PROXY_HOST,
        }
        
        missing_required = [k for k, v in required.items() if not v]
        missing_optional = [k for k, v in optional.items() if not v]
        
        return {
            "valid": len(missing_required) == 0,
            "missing_required": missing_required,
            "missing_optional": missing_optional,
        }


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance
    Uses lru_cache to ensure singleton pattern
    """
    return Settings()


# Convenience exports
settings = get_settings()

