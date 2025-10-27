"""
KARIGAR Configuration Settings
Centralized configuration management for the entire system
"""

import os
from typing import Optional
from pydantic import BaseSettings, Field


class Settings(BaseSettings):
    """Application settings - loads from .env file"""

    # API Configuration
    api_host: str = Field(default="0.0.0.0", env="API_HOST")
    api_port: int = Field(default=8000, env="API_PORT")
    api_debug: bool = Field(default=False, env="API_DEBUG")
    api_title: str = "KARIGAR - Artisan Multi-Agent Platform"
    api_version: str = "1.0.0"

    # Database Configuration
    database_url: str = Field(
        default="sqlite:///./karigar.db",
        env="DATABASE_URL"
    )

    # OpenAI Configuration
    openai_api_key: Optional[str] = Field(default=None, env="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4", env="OPENAI_MODEL")

    # Anthropic Configuration (Alternative)
    anthropic_api_key: Optional[str] = Field(default=None, env="ANTHROPIC_API_KEY")

    # Web Search Configuration
    perplexity_api_key: Optional[str] = Field(default=None, env="PERPLEXITY_API_KEY")

    # ChromaDB Vector Store
    chroma_db_path: str = Field(default="./data/chroma_db", env="CHROMA_DB_PATH")
    chroma_collection_name: str = Field(default="karigar_memory", env="CHROMA_COLLECTION_NAME")

    # Payment Configuration (Razorpay)
    razorpay_key_id: Optional[str] = Field(default=None, env="RAZORPAY_KEY_ID")
    razorpay_key_secret: Optional[str] = Field(default=None, env="RAZORPAY_KEY_SECRET")

    # Location Services
    nominatim_user_agent: str = Field(default="karigar-artisan-platform", env="NOMINATIM_USER_AGENT")

    # Logging Configuration
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    log_file: str = Field(default="./logs/karigar.log", env="LOG_FILE")

    # Feature Flags
    enable_web_scraping: bool = Field(default=True, env="ENABLE_WEB_SCRAPING")
    enable_supplier_search: bool = Field(default=True, env="ENABLE_SUPPLIER_SEARCH")
    enable_payment_processing: bool = Field(default=True, env="ENABLE_PAYMENT_PROCESSING")
    enable_pdf_generation: bool = Field(default=True, env="ENABLE_PDF_GENERATION")
    enable_notifications: bool = Field(default=True, env="ENABLE_NOTIFICATIONS")

    # Email Configuration
    smtp_server: str = Field(default="smtp.gmail.com", env="SMTP_SERVER")
    smtp_port: int = Field(default=587, env="SMTP_PORT")
    smtp_username: Optional[str] = Field(default=None, env="SMTP_USERNAME")
    smtp_password: Optional[str] = Field(default=None, env="SMTP_PASSWORD")
    smtp_from: str = Field(default="noreply@karigar.local", env="SMTP_FROM")

    # Timeout Settings (seconds)
    llm_timeout: int = Field(default=60, env="LLM_TIMEOUT")
    scraper_timeout: int = Field(default=30, env="SCRAPER_TIMEOUT")
    supplier_search_timeout: int = Field(default=15, env="SUPPLIER_SEARCH_TIMEOUT")
    pdf_generation_timeout: int = Field(default=20, env="PDF_GENERATION_TIMEOUT")

    # Cache TTL (seconds)
    cache_ttl_short: int = Field(default=300, env="CACHE_TTL_SHORT")
    cache_ttl_medium: int = Field(default=3600, env="CACHE_TTL_MEDIUM")
    cache_ttl_long: int = Field(default=86400, env="CACHE_TTL_LONG")

    # System Configuration
    max_workers: int = Field(default=4, env="MAX_WORKERS")
    max_concurrent_requests: int = Field(default=10, env="MAX_CONCURRENT_REQUESTS")
    batch_size: int = Field(default=10, env="BATCH_SIZE")

    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()


# Configuration Classes for Different Sections
class DatabaseConfig:
    """Database configuration"""
    url = settings.database_url
    echo = settings.api_debug
    pool_size = 20
    max_overflow = 40


class LLMConfig:
    """LLM configuration"""
    openai_api_key = settings.openai_api_key
    openai_model = settings.openai_model
    anthropic_api_key = settings.anthropic_api_key
    timeout = settings.llm_timeout
    temperature = 0.7
    max_tokens = 2000


class VectorStoreConfig:
    """Vector store (ChromaDB) configuration"""
    path = settings.chroma_db_path
    collection_name = settings.chroma_collection_name
    embedding_model = "all-MiniLM-L6-v2"  # Sentence transformer model
    chunk_size = 1000
    chunk_overlap = 100


class ToolConfig:
    """Tool execution configuration"""
    scraper_timeout = settings.scraper_timeout
    supplier_search_timeout = settings.supplier_search_timeout
    pdf_generation_timeout = settings.pdf_generation_timeout
    max_workers = settings.max_workers


class AgentConfig:
    """Agent configuration"""
    max_iterations = 10
    timeout = settings.llm_timeout
    temperature = 0.7
    top_k = 5
    retrieval_threshold = 0.5


class PaymentConfig:
    """Payment configuration"""
    razorpay_key_id = settings.razorpay_key_id
    razorpay_key_secret = settings.razorpay_key_secret
    currency = "INR"
    commission_percentage = 2.5  # Platform commission


class NotificationConfig:
    """Notification configuration"""
    smtp_server = settings.smtp_server
    smtp_port = settings.smtp_port
    smtp_username = settings.smtp_username
    smtp_password = settings.smtp_password
    smtp_from = settings.smtp_from
    enable_email = settings.smtp_username is not None
    enable_sms = False
    enable_whatsapp = False


# Logging configuration
LOG_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        },
        "detailed": {
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s"
        },
    },
    "handlers": {
        "default": {
            "formatter": "default",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stdout",
        },
        "file": {
            "formatter": "detailed",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": settings.log_file,
            "maxBytes": 10485760,  # 10MB
            "backupCount": 5,
        },
    },
    "loggers": {
        "karigar": {
            "handlers": ["default", "file"],
            "level": settings.log_level,
        },
        "fastapi": {
            "handlers": ["default"],
            "level": "INFO",
        },
        "sqlalchemy": {
            "handlers": ["file"],
            "level": "INFO",
        },
    },
}
