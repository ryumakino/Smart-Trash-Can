import logging
from config import (
    get_config,
    WASTE_TYPES,
    LOG_MSG_INVALID_WASTE,
    ESP_MSG_SET_TYPE,
    LOG_PREFIX_SEND,
    ESP_HOSTNAME
)

# Configure logging
logging.basicConfig(
    level=getattr(logging, get_config("LOG_LEVEL", "INFO")),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('data/logs/system.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# -------------------------
# Centralized Logging Functions
# -------------------------

def log_message(prefix: str, message: str) -> None:
    """Centralized function for logging with prefix"""
    logger.info(f"{prefix} {message}")

def log_error(message: str) -> None:
    """Log error message"""
    logger.error(message)

def log_warning(message: str) -> None:
    """Log warning message"""
    logger.warning(message)

def log_info(message: str) -> None:
    """Log info message"""
    logger.info(message)

def log_success(message: str) -> None:
    """Log success message"""
    logger.info(f"✅ {message}")

def log_camera(message: str) -> None:
    """Log camera-related message"""
    logger.info(f"📸 {message}")

def log_model(message: str) -> None:
    """Log ML model-related message"""
    logger.info(f"🤖 {message}")