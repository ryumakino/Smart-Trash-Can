import socket
import select
from utils import log_info, log_error
from config import UDP_TIMEOUT, UDP_PORT, BUFFER_SIZE

class UdpComm:
    def __init__(self, pc_ip, esp_ip):
        self.sock = None
        self.pc_ip = pc_ip
        self.esp_ip = esp_ip
        self.port = UDP_PORT

    def connect(self):
        """Connect UDP socket"""
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.sock.settimeout(UDP_TIMEOUT)
            self.sock.bind((self.pc_ip, self.port))
            log_info(f"UDP bound at {self.pc_ip}:{self.port}")
            log_info(f"Target ESP32: {self.esp_ip}:{self.port}")
            return True
        except Exception as e:
            log_error(f"UDP initialization error: {e}")
            return False

    def send(self, message):
        """Send message via UDP"""
        if self.sock:
            try:
                target = (self.esp_ip, self.port)
                self.sock.sendto(message.encode(), target)
                log_info(f"UDP -> {message} to {target}")
                return True
            except Exception as e:
                log_error(f"UDP send error: {e}")
                return False
        return False

    def read(self):
        """Read data from UDP with proper timeout"""
        if not self.sock:
            return None
            
        try:
            # Usar select para verificar se há dados disponíveis
            ready, _, _ = select.select([self.sock], [], [], 0.1)
            if ready:
                data, addr = self.sock.recvfrom(BUFFER_SIZE)
                if data:
                    message = data.decode().strip()
                    log_info(f"UDP <- {message} from {addr}")
                    return message
        except socket.timeout:
            pass
        except Exception as e:
            log_error(f"UDP read error: {e}")
        
        return None

    def close(self):
        """Close UDP socket"""
        if self.sock:
            self.sock.close()
            self.sock = None
            log_info("UDP connection closed")