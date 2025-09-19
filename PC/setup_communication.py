import time
from communication_manager import CommunicationManager
from utils import log_info, log_error, log_success, log_warning

# Global instance
comm_manager = CommunicationManager()

# Mensagens ESP32
ESP_MSG_MOVEMENT = "MOVEMENT"
ESP_MSG_DISPOSAL_DONE = "DISPOSAL_DONE"
ESP_MSG_ERROR = "ERROR"
ESP_MSG_ERROR_ALT = "ERR"
ESP_MSG_SET_TYPE = "SET_TYPE"
ESP_MSG_TYPE = "TYPE"

MAX_CONNECTION_ATTEMPTS = 3

def setup_connections() -> bool:
    """Set up connections to ESP32."""
    log_info("Initializing connections...")
    for _ in range(1, MAX_CONNECTION_ATTEMPTS + 1):
        if comm_manager.detect_channel() and comm_manager.is_synchronized():
            log_success(f"Connection established via {comm_manager.get_channel()}")
            return True
        time.sleep(1)
    log_error("Failed to establish connection with ESP32")
    return False

def process_esp32_messages() -> dict:
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
        msg_upper = message.upper()

        # Adicionar suporte a mensagens do ESP32
        if "IR:DETECTED" in msg_upper or "MOVEMENT" in msg_upper:
            result['movement_detected'] = True
            result['needs_processing'] = True
        elif "IR:CLEARED" in msg_upper:
            result['movement_detected'] = False
        elif "PONG" in msg_upper:
            # Resposta keep-alive
            pass
        elif "STATUS:" in msg_upper:
            # Mensagem de status
            pass

    return result

def send_waste_type(waste_type: int) -> bool:
    """
    Send waste type to ESP32.
    """
    if not comm_manager.is_synchronized():
        log_error("Cannot send waste type - communication not synchronized")
        return False
    if 0 <= waste_type <= 5:
        msg = f"{ESP_MSG_SET_TYPE}:{waste_type}"
        return comm_manager.send_message(msg)
    else:
        log_error(f"Invalid waste type: {waste_type}")
        return False

def get_connection_status() -> dict:
    return {
        'active_channel': comm_manager.get_channel(),
        'is_connected': comm_manager.get_channel() != 'NONE',
        'is_synchronized': comm_manager.is_synchronized(),
        'last_communication': comm_manager.last_communication_time
    }
