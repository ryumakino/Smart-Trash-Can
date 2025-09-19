from machine import Pin
from config import LED_PIN

def log_message(level: str, message: str) -> None:
    print(f"[{level}] {message}")

def get_free_memory() -> int:
    try:
        import gc
        gc.collect()
        return gc.mem_free()
    except Exception as e:
        log_message("ERROR", f"Memory check failed: {e}")
        return 0

def get_cpu_freq() -> int:
    try:
        import esp
        return esp.freq()[0] // 1000000
    except Exception as e:
        log_message("ERROR", f"CPU freq check failed: {e}")
        return 80

def get_temperature() -> float:
    try:
        import esp32
        return (esp32.raw_temperature() - 32) / 1.8
    except ImportError:
        log_message("WARNING", "esp32 module not available for temperature reading")
        return 0.0
    except Exception as e:
        log_message("ERROR", f"Temperature reading failed: {e}")
        return 0.0

def is_hardware_initialized() -> bool:
    try:
        led = Pin(LED_PIN, Pin.OUT)
        led.on()
        led.off()
        return True
    except Exception as e:
        log_message("ERROR", f"Hardware check failed: {e}")
        return False

def format_bytes(size_bytes: int) -> str:
    if size_bytes >= 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    elif size_bytes >= 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes} B"
