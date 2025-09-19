import serial
import time
import serial.tools.list_ports
from utils import log_info, log_error
from config import SERIAL_PORT, SERIAL_BAUDRATE, SERIAL_TIMEOUT, TIME_SERIAL_WAIT

class SerialComm:
    def __init__(self):
        self.conn = None
        self.port_name = None

    def is_available(self):
        """Check if serial port with ESP32 is available"""
        try:
            ports = serial.tools.list_ports.comports()
            for port in ports:
                if "ESP32" in port.description.upper() or "USB" in port.description.upper():
                    self.port_name = port.device
                    log_info(f"Found potential ESP32 port: {port.device} - {port.description}")
                    return True
            log_info("No ESP32 serial port found")
            return False
        except Exception as e:
            log_error(f"Serial detection error: {e}")
            return False

    def connect(self):
        """Connect to the serial port"""
        try:
            if not self.port_name:
                if not self.is_available():
                    return False
                    
            self.conn = serial.Serial(
                self.port_name or SERIAL_PORT, 
                SERIAL_BAUDRATE, 
                timeout=SERIAL_TIMEOUT
            )
            time.sleep(TIME_SERIAL_WAIT)
            log_info(f"Serial connected at {self.conn.port}")
            return True
        except Exception as e:
            log_error(f"Serial connection failed: {e}")
            return False

    def send(self, message):
        """Send message via serial"""
        if self.conn and self.conn.is_open:
            try:
                self.conn.write(f"{message}\n".encode())
                log_info(f"Serial -> {message}")
                return True
            except Exception as e:
                log_error(f"Serial send failed: {e}")
                return False
        return False

    def read(self):
        """Read data from serial"""
        if self.conn and self.conn.is_open and self.conn.in_waiting > 0:
            try:
                data = self.conn.readline().decode(errors="ignore").strip()
                if data:
                    log_info(f"Serial <- {data}")
                    return data
            except Exception as e:
                log_error(f"Serial read error: {e}")
        return None

    def close(self):
        """Close serial connection"""
        if self.conn and self.conn.is_open:
            self.conn.close()
            log_info("Serial connection closed")