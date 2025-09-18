import os
import time
import socket
import select
import serial
import serial.tools.list_ports
from typing import Optional, List, Tuple
from config import (
    SERIAL_PORT, SERIAL_BAUDRATE, SERIAL_TIMEOUT, TIME_SERIAL_WAIT,
    PROCESSING_SUCCESS, PROCESSING_FAIL, CHANNEL_NONE, CHANNEL_SERIAL, CHANNEL_UDP,
    UDP_TIMEOUT, PC_IP, UDP_PORT, PING_COUNT, PING_TIMEOUT, ESP_IP, IS_WINDOWS,
    MSG_ESP32_NOT_FOUND, MAX_RETRIES, MSG_NO_CHANNEL, LOG_PREFIX_SERIAL, LOG_PREFIX_UDP,
    BUFFER_SIZE, LOG_PREFIX_SYSTEM
)
from utils import log_message, log_error, log_info, log_success, log_warning

class CommunicationManager:
    """ESP32 Communication Manager"""

    def __init__(self) -> None:
        """Initialize communication manager with default values."""
        self.serial_conn: Optional[serial.Serial] = None
        self.udp_socket: Optional[socket.socket] = None
        self.last_communication_time: float = 0.0
        self.esp32_channel: str = CHANNEL_NONE

    # -------------------------
    # Initialization
    # -------------------------

    def initialize_serial(self) -> bool:
        """
        Initialize serial connection.
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            self.serial_conn = serial.Serial(
                SERIAL_PORT, 
                SERIAL_BAUDRATE, 
                timeout=SERIAL_TIMEOUT
            )
            time.sleep(TIME_SERIAL_WAIT)
            log_info(f"Connected via Serial: {SERIAL_PORT} ({SERIAL_BAUDRATE} baud)")
            return PROCESSING_SUCCESS
        except Exception as e:
            log_error(f"Failed to connect via Serial {SERIAL_PORT}: {e}")
            self.serial_conn = None
            return PROCESSING_FAIL

    def initialize_udp(self) -> bool:
        """
        Initialize UDP socket.
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.udp_socket.settimeout(UDP_TIMEOUT)
            self.udp_socket.bind((PC_IP, UDP_PORT))
            log_info(f"UDP socket initialized at {PC_IP}:{UDP_PORT}")
            return PROCESSING_SUCCESS
        except Exception as e:
            log_error(f"Failed to initialize UDP: {e}")
            self.udp_socket = None
            return PROCESSING_FAIL

    # -------------------------
    # Channel Detection
    # -------------------------

    def detect_esp32_channel(self) -> bool:
        """
        Detect available ESP32 communication channel.
        
        Returns:
            bool: True if channel detected, False otherwise
        """
        wifi_available = self._is_wifi_available()
        serial_available = self._is_serial_available()

        # Set active channel
        if serial_available and self.initialize_serial():
            self.esp32_channel = CHANNEL_SERIAL
            return PROCESSING_SUCCESS
        elif wifi_available and self.initialize_udp():
            self.esp32_channel = CHANNEL_UDP
            return PROCESSING_SUCCESS
        
        log_error(MSG_ESP32_NOT_FOUND)
        self.esp32_channel = CHANNEL_NONE
        return PROCESSING_FAIL

    def _is_wifi_available(self) -> bool:
        """Check if ESP32 is available via Wi-Fi."""
        if IS_WINDOWS:
            ping_cmd = f"ping -n {PING_COUNT} -w {PING_TIMEOUT} {ESP_IP}"
        else:
            ping_cmd = f"ping -c {PING_COUNT} -W {PING_TIMEOUT // 1000} {ESP_IP}"
        wifi_available = os.system(ping_cmd) == 0
        log_message("✅" if wifi_available else "❌", 
                    f"ESP32 {'connected' if wifi_available else 'not found'} on network: {ESP_IP}")
        return wifi_available

    def _is_serial_available(self) -> bool:
        """Check if ESP32 is available via Serial."""
        serial_available = False
        try:
            for port in serial.tools.list_ports.comports():
                if "ESP32" in port.description.upper() or "USB SERIAL" in port.description.upper():
                    serial_available = True
                    break
            log_message("✅" if serial_available else "❌", 
                        f"ESP32 {'detected' if serial_available else 'not found'} via Serial")
        except Exception as e:
            log_error(f"Error checking serial ports: {e}")
        return serial_available

    # -------------------------
    # Communication
    # -------------------------

    def send_message(self, message: str) -> bool:
        """
        Send message to ESP32 via available channel.
        
        Args:
            message: Message to send
            
        Returns:
            bool: True if successful, False otherwise
        """
        success = False

        for attempt in range(MAX_RETRIES):
            if self.serial_conn and self.serial_conn.is_open:
                success = self._send_serial(message)
            elif self.udp_socket:
                success = self._send_udp(message)

            if success:
                break
            else:
                log_warning(f"Attempt {attempt+1}/{MAX_RETRIES} failed")

        if not success:
            log_warning(f"{MSG_NO_CHANNEL}: {message}")
        return success

    def _send_serial(self, message: str) -> bool:
        """
        Send message via serial connection.
        
        Args:
            message: Message to send
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            self.serial_conn.write(f"{message}\n".encode())
            self.last_communication_time = time.time()
            log_message(LOG_PREFIX_SERIAL, message)
            return PROCESSING_SUCCESS
        except Exception as e:
            log_error(f"Error sending via Serial: {e}")
            return PROCESSING_FAIL

    def _send_udp(self, message: str) -> bool:
        """
        Send message via UDP.
        
        Args:
            message: Message to send
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            self.udp_socket.sendto(message.encode(), (ESP_IP, UDP_PORT))
            self.last_communication_time = time.time()
            log_message(LOG_PREFIX_UDP, f"{message} to {ESP_IP}:{UDP_PORT}")
            return PROCESSING_SUCCESS
        except Exception as e:
            log_error(f"Error sending via UDP: {e}")
            return PROCESSING_FAIL

    # -------------------------
    # Reading
    # -------------------------

    def read_messages(self) -> List[Tuple[str, str]]:
        """
        Read messages from all available channels.
        
        Returns:
            List[Tuple[str, str]]: List of (channel, message) tuples
        """
        messages = []

        if self.serial_conn:
            msg = self._read_serial()
            if msg: 
                messages.append((CHANNEL_SERIAL, msg))
        
        if self.udp_socket:
            msg = self._read_udp()
            if msg: 
                messages.append((CHANNEL_UDP, msg))

        return messages

    def _read_serial(self) -> Optional[str]:
        """
        Read message from serial connection.
        
        Returns:
            Optional[str]: Received message or None
        """
        try:
            if self.serial_conn.in_waiting > 0:
                data = self.serial_conn.readline()
                msg = data.decode(errors='ignore').strip()
                if msg:
                    self.last_communication_time = time.time()
                    return msg
        except Exception as e:
            log_error(f"Error reading Serial: {e}")
        return None

    def _read_udp(self) -> Optional[str]:
        """
        Read message from UDP socket.
        
        Returns:
            Optional[str]: Received message or None
        """
        try:
            rlist, _, _ = select.select([self.udp_socket], [], [], 0.1)
            for s in rlist:
                data, _ = s.recvfrom(BUFFER_SIZE)
                msg = data.decode().strip()
                if msg:
                    self.last_communication_time = time.time()
                    return msg
        except socket.timeout:
            pass
        except Exception as e:
            log_error(f"Error reading UDP: {e}")
        return None

    # -------------------------
    # Utilities
    # -------------------------

    def get_esp32_channel(self) -> str:
        """
        Get current ESP32 communication channel.
        
        Returns:
            str: Current channel name
        """
        return self.esp32_channel

    def close_connections(self) -> None:
        """Close all active connections."""
        if self.serial_conn and self.serial_conn.is_open:
            self.serial_conn.close()
            log_info("Serial connection closed")
        if self.udp_socket:
            self.udp_socket.close()
            log_info("UDP connection closed")

# Global instance
comm_manager = CommunicationManager()

def initialize_connections() -> bool:
    """
    Initialize all connections to ESP32.
    
    Returns:
        bool: True if successful, False otherwise
    """
    log_message(LOG_PREFIX_SYSTEM, "Initializing connections...")
    if comm_manager.detect_esp32_channel():
        log_success(f"ESP32 responding via channel: {comm_manager.get_esp32_channel()}")
        log_success("Connection initialized")
        return PROCESSING_SUCCESS
    return PROCESSING_FAIL