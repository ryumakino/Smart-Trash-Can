from machine import UART
from utils import log_message, blink_led

serial_uart = UART(0, baudrate=115200)

def send_serial_message(message: str) -> bool:
    try:
        serial_uart.write(message + "\n")
        blink_led(1, 50)
        log_message("INFO", f"Serial -> {message}")
        return True
    except Exception as e:
        log_message("ERROR", f"Serial send failed: {e}")
        return False

def read_serial_data() -> str:
    if serial_uart.any():
        try:
            data = serial_uart.read().decode().strip()
            if data:
                log_message("INFO", f"Serial <- {data}")
                return data
        except Exception as e:
            log_message("ERROR", f"Serial read failed: {e}")
    return ""
