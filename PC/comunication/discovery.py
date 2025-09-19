import socket
import threading
from config import DISCOVERY_PORT, BROADCAST_IP
from utils import log_info, log_error

class Discovery:
    def __init__(self):
        self.pc_ip = None
        self.esp_ip = None
        self.listener_thread = None
        self.listener_running = False

    def discover_local_ip(self):
        """Discover the local IP address of this PC"""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            self.pc_ip = s.getsockname()[0]
            s.close()
            log_info(f"PC Local IP: {self.pc_ip}")
            return self.pc_ip
        except Exception as e:
            log_error(f"Failed to discover local IP: {e}")
            return None

    def _listener_thread(self):
        """Thread function to listen for discovery requests"""
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(("", DISCOVERY_PORT))
        sock.settimeout(1.0)  # Timeout para não bloquear indefinidamente
        
        log_info(f"Discovery listener active on port {DISCOVERY_PORT}")

        while self.listener_running:
            try:
                data, addr = sock.recvfrom(1024)
                message = data.decode().strip()
                log_info(f"Received {message} from {addr}")

                if message == "DISCOVER_ESP32_REQUEST":
                    response = "DISCOVER_PC_RESPONSE"
                    sock.sendto(response.encode(), addr)
                    log_info(f"Sent discovery response to {addr}")
                    self.esp_ip = addr[0]
            except socket.timeout:
                continue
            except Exception as e:
                log_error(f"Discovery listener error: {e}")
                break
        
        sock.close()
        log_info("Discovery listener stopped")

    def start_listener(self):
        """Start the discovery listener in a separate thread"""
        if self.listener_running:
            return
            
        self.listener_running = True
        self.listener_thread = threading.Thread(target=self._listener_thread, daemon=True)
        self.listener_thread.start()
        log_info("Discovery listener thread started")

    def stop_listener(self):
        """Stop the discovery listener"""
        self.listener_running = False
        if self.listener_thread and self.listener_thread.is_alive():
            self.listener_thread.join(timeout=2.0)
        log_info("Discovery listener stopped")

    def get_esp_ip(self):
        """Get the discovered ESP32 IP address"""
        return self.esp_ip