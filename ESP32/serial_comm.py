from machine import UART
from hardware_utils import log_message
from io_utils import blink_led

class SerialComm:
    def __init__(self, uart_id=1, baudrate=115200, timeout=100):
        """
        Initialize UART only once to avoid ESP_ERR_INVALID_STATE.
        Default uses UART1 (safer than UART0).
        """
        try:
            self.uart = UART(uart_id, baudrate=baudrate, timeout=timeout)
            self.initialized = True
            log_message("INFO", f"Serial UART{uart_id} initialized at {baudrate}bps")
        except Exception as e:
            self.uart = None
            self.initialized = False
            log_message("ERROR", f"Serial UART{uart_id} initialization failed: {e}")

    def send_message(self, message: str) -> bool:
        try:
            if self.initialized and self.uart:
                self.uart.write(message + "\n")
                blink_led(1, 50)
                log_message("INFO", f"Serial -> {message}")
                return True
            else:
                log_message("WARNING", "Serial not initialized, cannot send")
                return False
        except Exception as e:
            log_message("ERROR", f"Serial send failed: {e}")
            return False

    def read_data(self) -> str:
        try:
            if self.initialized and self.uart and self.uart.any():
                data = self.uart.read().decode().strip()
                if data:
                    log_message("INFO", f"Serial <- {data}")
                    return data
        except Exception as e:
            log_message("ERROR", f"Serial read failed: {e}")
        return ""

# Instância global
serial_comm = SerialComm()
