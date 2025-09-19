# serial_comm.py
from machine import UART
from hardware_utils import log_message

class SerialComm:
    def __init__(self, uart_id=1, baudrate=115200, timeout=100):
        self.initialized = False
        try:
            self.uart = UART(uart_id, baudrate=baudrate, timeout=timeout)
            self.initialized = True
            log_message("INFO", f"Serial UART{uart_id} initialized at {baudrate}bps")
        except Exception as e:
            self.uart = None
            log_message("ERROR", f"Serial UART{uart_id} initialization failed: {e}")
    def send(self, msg: str):
        self.uart.write(msg + "\n")
    
    def read(self):
        if self.uart.any():
            return self.uart.read().decode().strip()
        return None

serial_comm = SerialComm()
