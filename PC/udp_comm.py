import socket
import time
from utils import log_info, log_error, log_warning

UDP_PORT = 8888
BUFFER_SIZE = 1024
UDP_TIMEOUT = 0.1  # segundos

# Mensagens padrão
MSG_DISCOVER = "DISCOVER"
MSG_HERE = "HERE"
MSG_HANDSHAKE = "HANDSHAKE"
MSG_PC_ACK = "PC_ACK"
MSG_SYNCHRONIZED = "SYNCHRONIZED"
MSG_ESP32_READY = "ESP32_READY"


class UdpComm:
    def __init__(self, local_ip=None, port=UDP_PORT, discover_timeout=5, handshake_timeout=5):
        self.local_ip = local_ip
        self.port = port
        self.sock = None
        self.peer_addr = None
        self.synchronized = False
        self.discover_timeout = discover_timeout
        self.handshake_timeout = handshake_timeout
        self.state = "CREATED"  # CREATED → INITIALIZED → DISCOVERED → HANDSHAKED

    # -------------------
    # Detecta IP local
    # -------------------
    def detect_local_ip(self) -> str:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            try:
                s.connect(("8.8.8.8", 80))
                return s.getsockname()[0]
            except Exception:
                return "0.0.0.0"

    # -------------------
    # Inicializa UDP
    # -------------------
    def initialize(self) -> bool:
        if not self.local_ip or self.local_ip == "0.0.0.0":
            self.local_ip = self.detect_local_ip()
            log_info(f"Local IP auto-detected: {self.local_ip}")

        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            self.sock.settimeout(UDP_TIMEOUT)
            self.sock.bind((self.local_ip, self.port))
            log_info(f"UDP initialized on {self.local_ip}:{self.port}")
            self.state = "INITIALIZED"
            return True
        except Exception as e:
            log_error(f"UDP initialization failed: {e}")
            return False

    # -------------------
    # Envia mensagem
    # -------------------
    def send(self, msg: str, addr=None) -> bool:
        target = addr if addr else self.peer_addr
        if not target:
            log_warning(f"No target to send message: {msg}")
            return False
        try:
            self.sock.sendto(msg.encode(), target)
            log_info(f"Sent: {msg} → {target}")
            return True
        except Exception as e:
            log_error(f"Send failed: {e}")
            return False

    # -------------------
    # Lê mensagem
    # -------------------
    def read(self):
        try:
            data, addr = self.sock.recvfrom(BUFFER_SIZE)
            msg = data.decode().strip()
            if addr[0] == self.local_ip:  # ignora mensagens próprias
                return None
            return msg, addr
        except socket.timeout:
            return None
        except Exception as e:
            log_error(f"Read failed: {e}")
            return None

    # -------------------
    # Descobre peers
    # -------------------
    def discover_peer(self, timeout=None) -> bool:
        timeout = timeout if timeout is not None else self.discover_timeout
        log_info("Starting peer discovery...")
        if not self.send(MSG_DISCOVER, ("255.255.255.255", self.port)):
            return False

        start_time = time.time()
        while time.time() - start_time < timeout:
            msg_tuple = self.read()
            if not msg_tuple:
                continue
            msg, addr = msg_tuple

            if msg == MSG_DISCOVER:
                self.send(MSG_HERE, addr)
            elif msg == MSG_HERE:
                log_info(f"Peer discovered at {addr}")
                self.peer_addr = addr
                self.state = "DISCOVERED"
                return True

        log_warning("No peer discovered within timeout")
        return False

    # -------------------
    # Handshake seguro
    # -------------------
    # udp_comm.py - Modificações no handshake
    def handshake(self, timeout=None) -> bool:
        if not self.peer_addr:
            log_error("No peer to handshake")
            return False

        timeout = timeout if timeout is not None else self.handshake_timeout
        log_info("Starting handshake...")

        # Envia mensagem de ready e espera ACK
        self.send(MSG_ESP32_READY)
        start_time = time.time()

        while time.time() - start_time < timeout:
            msg_tuple = self.read()
            if not msg_tuple:
                continue

            msg, addr = msg_tuple
            if addr != self.peer_addr:
                continue  # ignora outros peers

            if msg == MSG_PC_ACK:
                self.send(MSG_SYNCHRONIZED)
                self.synchronized = True
                self.state = "HANDSHAKED"
                log_info("Handshake completed successfully")
                return True
            elif "HERE" in msg:  # Resposta do ESP32 para discovery
                self.peer_addr = addr
                continue

        log_error("Handshake timeout")
        return False

    # -------------------
    # Envia com retry
    # -------------------
    def send_with_retry(self, msg, retries=3, delay=0.5) -> bool:
        for i in range(retries):
            if self.send(msg):
                return True
            log_warning(f"Retry {i+1}/{retries} failed")
            time.sleep(delay)
        return False
