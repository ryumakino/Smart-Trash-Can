import os
import time
import socket
import select
import serial
import serial.tools.list_ports
from config import *
from utils import log_message, log_error, log_info, log_success

class CommunicationManager:
    """ESP32 Communication Manager"""

    def __init__(self):
        self.serial_conn = None
        self.udp_socket = None
        self.last_communication_time = 0
        self.esp32_channel = CHANNEL_NONE

    # -------------------------
    # Initialization
    # -------------------------
    def initialize_serial(self):
        try:
            self.serial_conn = serial.Serial(SERIAL_PORT, SERIAL_BAUDRATE, timeout=SERIAL_TIMEOUT)
            time.sleep(TIME_SERIAL_WAIT)
            log_info(f"Connected via Serial: {SERIAL_PORT} ({SERIAL_BAUDRATE} baud)")
            return PROCESSING_SUCCESS
        except Exception as e:
            log_error(f"Failed to connect via Serial {SERIAL_PORT}: {e}")
            self.serial_conn = None
            return PROCESSING_FAIL

    def initialize_udp(self):
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
    def detect_esp32_channel(self):
        # Wi-Fi test
        if IS_WINDOWS:
            ping_cmd = f"ping -n {PING_COUNT} -w {PING_TIMEOUT} {ESP_IP}"
        else:
            ping_cmd = f"ping -c {PING_COUNT} -W {PING_TIMEOUT // 1000} {ESP_IP}"
        
        wifi_available = os.system(ping_cmd) == 0
        log_message("✅" if wifi_available else "❌", 
                    f"ESP32 {'connected' if wifi_available else 'not found'} on network: {ESP_IP}")

        # Serial test
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

        # Set active channel
        if serial_available:
            if self.initialize_serial():
                self.esp32_channel = CHANNEL_SERIAL
                return PROCESSING_SUCCESS
        elif wifi_available:
            if self.initialize_udp():
                self.esp32_channel = CHANNEL_UDP
                return PROCESSING_SUCCESS
        
        log_error(MSG_ESP32_NOT_FOUND)
        self.esp32_channel = CHANNEL_NONE
        return PROCESSING_FAIL

    # -------------------------
    # Communication
    # -------------------------
    def send_message(self, message):
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

    def _send_serial(self, message):
        try:
            self.serial_conn.write(f"{message}\n".encode())
            self.last_communication_time = time.time()
            log_message(LOG_PREFIX_SERIAL, message)
            return PROCESSING_SUCCESS
        except Exception as e:
            log_error(f"Error sending via Serial: {e}")
            return PROCESSING_FAIL

    def _send_udp(self, message):
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
    def read_messages(self):
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

    def _read_serial(self):
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

    def _read_udp(self):
        try:
            rlist, _, _ = select.select([self.udp_socket], [], [], 0.1)
            for s in rlist:
                data, addr = s.recvfrom(BUFFER_SIZE)
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
    def get_esp32_channel(self):
        return self.esp32_channel

    def close_connections(self):
        if self.serial_conn and self.serial_conn.is_open:
            self.serial_conn.close()
            log_info("Serial connection closed")
        if self.udp_socket:
            self.udp_socket.close()
            log_info("UDP connection closed")

# Global instance
comm_manager = CommunicationManager()

def initialize_connections():
    log_message(LOG_PREFIX_SYSTEM, "Initializing connections...")
    if comm_manager.detect_esp32_channel():
        log_success(f"ESP32 responding via channel: {comm_manager.get_esp32_channel()}")
        log_success("Connection initialized")
        return PROCESSING_SUCCESS
    return PROCESSING_FAIL