import time
from .hardware_utils import log_message

def generate_id() -> str:
    return str(time.ticks_ms())

def deep_sleep(duration_ms: int) -> None:
    try:
        import machine
        machine.deepsleep(duration_ms * 1000)
    except Exception as e:
        log_message("ERROR", f"Deep sleep failed: {e}")

def soft_reset() -> None:
    try:
        import machine
        machine.reset()
    except Exception as e:
        log_message("ERROR", f"Soft reset failed: {e}")

def validate_ip(ip: str) -> bool:
    try:
        parts = ip.split('.')
        if len(parts) != 4:
            return False
        for part in parts:
            if not 0 <= int(part) <= 255:
                return False
        return True
    except:
        return False
