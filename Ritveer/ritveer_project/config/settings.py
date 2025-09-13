import yaml
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Any

def load_yaml_config(file_path: str) -> dict[str, Any]:
    """Helper function to load and parse a YAML configuration file."""
    with open(file_path, 'r') as f:
        return yaml.safe_load(f)

class Settings(BaseSettings):
    """
    Defines the application's configuration settings, loaded from a .env file.
    Pydantic automatically reads environment variables and validates their types.
    """
    # By default, pydantic-settings looks for a .env file in the same directory.
    # We point it to the project root.
    model_config = SettingsConfigDict(env_file=Path(__file__).parent.parent / '.env', env_file_encoding='utf-8')

    # --- INFRASTRUCTURE ---
    # These variables are read directly from your .env file
    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    POSTGRES_HOST: str = "postgres"
    POSTGRES_PORT: int = 5432

    # --- EXTERNAL APIs ---
    TWILIO_ACCOUNT_SID: str
    TWILIO_AUTH_TOKEN: str
    RAZORPAY_KEY_ID: str
    RAZORPAY_KEY_SECRET: str
    SHIPROCKET_API_KEY: str
    GOOGLE_MAPS_API_KEY: str

    # --- LANGSMITH (Optional but Recommended) ---
    LANGCHAIN_TRACING_V2: bool = False
    LANGCHAIN_API_KEY: str | None = None # Optional, can be None

    # --- OPERATIONAL POLICIES ---
    # We load the business rules from the YAML file into this attribute.
    # This makes the settings object the single source for ALL config.
    POLICY_CONFIG: dict[str, Any] = load_yaml_config(Path(__file__).parent / 'policy.yml')

# Create a single instance of the settings class.
# Throughout the application, you will import this `settings` object
# instead of creating new instances. This ensures the .env and YAML
# files are read only once.
settings = Settings()

# --- Example of how to use it elsewhere in your app ---
# from config.settings import settings
#
# print(f"Connecting to Redis at {settings.REDIS_HOST}:{settings.REDIS_PORT}")
# max_late = settings.POLICY_CONFIG['supplier_policy']['three_strike_rule']['max_late_deliveries']
# print(f"Max late deliveries allowed: {max_late}")
