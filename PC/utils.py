import time
import random
from config import *
from connections import comm_manager

# -------------------------
# Funções de logging centralizadas
# -------------------------
def log_message(prefix, message):
    """Função centralizada para logging"""
    print(f"{prefix} {message}")

def log_error(message):
    """Log de erro"""
    log_message(LOG_PREFIX_ERROR, message)

def log_warning(message):
    """Log de warning"""
    log_message(LOG_PREFIX_WARNING, message)

def log_info(message):
    """Log de informação"""
    log_message(LOG_PREFIX_INFO, message)

def log_success(message):
    """Log de sucesso"""
    log_message(LOG_PREFIX_SUCCESS, message)

def log_camera(message):
    """Log relacionado à câmera"""
    log_message(LOG_PREFIX_CAMERA, message)

def log_model(message):
    """Log relacionado ao modelo ML"""
    log_message(LOG_PREFIX_MODEL, message)

# -------------------------
# Funções de validação
# -------------------------
def is_valid_waste_type(waste_type):
    """Valida se o tipo de lixo é válido"""
    return 0 <= waste_type < len(WASTE_TYPES)

def get_waste_name(waste_type):
    """Retorna o nome do tipo de lixo"""
    if is_valid_waste_type(waste_type):
        return WASTE_TYPES[waste_type]
    return "DESCONHECIDO"

# -------------------------
# Funções de comunicação
# -------------------------
def send_waste_type(waste_type):
    """Envia o tipo de lixo para o ESP32 usando o canal detectado"""
    if not is_valid_waste_type(waste_type):
        log_error(f"{LOG_MSG_INVALID_WASTE}: {waste_type}")
        return PROCESSING_FAIL
    
    waste_name = get_waste_name(waste_type)
    message = f"{ESP_MSG_SET_TYPE}{waste_type}"
    
    esp_channel = comm_manager.get_esp32_channel() or "AUTO"
    log_message(LOG_PREFIX_SEND, f"Enviando {waste_name} via canal {esp_channel}")
    
    return comm_manager.send_message(message)

def process_esp32_messages():
    """Processa mensagens recebidas do ESP32 e detecta canal"""
    messages = comm_manager.read_messages()
    movement_detected = False
    
    for source, message in messages:
        log_message(LOG_PREFIX_RECEIVE, f"ESP32 ({source}) -> {message}")
        
        # Atualiza o canal ativo
        if source == CHANNEL_SERIAL:
            comm_manager.esp32_channel = CHANNEL_SERIAL
        elif source == CHANNEL_UDP:
            comm_manager.esp32_channel = CHANNEL_UDP
        
        msg_upper = message.upper()
        
        # Processa mensagens importantes
        if ESP_MSG_MOVEMENT in msg_upper:
            movement_detected = True
            log_message(LOG_PREFIX_MOVEMENT, f"{LOG_MSG_MOVEMENT} via {source}")
        
        elif ESP_MSG_DISPOSAL_DONE in msg_upper:
            log_success(LOG_MSG_DISPOSAL_OK)
        
        elif ESP_MSG_ERROR in msg_upper or ESP_MSG_ERROR_ALT in msg_upper:
            log_error(f"{LOG_MSG_ERROR_ESP32}: {message}")
    
    return movement_detected

def get_system_status():
    """Obtém e exibe o status completo do sistema"""
    esp_channel = comm_manager.get_esp32_channel()
    
    status = {
        'serial_connected': comm_manager.serial_conn is not None and comm_manager.serial_conn.is_open,
        'udp_connected': comm_manager.udp_socket is not None,
        'esp32_channel': esp_channel,
        'last_communication': (
            time.time() - comm_manager.last_communication_time
            if comm_manager.last_communication_time > 0 else "Nunca"
        )
    }
    
    print(f"\n=== {LOG_MSG_SYSTEM_STATUS} ===")
    for key, value in status.items():
        if key == "last_communication" and isinstance(value, (int, float)):
            print(f"{key}: {value:.1f}s atrás")
        else:
            print(f"{key}: {value}")
    print("===============================")
    
    return status

# -------------------------
# Funções de fallback
# -------------------------
def random_waste_fallback(reason):
    """Fallback para classificação aleatória"""
    waste_type = random.randint(0, len(WASTE_TYPES) - 1)
    log_message(LOG_PREFIX_RANDOM, f"{reason}: {waste_type} ({get_waste_name(waste_type)})")
    return waste_type