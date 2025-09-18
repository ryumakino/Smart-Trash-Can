import time
import random
import logging
from typing import Dict, Any
from config import (
    get_config,
    WASTE_TYPES,
    LOG_MSG_INVALID_WASTE,
    PROCESSING_FAIL,
    ESP_MSG_SET_TYPE,
    LOG_PREFIX_SEND,
    comm_manager,
    CHANNEL_SERIAL,
    CHANNEL_UDP,
    ESP_MSG_MOVEMENT,
    LOG_PREFIX_RECEIVE,
    LOG_PREFIX_MOVEMENT,
    LOG_MSG_MOVEMENT,
    ESP_MSG_DISPOSAL_DONE,
    LOG_MSG_DISPOSAL_OK,
    ESP_MSG_ERROR,
    ESP_MSG_ERROR_ALT,
    LOG_MSG_ERROR_ESP32,
    LOG_PREFIX_RANDOM
)
from connections import comm_manager

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

# -------------------------
# Validation Functions
# -------------------------

def is_valid_waste_type(waste_type: int) -> bool:
    """
    Validate if the waste type is valid.
    
    Args:
        waste_type: The waste type to validate
        
    Returns:
        bool: True if valid, False otherwise
    """
    return 0 <= waste_type < len(WASTE_TYPES)

def get_waste_name(waste_type: int) -> str:
    """
    Return the name of the waste type.
    
    Args:
        waste_type: The waste type identifier
        
    Returns:
        str: The name of the waste type or "UNKNOWN"
    """
    if is_valid_waste_type(waste_type):
        return WASTE_TYPES[waste_type]
    return "UNKNOWN"

# -------------------------
# Communication Functions
# -------------------------

def send_waste_type(waste_type: int) -> bool:
    """
    Send waste type to ESP32 using the detected channel.
    
    Args:
        waste_type: The waste type to send
        
    Returns:
        bool: True if successful, False otherwise
    """
    if not is_valid_waste_type(waste_type):
        log_error(f"{LOG_MSG_INVALID_WASTE}: {waste_type}")
        return PROCESSING_FAIL
    
    waste_name = get_waste_name(waste_type)
    message = f"{ESP_MSG_SET_TYPE}{waste_type}"
    
    esp_channel = comm_manager.get_esp32_channel() or "AUTO"
    log_message(LOG_PREFIX_SEND, f"Sending {waste_name} via channel {esp_channel}")
    
    return comm_manager.send_message(message)

def process_esp32_messages() -> bool:
    """
    Process messages received from ESP32 and detect channel.
    
    Returns:
        bool: True if movement was detected, False otherwise
    """
    messages = comm_manager.read_messages()
    movement_detected = False
    
    for source, message in messages:
        log_message(LOG_PREFIX_RECEIVE, f"ESP32 ({source}) -> {message}")
        
        # Update active channel
        if source == CHANNEL_SERIAL:
            comm_manager.esp32_channel = CHANNEL_SERIAL
        elif source == CHANNEL_UDP:
            comm_manager.esp32_channel = CHANNEL_UDP
        
        msg_upper = message.upper()
        
        # Process important messages
        if ESP_MSG_MOVEMENT in msg_upper:
            movement_detected = True
            log_message(LOG_PREFIX_MOVEMENT, f"{LOG_MSG_MOVEMENT} via {source}")
        
        elif ESP_MSG_DISPOSAL_DONE in msg_upper:
            log_success(LOG_MSG_DISPOSAL_OK)
        
        elif ESP_MSG_ERROR in msg_upper or ESP_MSG_ERROR_ALT in msg_upper:
            log_error(f"{LOG_MSG_ERROR_ESP32}: {message}")
    
    return movement_detected

def get_system_status() -> Dict[str, Any]:
    """
    Get and display the complete system status.
    
    Returns:
        Dict: Dictionary containing system status information
    """
    esp_channel = comm_manager.get_esp32_channel()
    
    status = {
        'serial_connected': comm_manager.serial_conn is not None and comm_manager.serial_conn.is_open,
        'udp_connected': comm_manager.udp_socket is not None,
        'esp32_channel': esp_channel,
        'last_communication': (
            time.time() - comm_manager.last_communication_time
            if comm_manager.last_communication_time > 0 else "Never"
        )
    }
    
    logger.info("System status check:")
    for key, value in status.items():
        if key == "last_communication" and isinstance(value, (int, float)):
            logger.info(f"{key}: {value:.1f}s ago")
        else:
            logger.info(f"{key}: {value}")
    
    return status

# -------------------------
# Fallback Functions
# -------------------------

def random_waste_fallback(reason: str) -> int:
    """
    Fallback to random classification.
    
    Args:
        reason: The reason for using fallback
        
    Returns:
        int: Random waste type
    """
    waste_type = random.randint(0, len(WASTE_TYPES) - 1)
    log_message(LOG_PREFIX_RANDOM, f"{reason}: {waste_type} ({get_waste_name(waste_type)})")
    return waste_type