from datetime import datetime

def log_message(prefix: str, message: str):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] [{prefix}] {message}")

def log_info(message: str):
    log_message("INFO", message)

def log_error(message: str):
    log_message("ERROR", message)

def log_warning(message: str):
    log_message("WARNING", message)

def log_success(message: str):
    log_message("SUCCESS", message)

def log_debug(message: str):
    log_message("DEBUG", message)

def log_camera(message: str):
    log_message("CAMERA", message)
