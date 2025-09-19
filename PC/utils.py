from config import (
    WASTE_TYPES,
    LOG_MSG_INVALID_WASTE,
    ESP_MSG_SET_TYPE,
    LOG_PREFIX_SEND,
    ESP_HOSTNAME
)

from datetime import datetime

def log_message(prefix, message):
    """Log a message with timestamp and prefix"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] [{prefix}] {message}")

def log_info(message):
    """Log an info message"""
    log_message("INFO", message)

def log_error(message):
    """Log an error message"""
    log_message("ERROR", message)

def log_warning(message):
    """Log a warning message"""
    log_message("WARNING", message)

def log_success(message):
    """Log a success message"""
    log_message("SUCCESS", message)

def log_debug(message):
    """Log a debug message"""
    log_message("DEBUG", message)