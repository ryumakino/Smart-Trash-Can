from datetime import datetime
import sys

class Logger:
    def __init__(self):
        self.colors = {
            'INFO': '\033[94m',      # Azul
            'SUCCESS': '\033[92m',   # Verde
            'WARNING': '\033[93m',   # Amarelo
            'ERROR': '\033[91m',     # Vermelho
            'DEBUG': '\033[90m',     # Cinza
            'CAMERA': '\033[95m',    # Magenta
            'RESET': '\033[0m'       # Reset
        }
    
    def log_message(self, prefix: str, message: str, color: str = None):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        if color and sys.stdout.isatty():  # Verifica se é terminal
            colored_prefix = f"{color}[{prefix}]{self.colors['RESET']}"
            print(f"[{timestamp}] {colored_prefix} {message}")
        else:
            print(f"[{timestamp}] [{prefix}] {message}")

logger = Logger()

def log_message(prefix: str, message: str):
    logger.log_message(prefix, message)

def log_info(message: str):
    logger.log_message("INFO", message, logger.colors['INFO'])

def log_error(message: str):
    logger.log_message("ERROR", message, logger.colors['ERROR'])

def log_warning(message: str):
    logger.log_message("WARNING", message, logger.colors['WARNING'])

def log_success(message: str):
    logger.log_message("SUCCESS", message, logger.colors['SUCCESS'])

def log_debug(message: str):
    logger.log_message("DEBUG", message, logger.colors['DEBUG'])

def log_camera(message: str):
    logger.log_message("CAMERA", message, logger.colors['CAMERA'])