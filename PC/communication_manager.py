import time
from typing import Optional
from udp_comm import UdpComm
from serial_comm import SerialComm
from utils import log_info, log_error, log_warning

class CommunicationManager:
    def __init__(self):
        self.serial = SerialComm()
        self.udp = UdpComm()
        self.active_channel: str = 'NONE'
        self.last_communication_time: float = time.time()
        self.synchronized: bool = False

    def detect_channel(self) -> bool:
        """
        Detect available communication channel with ESP32.
        Prioritizes Serial over UDP.
        """
        log_info("Scanning for available communication channels...")

        # --- Tenta serial ---
        if self.serial.is_available():
            if self.serial.connect():
                self.active_channel = 'SERIAL'
                self.synchronized = True  # Serial não precisa de handshake
                log_info("Using SERIAL communication channel")
                return True

        # --- Tenta UDP ---
        if not self.udp.initialize():
            log_error("Failed to initialize UDP")
            return False

        if not self.udp.discover_peer(timeout=5.0):
            log_error("No UDP peer discovered")
            return False

        if not self.udp.handshake():
            log_error("UDP handshake failed")
            return False

        self.active_channel = 'UDP'
        self.synchronized = True
        log_info(f"Using UDP communication channel with {self.udp.peer_addr}")
        return True

    def send_message(self, message: str) -> bool:
        """Send message via active channel."""
        if not self.synchronized:
            log_warning("Cannot send message - communication not synchronized")
            return False

        self.last_communication_time = time.time()

        if self.active_channel == 'SERIAL':
            return self.serial.send(message)
        elif self.active_channel == 'UDP':
            return self.udp.send(message)
        else:
            log_error("No active channel for sending message")
            return False

    def read_messages(self) -> list:
        """Read messages from active channel."""
        messages = []

        if self.active_channel == 'SERIAL':
            data = self.serial.read()
            if data:
                messages.append(('SERIAL', data))
                self.last_communication_time = time.time()
        elif self.active_channel == 'UDP':
            msg = self.udp.read()
            if msg:
                text, addr = msg
                messages.append(('UDP', text))
                self.last_communication_time = time.time()

        return messages

    def get_channel(self) -> str:
        return self.active_channel

    def is_synchronized(self) -> bool:
        return self.synchronized

    def close_connections(self):
        """Close all connections."""
        self.serial.close()
        self.udp.close()
        self.synchronized = False
        self.active_channel = 'NONE'
        log_info("All communication connections closed")