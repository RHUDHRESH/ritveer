import logging
import os

LOGGING_LEVEL = logging.INFO
LOGGING_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# Use PostgreSQL if available, fallback to SQLite
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///agents.db")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
