class WiFiConfig:
    SSID: str = "makedc"
    PASSWORD: str = "deco747387"
    TIMEOUT: int = 10
    MAX_RETRIES: int = 10
    RETRY_DELAY: int = 5

class NetworkConfig:
    # --- UDP ---
    UDP_PORT = 8888
    UDP_BUFFER_SIZE = 1024
    UDP_SOCKET_TIMEOUT = 1.0

    # --- Segurança ---
    AUTH_KEY = "TR4SH_4I_S3CUR3_K3Y_2024_M4K3DC_D3C0747387"
    TOKEN_TIMEOUT = 30  # segundos
    AUTH_TIMEOUT = 5  # Adicionado

class IRSensorConfig:
    PIN: int = 34               # Pino do sensor IR
    CHECK_INTERVAL: float = 0.1 # Intervalo de leitura em segundos
    ACTIVE_HIGH: bool = True    # Sensor ativo em nível alto
    DETECTION_THRESHOLD: int = 2 # Número de leituras consecutivas para confirmar movimento

class ServoConfig:
    SERVO_PIN: int = 18
    FREQ: int = 50
    MIN_DUTY: int = 40
    MAX_DUTY: int = 115
    RESET_DELAY: int = 3
    WASTE_TYPES = ["PLASTICO", "PAPEL", "VIDRO", "METAL", "LIXO", "PAPELAO"]
    SERVO_ANGLES = [0, 30, 60, 90, 120, 150]