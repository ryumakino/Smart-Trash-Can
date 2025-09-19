from .discovery import Discovery
from .serial_comm import SerialComm
from .udp_comm import UdpComm
from utils import log_error

class CommunicationManager:
    def __init__(self):
        self.discovery = Discovery()
        self.serial = SerialComm()
        self.udp = None
        self.esp_ip = None

    def detect_channel(self):
        self.esp_ip = self.discovery.discover_esp32_ip()
        if not self.esp_ip:
            log_error("ESP32 not found")
            return False

        if self.serial.is_available() and self.serial.connect():
            return True

        udp = UdpComm(self.discovery.pc_ip, self.esp_ip)
        if udp.connect():
            self.udp = udp
            return True

        log_error("No channel available")
        return False

    def send(self, message):
        if self.serial and self.serial.conn:
            return self.serial.send(message)
        elif self.udp:
            return self.udp.send(message)
        return False

    def read(self):
        if self.serial and self.serial.conn:
            return self.serial.read()
        elif self.udp:
            return self.udp.read()
        return None

    def close(self):
        if self.serial.conn:
            self.serial.close()
        if self.udp:
            self.udp.close()