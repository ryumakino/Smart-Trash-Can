from manager import CommunicationManager
import time
from config import (
    LOG_PREFIX_SYSTEM,
    MAX_CONNECTION_ATTEMPTS,
    LOG_CONNECTION_OK,
    LOG_CONNECTION_ERROR,
    ESP_MSG_MOVEMENT,
    LOG_PREFIX_RECEIVE,
    LOG_PREFIX_MOVEMENT,
    LOG_MSG_MOVEMENT,
    ESP_MSG_DISPOSAL_DONE,
    LOG_MSG_DISPOSAL_OK,
    ESP_MSG_ERROR,
    ESP_MSG_ERROR_ALT,
    LOG_MSG_ERROR_ESP32,
    ESP_MSG_SET_TYPE,
    ESP_MSG_TYPE,
    LOG_MSG_INVALID_WASTE
)
from utils import log_message, log_success, log_error, log_warning

# Global instance
comm_manager = CommunicationManager()

def setup_connections() -> bool:
    """
    Set up connections to ESP32.
    
    Returns:
        bool: True if connections established, False otherwise
    """
    log_message(LOG_PREFIX_SYSTEM, "Initializing connections...")
    attempt = 0
    
    while attempt < MAX_CONNECTION_ATTEMPTS:
        attempt += 1
        log_message(LOG_PREFIX_SYSTEM, f"Connection attempt {attempt}/{MAX_CONNECTION_ATTEMPTS}")
        
        if comm_manager.detect_channel():
            log_success(LOG_CONNECTION_OK)
            log_success(f"ESP32 responding via channel: {comm_manager.get_esp32_channel()}")
            return True
        
        time.sleep(1)
    
    log_error(LOG_CONNECTION_ERROR)
    return False

def _process_movement_message(result, source):
    result['movement_detected'] = True
    result['needs_processing'] = True
    log_message(LOG_PREFIX_MOVEMENT, f"{LOG_MSG_MOVEMENT} via {source}")

def _process_disposal_done_message(result):
    result['disposal_completed'] = True
    log_success(LOG_MSG_DISPOSAL_OK)

def _process_error_message(result, message):
    result['error_occurred'] = True
    result['error_message'] = message
    log_error(f"{LOG_MSG_ERROR_ESP32}: {message}")

def _process_waste_type_message(result, message):
    parts = message.split(':')
    if len(parts) >= 2:
        try:
            waste_type = int(parts[1])
            if 0 <= waste_type <= 5:
                result['waste_type_selected'] = waste_type
                result['needs_processing'] = True
                log_message("INFO", f"Waste type selected: {waste_type}")
            else:
                log_warning(LOG_MSG_INVALID_WASTE)
        except ValueError:
            log_warning(f"Invalid waste type format: {message}")

def _process_numeric_waste_type_message(result, message):
    try:
        waste_type = int(message.strip())
        result['waste_type_selected'] = waste_type
        result['needs_processing'] = True
        log_message("INFO", f"Waste type selected via number: {waste_type}")
    except ValueError:
        pass

def process_esp32_messages() -> dict:
    """
    Process messages received from ESP32 and return detailed status.

    Returns:
        dict: Dictionary with message processing results containing:
            - movement_detected: bool (if movement was detected)
            - disposal_completed: bool (if disposal was completed)
            - error_occurred: bool (if error occurred)
            - waste_type_selected: int (waste type if selected, else -1)
            - raw_messages: list (raw messages received)
            - needs_processing: bool (if system needs to process something)
    """
    messages = comm_manager.read_messages()
    result = {
        'movement_detected': False,
        'disposal_completed': False,
        'error_occurred': False,
        'waste_type_selected': -1,
        'raw_messages': [],
        'needs_processing': False,
        'error_message': '',
        'source_channel': ''
    }

    for source, message in messages:
        result['raw_messages'].append({'source': source, 'message': message})
        result['source_channel'] = source
        log_message(LOG_PREFIX_RECEIVE, f"ESP32 ({source}) -> {message}")
        msg_upper = message.upper()

        if ESP_MSG_MOVEMENT in msg_upper:
            _process_movement_message(result, source)
        elif ESP_MSG_DISPOSAL_DONE in msg_upper:
            _process_disposal_done_message(result)
        elif ESP_MSG_ERROR in msg_upper or ESP_MSG_ERROR_ALT in msg_upper:
            _process_error_message(result, message)
        elif ESP_MSG_SET_TYPE in msg_upper or ESP_MSG_TYPE in msg_upper:
            _process_waste_type_message(result, message)
        elif message.strip() in ['0', '1', '2', '3', '4', '5']:
            _process_numeric_waste_type_message(result, message)

    return result

def send_waste_type(waste_type: int) -> bool:
    """
    Send waste type to ESP32.
    
    Args:
        waste_type: Waste type identifier (0-5)
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        if 0 <= waste_type <= 5:
            success = comm_manager.send_message(f"SET_TYPE:{waste_type}")
            if success:
                log_message("INFO", f"Sent waste type: {waste_type}")
            return success
        else:
            log_error(f"Invalid waste type: {waste_type}")
            return False
    except Exception as e:
        log_error(f"Error sending waste type: {e}")
        return False

def get_connection_status() -> dict:
    """
    Get current connection status.
    
    Returns:
        dict: Connection status information
    """
    return {
        'active_channel': comm_manager.get_esp32_channel(),
        'esp32_ip': comm_manager.get_esp32_ip(),
        'is_connected': comm_manager.get_esp32_channel() != 'NONE',
        'last_communication': comm_manager.last_communication_time
    }