# Correção da importação circular
try:
    from discovery import Discovery
    from serial_comm import SerialComm
    from udp_comm import UdpComm
except ImportError:
    from .discovery import Discovery
    from .serial_comm import SerialComm
    from .udp_comm import UdpComm

from utils import log_info, log_error, log_warning
import time

class CommunicationManager:
    def __init__(self):
        self.discovery = Discovery()
        self.serial = SerialComm()
        self.udp = None
        self.esp_ip = None
        self.active_channel = 'NONE'
        self.last_communication_time = time.time()

    def detect_channel(self):
        """Detect available communication channel with ESP32"""
        # Descobre IP local primeiro
        self.discovery.discover_local_ip()
        
        # Inicia listener para descoberta
        self.discovery.start_listener()
        
        log_info("Scanning for available communication channels...")
        
        # Tenta conexão serial primeiro
        if self.serial.is_available():
            if self.serial.connect():
                self.active_channel = 'SERIAL'
                self.esp_ip = 'SERIAL'
                log_info("Using SERIAL communication channel")
                return True
        
        # Tenta descobrir ESP32 via rede
        log_info("Waiting for ESP32 discovery...")
        for _ in range(5):  # Espera por 5 segundos
            time.sleep(1)
            self.esp_ip = self.discovery.get_esp_ip()
            if self.esp_ip:
                break
        
        if self.esp_ip:
            # Tenta conectar via UDP
            self.udp = UdpComm(self.discovery.pc_ip, self.esp_ip)
            if self.udp.connect():
                self.active_channel = 'UDP'
                log_info(f"Using UDP communication channel with ESP32 at {self.esp_ip}")
                return True
        
        log_error("No communication channel available")
        return False

    def send_message(self, message):
        """Send message via active channel"""
        self.last_communication_time = time.time()
        
        if self.active_channel == 'SERIAL':
            return self.serial.send(message)
        elif self.active_channel == 'UDP' and self.udp:
            return self.udp.send(message)
        else:
            log_error("No active channel for sending message")
            return False

    def read_messages(self):
        """Read messages from active channel"""
        messages = []
        
        if self.active_channel == 'SERIAL':
            data = self.serial.read()
            if data:
                messages.append(('SERIAL', data))
                self.last_communication_time = time.time()
                
        elif self.active_channel == 'UDP' and self.udp:
            data = self.udp.read()
            if data:
                messages.append(('UDP', data))
                self.last_communication_time = time.time()
        
        return messages

    def get_esp32_channel(self):
        """Get current ESP32 communication channel"""
        return self.active_channel

    def get_esp32_ip(self):
        """Get ESP32 IP address (if using UDP)"""
        return self.esp_ip if self.active_channel == 'UDP' else 'N/A'

    def close_connections(self):
        """Close all connections"""
        self.discovery.stop_listener()
        self.serial.close()
        if self.udp:
            self.udp.close()
        log_info("All communication connections closed")