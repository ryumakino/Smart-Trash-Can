class ESP32Config:
    # --- WiFi ---
    WIFI_SSID = "makedc"
    WIFI_PASSWORD = "deco747387"
    WIFI_TIMEOUT = 10
    MAX_RETRIES = 10
    RETRY_DELAY = 5
    
    # --- Rede ---
    UDP_PORT = 8888
    UDP_BUFFER_SIZE = 1024
    
    # --- Serial ---
    UART_PORT = 2  # UART2 no ESP32 (GPIO16=RX, GPIO17=TX)
    UART_BAUD = 115200
    
    # --- Hardware ---
    SERVO_PIN = 18
    IR_SENSOR_PIN = 34
    
    # --- Servo ---
    SERVO_FREQ = 50
    SERVO_MIN_DUTY = 40
    SERVO_MAX_DUTY = 115
    
    # --- Sistema ---
    CHANNEL_CHECK_INTERVAL = 5
    SERVO_RESET_DELAY = 3

# Configuração simplificada
WASTE_TYPES = ["PLASTICO", "PAPEL", "VIDRO", "METAL", "LIXO", "PAPELAO"]
SERVO_ANGLES = [0, 30, 60, 90, 120, 150]
AUTH_KEY = "TR4SH_4I_S3CUR3_K3Y_2024"