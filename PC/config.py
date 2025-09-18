import platform

# =====================================================
# ----------- OPERATING SYSTEM -----------------------
# =====================================================

OS_WINDOWS = "Windows"
OS_LINUX = "Linux"
OS_MAC = "Darwin"
OS_UNKNOWN = "Unknown"

OPERATION_SYSTEM = platform.system()
IS_WINDOWS = OPERATION_SYSTEM == OS_WINDOWS
IS_LINUX = OPERATION_SYSTEM == OS_LINUX
IS_MAC = OPERATION_SYSTEM == OS_MAC

# =====================================================
# ----------- COMMUNICATION CHANNELS ----------------
# =====================================================

# Channel activation
USE_SERIAL = True
USE_BLUETOOTH = False
USE_WIFI = True

# Serial
SERIAL_BAUDRATE = 115200
SERIAL_TIMEOUT = 1.0
if IS_WINDOWS:
    SERIAL_PORT = "COM3"
elif IS_LINUX:
    SERIAL_PORT = "/dev/ttyUSB0"
elif IS_MAC:
    SERIAL_PORT = "/dev/tty.SLAB_USBtoUART"
else:
    SERIAL_PORT = None

# UDP / Wi-Fi
ESP_IP = "192.168.1.100"
PC_IP = "192.168.1.50"
UDP_PORT = 12345
UDP_TIMEOUT = 2.0
MAX_RETRIES = 3
BUFFER_SIZE = 1024
PING_COUNT = 1
PING_TIMEOUT = 1000

# =====================================================
# ----------- LOGS AND CHANNELS ----------------------
# =====================================================

# Log prefixes
LOG_PREFIX_SERIAL = "📤 Serial ->"
LOG_PREFIX_UDP = "📤 UDP ->"
LOG_PREFIX_ERROR = "❌"
LOG_PREFIX_WARNING = "⚠️"
LOG_PREFIX_INFO = "ℹ️"
LOG_PREFIX_SUCCESS = "✅"
LOG_PREFIX_CAMERA = "📸"
LOG_PREFIX_MODEL = "🤖"
LOG_PREFIX_RANDOM = "🎲"
LOG_PREFIX_MOVEMENT = "🎯"
LOG_PREFIX_RECEIVE = "📥"
LOG_PREFIX_SEND = "📤"
LOG_PREFIX_SYSTEM = "🔌"

# Channel names
CHANNEL_SERIAL = "SERIAL"
CHANNEL_UDP = "UDP"
CHANNEL_NONE = "NONE"

# Default communication messages
MSG_NO_CHANNEL = "No available channel to send the message"
MSG_ESP32_NOT_FOUND = "ESP32 channel could not be detected"

# =====================================================
# ----------- MACHINE LEARNING ----------------------
# =====================================================

USE_MODEL = True
MODEL_PATH = "waste_model.h5"
CONFIDENCE_THRESHOLD = 0.7
DEFAULT_WASTE_TYPE = 0  # PLASTIC (fallback)
MODEL_FALLBACK_RANDOM = True

# ML logs
LOG_MODEL_LOAD_OK = "ML model loaded successfully"
LOG_MODEL_LOAD_ERROR = "ERROR loading ML model"
LOG_MODEL_FALLBACK = "Using random classification as fallback"
LOG_MODEL_NOT_LOADED = "ML model not loaded, using random classification"
LOG_MODEL_PREPROCESS_FAIL = "Image preprocessing failed"
LOG_MODEL_CLASSIFICATION = "Classified as"
LOG_MODEL_LOW_CONFIDENCE = "Low confidence, using random classification"
LOG_MODEL_CLASSIFICATION_ERROR = "ERROR in ML classification"

# Waste types
WASTE_TYPES = ["PLASTIC", "PAPER", "GLASS", "METAL", "ORGANIC", "SPECIAL"]
WASTE_TYPE_PLASTIC = 0
WASTE_TYPE_PAPER = 1
WASTE_TYPE_GLASS = 2
WASTE_TYPE_METAL = 3
WASTE_TYPE_ORGANIC = 4
WASTE_TYPE_SPECIAL = 5

# =====================================================
# ----------- CAMERA / IMAGES -----------------------
# =====================================================

CAMERA_ID = 0
IMAGE_SAVE_PATH = "waste_capture"
IMAGE_WIDTH = 512
IMAGE_HEIGHT = 384
CAPTURE_WIDTH = 1280
CAPTURE_HEIGHT = 720
IMAGE_FORMAT = "jpg"
SAVE_IMAGES = True
DISPLAY_TIME_MS = 1000
BLUR_KERNEL = (3, 3)
CAMERA_WARMUP_ATTEMPTS = 5

# =====================================================
# ----------- ESP32 / MESSAGES ----------------------
# =====================================================

ESP_MSG_MOVEMENT = "MOVEMENT_DETECTED"
ESP_MSG_DISPOSAL_DONE = "DISPOSAL_COMPLETED"
ESP_MSG_ERROR = "ERROR"
ESP_MSG_ERROR_ALT = "ERROR"
ESP_MSG_SET_TYPE = "SET_TYPE:"
ESP_MSG_TYPE = "TYPE:"

# ESP message logs
LOG_MSG_INVALID_WASTE = "ERROR: Invalid waste type"
LOG_MSG_MOVEMENT = "Movement detected"
LOG_MSG_DISPOSAL_OK = "Disposal successfully processed!"
LOG_MSG_ERROR_ESP32 = "ERROR reported by ESP32"

# =====================================================
# ----------- MAIN SYSTEM ---------------------------
# =====================================================

MAX_CONNECTION_ATTEMPTS = 10
MOVEMENT_CHECK_INTERVAL = 1.0  # seconds
STATUS_CHECK_INTERVAL = 30  # seconds
NO_TYPE_SELECTED = -1

# System logs
LOG_HEADER = "WASTE CLASSIFICATION SYSTEM - PC"
LOG_CONNECTION_FAIL = "Failed to initialize connections"
LOG_CONNECTION_OK = "Connections successfully initialized!"
LOG_CONNECTION_ERROR = "Unable to initialize connections. Check ESP32 and network."
LOG_MODEL_OK = "ML model loaded successfully!"
LOG_MODEL_FAIL = "Failed to load ML model. Fallback mode activated."
LOG_MODEL_ERROR = "Error loading ML model"
LOG_MOVEMENT_DETECTED = "Movement detected! Capturing image..."
LOG_IMAGE_FAIL = "Failed to capture image"
LOG_IMAGE_ERROR = "Error capturing/processing image"
LOG_CLASSIFICATION_ERROR = "Error in ML classification"
LOG_CLASSIFICATION_RANDOM = "Using random classification"
LOG_SEND_OK = "Waste type sent"
LOG_SEND_FAIL = "Failed to send waste type"
LOG_STATUS_ERROR = "Error obtaining system status"
LOG_INTERRUPTED = "Interrupted by user"
LOG_UNEXPECTED_ERROR = "Unexpected ERROR"
LOG_CONNECTIONS_CLOSED = "Connections closed. Program terminated."
LOG_MSG_SYSTEM_STATUS = "SYSTEM STATUS"

# =====================================================
# ----------- TIME CONSTANTS ------------------------
# =====================================================

TIME_SERIAL_WAIT = 2.0
TIME_CAMERA_WARMUP = 0.1
TIME_MAIN_LOOP_SLEEP = 0.05
TIME_STATUS_CHECK = 30

# =====================================================
# ----------- PROCESSING CONSTANTS ------------------
# =====================================================

PROCESSING_SUCCESS = True
PROCESSING_FAIL = False
IMAGE_PREPROCESS_SUCCESS = True
IMAGE_PREPROCESS_FAIL = False