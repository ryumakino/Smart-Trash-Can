import socket
from config import ESP32Config
from utils import get_logger

logger = get_logger("ESP32_UDP")

class UDPCommunicator:
    def __init__(self, port=ESP32Config.UDP_PORT):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(('', ESP32Config.UDP_PORT))
        self.sock.settimeout(0.5)
        self.port = port

    def send(self, message, ip='255.255.255.255', port=None):
        try:
            self.sock.sendto(message.encode(), (ip, port or self.port))
            logger.debug(f"[UDP] Enviado para {ip}:{port or self.port} -> {message}")
        except Exception as e:
            logger.error(f"[UDP] Erro ao enviar: {e}")

    def receive(self):
        try:
            data, addr = self.sock.recvfrom(1024)
            return data.decode().strip(), addr[0]
        except OSError as e:
            if e.args[0] in (110, 116):
                return None, None
            logger.error(f"[UDP] Erro receive: {e}")
            return None, None
        except Exception as e:
            logger.error(f"[UDP] Erro receive: {e}")
            return None, None
