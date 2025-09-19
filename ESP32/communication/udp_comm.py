import socket
import _thread
import time
from utils import log_message, blink_led, validate_ip
from config import UDP_PORT, DISCOVERY_PORT

class UDPComm:
    def __init__(self):
        self.udp_socket = None
        self.discovery_sock = None
        self.discovery_running = False
        self.pc_ip_address = None
        self.initialized = False

    def initialize(self):
        """Initialize UDP socket"""
        try:
            self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.udp_socket.setblocking(False)
            self.initialized = True
            log_message("INFO", "UDP communication initialized")
            return True
        except Exception as e:
            log_message("ERROR", f"UDP initialization failed: {e}")
            return False

    def _process_discovery_message(self, message, addr, discovery_sock):
        """Process a discovery message"""
        if message.startswith("DISCOVER_ESP32"):
            if "PC_IP:" in message:
                parts = message.split(":")
                if len(parts) >= 3:
                    received_pc_ip = parts[2]
                    if validate_ip(received_pc_ip):
                        self.pc_ip_address = received_pc_ip
                        log_message("INFO", f"Updated PC IP from discovery: {self.pc_ip_address}")

            # Responde com confirmação
            response_msg = "ESP32_RESPONSE:PC_IP_RECEIVED"
            discovery_sock.sendto(response_msg.encode(), addr)
            log_message("INFO", f"Discovery request from {addr[0]}, PC IP: {self.pc_ip_address}")
            blink_led(2, 100)

    def _handle_discovery(self):
        """Handle discovery requests"""
        self.discovery_running = True
        try:
            self.discovery_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.discovery_sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            self.discovery_sock.bind(('0.0.0.0', DISCOVERY_PORT))
            self.discovery_sock.settimeout(1.0)

            log_message("INFO", f"Discovery service started on port {DISCOVERY_PORT}")

            while self.discovery_running:
                try:
                    data, addr = self.discovery_sock.recvfrom(1024)
                    message = data.decode().strip()
                    self._process_discovery_message(message, addr, self.discovery_sock)
                except socket.timeout:
                    continue
                except Exception as e:
                    log_message("ERROR", f"Discovery error: {e}")
                    time.sleep(1)

        except Exception as e:
            log_message("ERROR", f"Discovery handler failed: {e}")
        finally:
            if self.discovery_sock:
                self.discovery_sock.close()
            self.discovery_running = False

    def start_discovery_service(self):
        """Start discovery service"""
        try:
            _thread.start_new_thread(self._handle_discovery, ())
            log_message("INFO", "Discovery service thread started")
            return True
        except Exception as e:
            log_message("ERROR", f"Failed to start discovery thread: {e}")
            return False

    def stop_discovery_service(self):
        """Stop discovery service"""
        self.discovery_running = False
        log_message("INFO", "Discovery service stopped")

    def get_pc_ip(self) -> str:
        """Get current PC IP address"""
        return self.pc_ip_address

    def update_pc_ip(self, new_ip: str) -> bool:
        """Update PC IP address"""
        if validate_ip(new_ip):
            self.pc_ip_address = new_ip
            log_message("INFO", f"PC IP updated to: {self.pc_ip_address}")
            return True
        return False

    def send_message(self, message: str) -> bool:
        """Send message via UDP"""
        try:
            if not self.initialized:
                self.initialize()
                
            if not validate_ip(self.pc_ip_address):
                log_message("ERROR", f"Invalid PC IP: {self.pc_ip_address}")
                return False
            
            addr = (self.pc_ip_address, UDP_PORT)
            self.udp_socket.sendto(message.encode(), addr)
            blink_led(1, 50)
            log_message("INFO", f"UDP -> {message} to {addr}")
            return True
        except Exception as e:
            log_message("ERROR", f"UDP send failed: {e}")
            return False

    def read_data(self) -> str:
        """Read data from UDP"""
        try:
            if not self.initialized:
                self.initialize()
                
            data, addr = self.udp_socket.recvfrom(1024)
            if data:
                message = data.decode().strip()
                blink_led(1, 50)
                log_message("INFO", f"UDP <- {message} from {addr[0]}")
                
                # Atualiza IP do PC se necessário
                if addr[0] != self.pc_ip_address and validate_ip(addr[0]):
                    self.update_pc_ip(addr[0])
                    
                return message
        except OSError:
            pass
        except Exception as e:
            log_message("ERROR", f"UDP read failed: {e}")
        return ""

# Instância global
udp_comm = UDPComm()