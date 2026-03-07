"""
Configuration settings for the chatbot module.

This module defines all configuration settings including database URLs,
JWT settings, LLM provider settings, and session configuration.
"""

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Service Configuration
    SERVICE_NAME: str = "chatbot"
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8002
    
    # Chat Database (Async PostgreSQL)
    CHAT_DATABASE_URL: str
    
    # Main Database (Sync PostgreSQL - for reading via existing services)
    MAIN_DATABASE_URL: str
    
    # Security
    JWT_SECRET: str
    JWT_ALGORITHM: str = "HS256"
    
    # OpenAI Configuration
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "gpt-4o-mini"
    OPENAI_MAX_TOKENS: int = 500
    OPENAI_TEMPERATURE: float = 0.7
    
    # LLM Provider Selection
    LLM_PROVIDER: str = "openai"  # openai, gemini
    
    # Session Configuration
    SESSION_EXPIRY_HOURS: int = 24
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"
    
    # Database Connection Pool Settings
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 10
    DB_POOL_TIMEOUT: int = 30
    DB_POOL_RECYCLE: int = 3600
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# Global settings instance
settings = Settings()
