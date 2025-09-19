# udp_comm_wifi.py
import usocket as socket
import utime as time
import network
from hardware_utils import log_message
from config import WIFI_SSID, WIFI_PASSWORD, WIFI_CONNECTION_TIMEOUT_MS

UDP_PORT = 8888
BUFFER_SIZE = 1024
UDP_TIMEOUT = 0.1  # tempo de espera em segundos

MSG_DISCOVER = "DISCOVER"
MSG_HERE = "HERE"


class UDPComm:
    def __init__(self):
        self.local_ip = "0.0.0.0"
        self.port = UDP_PORT
        self.sock = None
        self.peer_addr = None
        self.initialized = False
        self.wlan = network.WLAN(network.STA_IF)
        self.connected = False

    # -----------------------------
    # Conexão Wi-Fi
    # -----------------------------
    def connect_wifi(self):
        log_message("INFO", "Connecting to Wi-Fi...")
        if not self.wlan.active():
            self.wlan.active(True)
        self.wlan.connect(WIFI_SSID, WIFI_PASSWORD)

        start = time.ticks_ms()
        while not self.wlan.isconnected():
            if time.ticks_diff(time.ticks_ms(), start) > WIFI_CONNECTION_TIMEOUT_MS:
                log_message("ERROR", "Wi-Fi connection timeout")
                return False
            time.sleep_ms(500)

        self.connected = True
        self.local_ip = self.wlan.ifconfig()[0]
        log_message("INFO", f"Wi-Fi connected, IP: {self.local_ip}")
        return True

    def get_ip(self):
        return self.local_ip if self.connected else "0.0.0.0"

    # -----------------------------
    # Inicializa UDP
    # -----------------------------
    def initialize(self):
        log_message("INFO", "Initializing UDPComm...")
        if not self.connect_wifi():
            return False

        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.sock.setblocking(False)
            self.sock.bind((self.local_ip, self.port))
            self.initialized = True
            log_message("INFO", f"UDP initialized on {self.local_ip}:{self.port}")
        except Exception as e:
            log_message("ERROR", f"UDP initialization failed: {e}")
            return False

        # Descobre peer
        self.discover_peer()
        return True

    # -----------------------------
    # Envio e leitura
    # -----------------------------
    def send(self, message: str, addr=None):
        if not self.initialized:
            log_message("ERROR", "UDP not initialized")
            return False
        target = addr if addr else self.peer_addr
        if not target:
            log_message("ERROR", "No target to send UDP message")
            return False
        try:
            self.sock.sendto(message.encode(), target)
            log_message("INFO", f"UDP -> {message} to {target}")
            return True
        except Exception as e:
            log_message("ERROR", f"UDP send failed: {e}")
            return False

    def read(self):
        if not self.initialized:
            return None
        try:
            data, addr = self.sock.recvfrom(BUFFER_SIZE)
            message = data.decode().strip()
            log_message("INFO", f"UDP <- {message} from {addr}")
            return message, addr
        except Exception:
            return None

    # -----------------------------
    # Descoberta de peer
    # -----------------------------
    def discover_peer(self, timeout=5000):
        """Descobre automaticamente o peer na rede (UDP broadcast)"""
        if not self.initialized:
            log_message("ERROR", "UDP not initialized for discovery")
            return False

        end_time = time.ticks_ms() + timeout
        broadcast_addr = ("255.255.255.255", self.port)

        while time.ticks_ms() < end_time and not self.peer_addr:
            self.send(MSG_DISCOVER, broadcast_addr)
            msg = self.read()
            if msg:
                text, addr = msg
                if text == MSG_DISCOVER:
                    # responde ao peer
                    self.send(MSG_HERE, addr)
                elif text == MSG_HERE:
                    self.peer_addr = addr
                    log_message("INFO", f"Peer discovered at {addr}")
                    return True
            time.sleep_ms(200)

        log_message("WARNING", "Peer discovery timeout")
        return False

    # -----------------------------
    # Atualiza IP do PC
    # -----------------------------
    def update_pc_ip(self, ip: str):
        try:
            self.peer_addr = (ip, self.port)
            log_message("INFO", f"PC IP updated to {self.peer_addr}")
            return True
        except Exception as e:
            log_message("ERROR", f"Failed to update PC IP: {e}")
            return False


# Instância global
udp_comm = UDPComm()
