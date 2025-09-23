import platform
import serial.tools.list_ports
import time

class SystemConfig:
    # --- Sistema Operacional ---
    OS_WINDOWS = "Windows"
    OS_LINUX = "Linux" 
    OS_MAC = "Darwin"
    OPERATING_SYSTEM = platform.system()
    
    # --- Segurança ---
    AUTH_KEY = "TR4SH_4I_S3CUR3_K3Y_2024_M4K3DC_D3C0747387"
    TOKEN_TIMEOUT = 30  # segundos
    AUTH_TIMEOUT = 5  # Adicionado
    
    # --- Tentativas e Timeouts ---
    RECONNECT_ATTEMPTS = 3
    DISCOVERY_TIMEOUT = 5
    HEARTBEAT_INTERVAL = 10

    MAX_RETRIES = 3
    COMMAND_TIMEOUT = 5

class HardwareConfig:
    # --- Portas Serial por SO ---
    @staticmethod
    def get_serial_port():
        if SystemConfig.OPERATING_SYSTEM == SystemConfig.OS_WINDOWS:
            return "COM3"
        elif SystemConfig.OPERATING_SYSTEM == SystemConfig.OS_LINUX:
            return "/dev/ttyUSB0"
        elif SystemConfig.OPERATING_SYSTEM == SystemConfig.OS_MAC:
            return "/dev/tty.SLAB_USBtoUART"
        else:
            return ""
    
    # --- Tamanhos de buffer ---
    BUFFER_SIZE = 1024

class PCConfig:
    # --- Serial ---
    SERIAL_BAUDRATE = 115200
    SERIAL_TIMEOUT = 1
    SERIAL_WAIT_TIME = 2  # segundos
    TIME_SERIAL_WAIT = 2  # Adicionado para compatibilidade
    
    # --- UDP ---
    UDP_PORT = 8888
    UDP_BUFFER_SIZE = 1024
    UDP_SOCKET_TIMEOUT = 1.0
    
    # --- Descoberta ---
    DISCOVERY_TIMEOUT = 5
    DISCOVERY_RETRIES = 3
    RECONNECT_INTERVAL = 10
    DISCOVERY_BROADCAST_ADDR = '255.255.255.255'
    
    # --- Portas Serial disponíveis ---
    @staticmethod
    def get_serial_ports():
        """Retorna lista de portas serial disponíveis"""
        ports = []
        try:
            available_ports = list(serial.tools.list_ports.comports())
            for port_info in available_ports:
                ports.append({
                    'device': port_info.device,
                    'description': port_info.description,
                    'hwid': port_info.hwid
                })
        except Exception as e:
            print(f"Erro ao listar portas serial: {e}")
        return ports
    
    @staticmethod
    def get_default_serial_port():
        """Retorna porta serial padrão baseada no SO"""
        return HardwareConfig.get_serial_port()

class CameraConfig:
    CAMERA_ID = 0
    IMAGE_SAVE_DIR = "data/captured"
    IMAGE_SAVE_PATH = f"{IMAGE_SAVE_DIR}/waste_capture"
    IMAGE_FORMAT = "jpg"
    
    # --- Dimensões ---
    CAPTURE_WIDTH = 1280
    CAPTURE_HEIGHT = 720
    PROCESSED_WIDTH = 512
    PROCESSED_HEIGHT = 384
    
    # --- Processamento ---
    BLUR_KERNEL = (5, 5)
    DISPLAY_TIME_MS = 1000
    
    # --- Captura ---
    SAVE_IMAGES = True
    CAMERA_WARMUP_ATTEMPTS = 10
    CAMERA_WARMUP_DELAY = 0.5  # segundos

class MLConfig:
    # --- Tipos de Resíduo ---
    WASTE_TYPES = ["PLASTICO", "PAPEL", "VIDRO", "METAL", "LIXO", "PAPELAO"]
    
    # --- Classificação ---
    CONFIDENCE_THRESHOLD = 0.6
    
    # --- Modelo ---
    MODEL_INPUT_SHAPE = (384, 512, 3)
    USE_MOCK_MODEL = True

class CommunicationConfig:
    # --- Prefixos de Mensagem ---
    MESSAGE_PREFIXES = {
        'AUTH': 'AUTH:',
        'AUTH_OK': 'AUTH_OK:',
        'CMD': 'CMD:',
        'PING': 'PING:',
        'PONG': 'PONG:',
        'RESP': 'RESP:'
    }
    
    # --- Protocolos Suportados ---
    SUPPORTED_PROTOCOLS = ['serial', 'udp']
    PROTOCOL_PRIORITY = ['serial', 'udp']
    
    # --- Timeouts ---
    MESSAGE_RETRY_DELAY = 1.0
    CONNECTION_CHECK_INTERVAL = 5