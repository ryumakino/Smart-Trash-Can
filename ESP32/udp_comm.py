import socket
import _thread
import time
from hardware_utils import log_message
from io_utils import blink_led
from system_utils import validate_ip
from config import UDP_PORT, DISCOVERY_PORT, BROADCAST_IP, MSG_DISCOVERY

class UDPComm:
    def __init__(self):
        self.udp_socket = None
        self.discovery_sock = None
        self.discovery_running = False
        self.pc_ip_address = None
        self.initialized = False
        self.last_discovery_time = 0
        self.discovery_interval = 10000  # 10 segundos

    def initialize(self):
        """Initialize UDP socket"""
        try:
            self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.udp_socket.setblocking(False)
            # Bind to UDP port for receiving messages
            self.udp_socket.bind(('0.0.0.0', UDP_PORT))
            self.initialized = True
            log_message("INFO", f"UDP communication initialized on port {UDP_PORT}")
            return True
        except Exception as e:
            log_message("ERROR", f"UDP initialization failed: {e}")
            return False

    def _send_discovery_request(self):
        """Send discovery request via broadcast"""
        try:
            discovery_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            discovery_sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            
            message = "DISCOVER_ESP32_REQUEST"
            discovery_sock.sendto(message.encode(), (BROADCAST_IP, DISCOVERY_PORT))
            discovery_sock.close()
            
            log_message("DEBUG", f"Discovery request sent to {BROADCAST_IP}:{DISCOVERY_PORT}")
            return True
        except Exception as e:
            log_message("ERROR", f"Discovery request failed: {e}")
            return False

    def _process_discovery_response(self, message, addr):
        """Process a discovery response from PC"""
        if message.startswith("DISCOVER_PC_RESPONSE"):
            if validate_ip(addr[0]):
                self.pc_ip_address = addr[0]
                log_message("INFO", f"Discovered PC IP: {self.pc_ip_address}")
                blink_led(3, 100)  # Sinal de descoberta bem-sucedida
                return True
        return False

    def _handle_discovery(self):
        """Handle discovery process - non-blocking version"""
        self.discovery_running = True
        
        try:
            self.discovery_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.discovery_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.discovery_sock.bind(('0.0.0.0', DISCOVERY_PORT))
            self.discovery_sock.setblocking(False)

            log_message("INFO", f"Discovery service started on port {DISCOVERY_PORT}")

            while self.discovery_running:
                current_time = time.ticks_ms()
                
                # Send discovery request periodically
                if time.ticks_diff(current_time, self.last_discovery_time) > self.discovery_interval:
                    self._send_discovery_request()
                    self.last_discovery_time = current_time
                
                # Check for responses (non-blocking)
                try:
                    data, addr = self.discovery_sock.recvfrom(1024)
                    if data:
                        message = data.decode().strip()
                        self._process_discovery_response(message, addr)
                except OSError:
                    # No data available
                    pass
                
                time.sleep_ms(100)  # Yield to other threads

        except Exception as e:
            log_message("ERROR", f"Discovery handler failed: {e}")
        finally:
            if self.discovery_sock:
                self.discovery_sock.close()
            self.discovery_running = False

    def start_discovery_service(self):
        """Start discovery service"""
        try:
            # Primeiro envia uma solicitação imediatamente
            self._send_discovery_request()
            self.last_discovery_time = time.ticks_ms()
            
            # Inicia a thread de descoberta
            _thread.start_new_thread(self._handle_discovery, ())
            log_message("INFO", "Discovery service thread started")
            return True
        except Exception as e:
            log_message("ERROR", f"Failed to start discovery thread: {e}")
            return False

    def stop_discovery_service(self):
        """Stop discovery service"""
        self.discovery_running = False
        log_message("INFO", "Discovery service stopping...")

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
                
            if not self.pc_ip_address or not validate_ip(self.pc_ip_address):
                log_message("WARNING", f"No valid PC IP available: {self.pc_ip_address}")
                return False
            
            addr = (self.pc_ip_address, UDP_PORT)
            self.udp_socket.sendto(message.encode(), addr)
            blink_led(1, 50)
            log_message("DEBUG", f"UDP -> {message} to {addr}")
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
                log_message("DEBUG", f"UDP <- {message} from {addr[0]}")
                
                # Atualiza IP do PC se a mensagem vier de um IP válido
                if addr[0] != self.pc_ip_address and validate_ip(addr[0]):
                    self.update_pc_ip(addr[0])
                    
                return message
        except OSError:
            # No data available (non-blocking socket)
            pass
        except Exception as e:
            log_message("ERROR", f"UDP read failed: {e}")
        return ""

# Instância global
udp_comm = UDPComm()