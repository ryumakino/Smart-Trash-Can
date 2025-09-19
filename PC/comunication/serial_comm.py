import serial, time, serial.tools.list_ports
from utils import log_info, log_error
from config import SERIAL_PORT, SERIAL_BAUDRATE, SERIAL_TIMEOUT, TIME_SERIAL_WAIT

class SerialComm:
    def __init__(self):
        self.conn = None

    def is_available(self):
        try:
            for port in serial.tools.list_ports.comports():
                if "ESP32" in port.description.upper():
                    return True
        except Exception as e:
            log_error(f"Serial detection error: {e}")
        return False

    def connect(self):
        try:
            self.conn = serial.Serial(SERIAL_PORT, SERIAL_BAUDRATE, timeout=SERIAL_TIMEOUT)
            time.sleep(TIME_SERIAL_WAIT)
            log_info(f"Serial connected at {SERIAL_PORT}")
            return True
        except Exception as e:
            log_error(f"Serial connection failed: {e}")
            return False

    def send(self, message):
        if self.conn:
            self.conn.write(f"{message}\n".encode())
            return True
        return False

    def read(self):
        if self.conn and self.conn.in_waiting > 0:
            return self.conn.readline().decode(errors="ignore").strip()
        return None

    def close(self):
        if self.conn and self.conn.is_open:
            self.conn.close()
            log_info("Serial closed")
