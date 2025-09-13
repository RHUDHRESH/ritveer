import logging
import os
from config.settings import settings

def setup_logging():
    """
    Sets up the logging configuration for the application.
    """
    log_level = os.environ.get("LOG_LEVEL", "INFO").upper()
    log_file = settings.LOG_FILE_PATH # Assuming LOG_FILE_PATH is defined in settings

    # Create logs directory if it doesn't exist
    log_dir = os.path.dirname(log_file)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir)

    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(), # Log to console
            logging.FileHandler(log_file) # Log to file
        ]
    )

    # Set specific log levels for some modules if needed
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)

    print(f"Logging configured. Level: {log_level}, File: {log_file}")

def get_logger(name: str) -> logging.Logger:
    """
    Returns a logger instance with the given name.
    """
    return logging.getLogger(name)

# Call setup_logging once when the module is imported
setup_logging()
