import platform
from typing import List

# =====================================================
# ----------- OPERATING SYSTEM -----------------------
# =====================================================

OS_WINDOWS = "Windows"
OS_LINUX = "Linux"
OS_MAC = "Darwin"
OS_UNKNOWN = "Unknown"

OPERATION_SYSTEM: str = platform.system()
IS_WINDOWS: bool = OPERATION_SYSTEM == OS_WINDOWS
IS_LINUX: bool = OPERATION_SYSTEM == OS_LINUX
IS_MAC: bool = OPERATION_SYSTEM == OS_MAC

# =====================================================
# ----------- COMMUNICATION CHANNELS ----------------
# =====================================================

# Channel activation
USE_SERIAL: bool = True
USE_BLUETOOTH: bool = False
USE_WIFI: bool = True

# Serial
SERIAL_BAUDRATE: int = 115200
SERIAL_TIMEOUT: float = 1.0
if IS_WINDOWS:
    SERIAL_PORT: str = "COM3"
elif IS_LINUX:
    SERIAL_PORT: str = "/dev/ttyUSB0"
elif IS_MAC:
    SERIAL_PORT: str = "/dev/tty.SLAB_USBtoUART"
else:
    SERIAL_PORT: str = ""

# UDP / Wi-Fi
ESP_IP: str = "192.168.1.100"
PC_IP: str = "192.168.1.50"
UDP_PORT: int = 12345
UDP_TIMEOUT: float = 2.0
MAX_RETRIES: int = 3
BUFFER_SIZE: int = 1024
PING_COUNT: int = 1
PING_TIMEOUT: int = 1000

# =====================================================
# ----------- LOGS AND CHANNELS ----------------------
# =====================================================

# Log prefixes
LOG_PREFIX_SERIAL: str = "📤 Serial ->"
LOG_PREFIX_UDP: str = "📤 UDP ->"
LOG_PREFIX_ERROR: str = "❌"
LOG_PREFIX_WARNING: str = "⚠️"
LOG_PREFIX_INFO: str = "ℹ️"
LOG_PREFIX_SUCCESS: str = "✅"
LOG_PREFIX_CAMERA: str = "📸"
LOG_PREFIX_MODEL: str = "🤖"
LOG_PREFIX_RANDOM: str = "🎲"
LOG_PREFIX_MOVEMENT: str = "🎯"
LOG_PREFIX_RECEIVE: str = "📥"
LOG_PREFIX_SEND: str = "📤"
LOG_PREFIX_SYSTEM: str = "🔌"

# Channel names
CHANNEL_SERIAL: str = "SERIAL"
CHANNEL_UDP: str = "UDP"
CHANNEL_NONE: str = "NONE"

# Default communication messages
MSG_NO_CHANNEL: str = "No available channel to send the message"
MSG_ESP32_NOT_FOUND: str = "ESP32 channel could not be detected"

# =====================================================
# ----------- MACHINE LEARNING -----------------------
# =====================================================

MODEL_PATH: str = "models/waste_model.h5"
CONFIDENCE_THRESHOLD: float = 0.7
DEFAULT_WASTE_TYPE: int = 0  # PLASTIC (fallback)
MODEL_FALLBACK_RANDOM: bool = True

# ML logs
LOG_MODEL_LOAD_OK: str = "ML model loaded successfully"
LOG_MODEL_LOAD_ERROR: str = "ERROR loading ML model"
LOG_MODEL_FALLBACK: str = "Using random classification as fallback"
LOG_MODEL_NOT_LOADED: str = "ML model not loaded, using random classification"
LOG_MODEL_PREPROCESS_FAIL: str = "Image preprocessing failed"
LOG_MODEL_CLASSIFICATION: str = "Classified as"
LOG_MODEL_LOW_CONFIDENCE: str = "Low confidence, using random classification"
LOG_MODEL_CLASSIFICATION_ERROR: str = "ERROR in ML classification"

# Waste types
WASTE_TYPES: List[str] = ["PLASTIC", "PAPER", "GLASS", "METAL", "TRASH", "CARDBOARD"]
WASTE_TYPE_PLASTIC: int = 0
WASTE_TYPE_PAPER: int = 1
WASTE_TYPE_GLASS: int = 2
WASTE_TYPE_METAL: int = 3
WASTE_TYPE_TRASH: int = 4
WASTE_TYPE_SCARDBOARD: int = 5

# =====================================================
# ----------- CAMERA / IMAGES ------------------------
# =====================================================

CAMERA_ID: int = 0
IMAGE_SAVE_PATH: str = "data/captured/waste_capture"
IMAGE_WIDTH: int = 512
IMAGE_HEIGHT: int = 384
CAPTURE_WIDTH: int = 1280
CAPTURE_HEIGHT: int = 720
IMAGE_FORMAT: str = "jpg"
SAVE_IMAGES: bool = True
DISPLAY_TIME_MS: int = 1000
BLUR_KERNEL: tuple = (3, 3)
CAMERA_WARMUP_ATTEMPTS: int = 5

# =====================================================
# ----------- ESP32 / MESSAGES -----------------------
# =====================================================

ESP_MSG_MOVEMENT: str = "MOVEMENT_DETECTED"
ESP_MSG_DISPOSAL_DONE: str = "DISPOSAL_COMPLETED"
ESP_MSG_ERROR: str = "ERROR"
ESP_MSG_ERROR_ALT: str = "ERROR"
ESP_MSG_SET_TYPE: str = "SET_TYPE:"
ESP_MSG_TYPE: str = "TYPE:"

# ESP message logs
LOG_MSG_INVALID_WASTE: str = "ERROR: Invalid waste type"
LOG_MSG_MOVEMENT: str = "Movement detected"
LOG_MSG_DISPOSAL_OK: str = "Disposal successfully processed!"
LOG_MSG_ERROR_ESP32: str = "ERROR reported by ESP32"

# =====================================================
# ----------- MAIN SYSTEM ----------------------------
# =====================================================

MAX_CONNECTION_ATTEMPTS: int = 10
MOVEMENT_CHECK_INTERVAL: float = 1.0  # seconds
STATUS_CHECK_INTERVAL: int = 30  # seconds
NO_TYPE_SELECTED: int = -1

# System logs
LOG_HEADER: str = "WASTE CLASSIFICATION SYSTEM - PC"
LOG_CONNECTION_FAIL: str = "Failed to initialize connections"
LOG_CONNECTION_OK: str = "Connections successfully initialized!"
LOG_CONNECTION_ERROR: str = "Unable to initialize connections. Check ESP32 and network."
LOG_MODEL_OK: str = "ML model loaded successfully!"
LOG_MODEL_FAIL: str = "Failed to load ML model. Fallback mode activated."
LOG_MODEL_ERROR: str = "Error loading ML model"
LOG_MOVEMENT_DETECTED: str = "Movement detected! Capturing image..."
LOG_IMAGE_FAIL: str = "Failed to capture image"
LOG_IMAGE_ERROR: str = "Error capturing/processing image"
LOG_CLASSIFICATION_ERROR: str = "Error in ML classification"
LOG_CLASSIFICATION_RANDOM: str = "Using random classification"
LOG_SEND_OK: str = "Waste type sent"
LOG_SEND_FAIL: str = "Failed to send waste type"
LOG_STATUS_ERROR: str = "Error obtaining system status"
LOG_INTERRUPTED: str = "Interrupted by user"
LOG_UNEXPECTED_ERROR: str = "Unexpected ERROR"
LOG_CONNECTIONS_CLOSED: str = "Connections closed. Program terminated."
LOG_MSG_SYSTEM_STATUS: str = "SYSTEM STATUS"

# =====================================================
# ----------- TIME CONSTANTS -------------------------
# =====================================================

TIME_SERIAL_WAIT: float = 2.0
TIME_CAMERA_WARMUP: float = 0.1
TIME_MAIN_LOOP_SLEEP: float = 0.05
TIME_STATUS_CHECK: int = 30

# =====================================================
# ----------- PROCESSING CONSTANTS -------------------
# =====================================================

PROCESSING_SUCCESS: bool = True
PROCESSING_FAIL: bool = False
IMAGE_PREPROCESS_SUCCESS: bool = True
IMAGE_PREPROCESS_FAIL: bool = False