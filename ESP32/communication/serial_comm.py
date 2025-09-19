from machine import UART
from utils import log_message, blink_led

class SerialComm:
    def __init__(self):
        self.uart = UART(0, baudrate=115200)
        self.initialized = False

    def initialize(self):
        """Initialize serial communication"""
        try:
            self.uart.init(baudrate=115200, timeout=100)
            self.initialized = True
            log_message("INFO", "Serial communication initialized")
            return True
        except Exception as e:
            log_message("ERROR", f"Serial initialization failed: {e}")
            return False

    def send_message(self, message: str) -> bool:
        """Send message via serial"""
        try:
            if not self.initialized:
                self.initialize()
                
            self.uart.write(message + "\n")
            blink_led(1, 50)
            log_message("INFO", f"Serial -> {message}")
            return True
        except Exception as e:
            log_message("ERROR", f"Serial send failed: {e}")
            return False

    def read_data(self) -> str:
        """Read data from serial"""
        try:
            if self.uart.any():
                data = self.uart.read().decode().strip()
                if data:
                    log_message("INFO", f"Serial <- {data}")
                    return data
        except Exception as e:
            log_message("ERROR", f"Serial read failed: {e}")
        return ""

# Instância global
serial_comm = SerialComm()