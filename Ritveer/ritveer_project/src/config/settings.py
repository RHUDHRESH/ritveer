from pydantic import BaseSettings


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""
    GOOGLE_MAPS_API_KEY: str | None = None

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
