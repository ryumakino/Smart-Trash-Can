import time
from machine import Pin
from config import LED_PIN
from hardware_utils import log_message

def blink_led(times: int = 3, delay: int = 200) -> None:
    try:
        led = Pin(LED_PIN, Pin.OUT)
        for _ in range(times):
            led.on()
            time.sleep_ms(delay)
            led.off()
            time.sleep_ms(delay)
    except Exception as e:
        log_message("ERROR", f"LED blink failed: {e}")

def debounce_movement() -> bool:
    # Fallback function
    return False

def set_movement_detected() -> None:
    # Placeholder, logic moved to sensor.py
    pass
