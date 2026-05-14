import os
import logging
from typing import List
from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)

_DEFAULT_JWT_SECRET = "your-super-secret-jwt-key-change-this-in-production"

class Settings(BaseSettings):
    # =============================================================================
    # Application Settings
    # =============================================================================
    APP_NAME: str = "Legal Research AI API"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"

    # TESTING is never read from .env — only set programmatically in test fixtures.
    # When True, the test-dev-token auth bypass is allowed.
    TESTING: bool = False
    
    # =============================================================================
    # Supabase Settings
    # =============================================================================
    SUPABASE_URL: str
    SUPABASE_KEY: str
    SUPABASE_SERVICE_ROLE_KEY: str | None = None
    
    # =============================================================================
    # Authentication Settings (JWT)
    # =============================================================================
    JWT_SECRET_KEY: str = "your-super-secret-jwt-key-change-this-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRATION_MINUTES: int = 1440  # 24 hours
    
    # =============================================================================
    # LLM Settings
    # =============================================================================
    # Ollama Configuration
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "gemma2:9b"
    OLLAMA_FALLBACK_MODEL: str = "gemma2:2b"
    
    # OpenAI Configuration (fallback)
    OPENAI_API_KEY: str | None = None
    OPENAI_MODEL: str = "gpt-3.5-turbo"
    
    # =============================================================================
    # Vector Database Settings
    # =============================================================================
    PINECONE_API_KEY: str | None = None
    PINECONE_INDEX_NAME: str = "legal-case-rag-advanced"
    
    # =============================================================================
    # CORS Settings
    # =============================================================================
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:5173"
    
    @property
    def cors_origins_list(self) -> List[str]:
        """Parse CORS origins from comma-separated string"""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]

    class Config:
        env_file = ".env"
        env_file_encoding = 'utf-8'
        extra = "ignore"

settings = Settings()

# Production safety check — warn if running with insecure defaults
if not settings.DEBUG and settings.JWT_SECRET_KEY == _DEFAULT_JWT_SECRET:
    logger.critical(
        "SECURITY WARNING: JWT_SECRET_KEY is set to the default insecure value "
        "in a non-debug environment! Set a strong secret in your .env file."
    )
