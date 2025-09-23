from machine import UART
import time
from config import ESP32Config
from utils import get_logger

logger = get_logger("Serial")

class SerialCommunicator:
    def __init__(self):
        self.uart = UART(ESP32Config.UART_PORT, ESP32Config.UART_BAUD)
        self.uart.init(baudrate=ESP32Config.UART_BAUD, timeout=1000)
        logger.info("Serial inicializada")
    
    def send(self, message):
        """Envia mensagem pela serial"""
        try:
            self.uart.write(message + '\n')
            return True
        except Exception as e:
            logger.error(f"Erro serial send: {e}")
            return False
    
    def receive(self):
        """Recebe mensagem da serial"""
        if self.uart.any():
            try:
                data = self.uart.readline().decode().strip()
                return data
            except:
                pass
        return None