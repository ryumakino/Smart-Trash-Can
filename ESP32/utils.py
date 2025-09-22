import time
import sys

class Logger:
    def __init__(self):
        self.start_time = time.time()
    
    def _get_timestamp(self):
        uptime = time.time() - self.start_time
        return f"[{uptime:07.1f}s]"
    
    def log(self, level, message):
        timestamp = self._get_timestamp()
        print(f"{timestamp} [{level}] {message}")
        
        # Flush para garantir que logs aparecem imediatamente
        sys.stdout.flush()

logger = Logger()

def log_info(message):
    logger.log("INFO", message)

def log_error(message):
    logger.log("ERROR", message)

def log_success(message):
    logger.log("SUCCESS", message)

def log_warning(message):
    logger.log("WARNING", message)

def log_debug(message):
    logger.log("DEBUG", message)

def log_hardware(message):
    logger.log("HARDWARE", message)