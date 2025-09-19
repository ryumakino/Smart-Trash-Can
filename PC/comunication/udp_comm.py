import socket, select
from utils import log_info, log_error
from config import UDP_TIMEOUT, UDP_PORT, BUFFER_SIZE

class UdpComm:
    def __init__(self, pc_ip, esp_ip):
        self.sock = None
        self.pc_ip = pc_ip
        self.esp_ip = esp_ip

    def connect(self):
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.sock.settimeout(UDP_TIMEOUT)
            self.sock.bind((self.pc_ip, UDP_PORT))
            log_info(f"UDP bound at {self.pc_ip}:{UDP_PORT}")
            return True
        except Exception as e:
            log_error(f"UDP init error: {e}")
            return False

    def send(self, message):
        if self.sock:
            self.sock.sendto(message.encode(), (self.esp_ip, UDP_PORT))
            return True
        return False

    def read(self):
        try:
            rlist, _, _ = select.select([self.sock], [], [], 0.1)
            for s in rlist:
                data, _ = s.recvfrom(BUFFER_SIZE)
                return data.decode().strip()
        except Exception:
            return None
        return None

    def close(self):
        if self.sock:
            self.sock.close()
            log_info("UDP closed")
