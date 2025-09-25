from typing import List

class UDPConfig:    
    # --- UDP ---
    UDP_PORT = 8888
    UDP_BUFFER_SIZE = 1024
    UDP_SOCKET_TIMEOUT = 1.0

    # --- Segurança ---
    AUTH_KEY = "TR4SH_4I_S3CUR3_K3Y_2024_M4K3DC_D3C0747387"
    TOKEN_TIMEOUT = 30  # segundos
    AUTH_TIMEOUT = 5  # Adicionado

class CameraConfig:
    CAMERA_ID: int = 1
    IMAGE_SAVE_DIR: str = "data/captured"
    IMAGE_SAVE_PATH: str = f"{IMAGE_SAVE_DIR}/waste_capture"
    IMAGE_FORMAT: str = "jpg"
    
    # --- Dimensões ---
    IMAGE_WIDTH: int = 512
    IMAGE_HEIGHT: int = 384
    CAPTURE_WIDTH: int = 1280
    CAPTURE_HEIGHT: int = 720
    
    # --- Processamento ---
    DISPLAY_TIME_MS: int = 1000
    BLUR_KERNEL: tuple = (5, 5)
    
    # --- Captura ---
    SAVE_IMAGES: bool = True
    WEB_CAM_INTERIOR: bool = False
    CAMERA_WARMUP_ATTEMPTS: int = 10
    CAMERA_WARMUP_DELAY: float = 0.5

class MLConfig:
    # --- Tipos de Resíduo ---
    WASTE_TYPES: List[str] = ["PAPELAO", "VIDRO", "METAL", "PAPEL", "PLASTICO", "LIXO"]
        
    # --- Classificação ---
    CONFIDENCE_THRESHOLD: float = 0.6
    
    # --- Modelo ---
    MODEL_INPUT_SHAPE = (224, 224, 3)  # Modelo treinado usa 224x224
    USE_MOCK_MODEL = False  # Agora usa o modelo real

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