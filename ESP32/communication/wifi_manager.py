import network
import time
from utils import log_message
from config import WIFI_SSID, WIFI_PASSWORD, WIFI_CONNECTION_TIMEOUT_MS

class WiFiManager:
    def __init__(self):
        self.wlan = network.WLAN(network.STA_IF)
        self.connected = False

    def initialize(self) -> bool:
        """Initialize WiFi connection"""
        log_message("INFO", "Setting up Wi-Fi...")
        
        try:
            # Ativa a interface Wi-Fi
            if not self.wlan.active():
                self.wlan.active(True)
                log_message("INFO", "Wi-Fi interface activated")
                time.sleep_ms(100)
            
            # Usa DHCP
            self.wlan.ifconfig(('0.0.0.0', '0.0.0.0', '0.0.0.0', '0.0.0.0'))
            log_message("INFO", "Using DHCP for IP configuration")

            # Verifica se já está conectado
            if self.wlan.isconnected():
                ip_info = self.wlan.ifconfig()
                log_message("INFO", f"Already connected to Wi-Fi! IP: {ip_info[0]}")
                self.connected = True
                return True
            
            # Conecta ao Wi-Fi
            log_message("INFO", f"Connecting to: {WIFI_SSID}")
            self.wlan.connect(WIFI_SSID, WIFI_PASSWORD)
            
            # Aguarda a conexão
            start_time = time.ticks_ms()
            while not self.wlan.isconnected():
                if time.ticks_diff(time.ticks_ms(), start_time) > WIFI_CONNECTION_TIMEOUT_MS:
                    log_message("ERROR", "Wi-Fi connection timeout")
                    return False
                
                log_message("DEBUG", "Waiting for Wi-Fi connection...")
                time.sleep_ms(1000)
            
            # Conexão bem-sucedida
            ip_info = self.wlan.ifconfig()
            log_message("INFO", "Wi-Fi connected successfully!")
            log_message("INFO", f"IP Address: {ip_info[0]}")
            self.connected = True
            return True
            
        except Exception as e:
            log_message("ERROR", f"Wi-Fi setup failed: {e}")
            return False

    def get_ip_address(self) -> str:
        """Get current IP address"""
        if self.wlan.isconnected():
            return self.wlan.ifconfig()[0]
        return "0.0.0.0"

    def get_network_info(self) -> tuple:
        """Get network info"""
        if self.wlan.isconnected():
            return self.wlan.ifconfig()
        return ("0.0.0.0", "0.0.0.0", "0.0.0.0", "0.0.0.0")

    def get_full_network_info(self) -> dict:
        """Get complete network info"""
        try:
            if self.wlan.isconnected():
                ip, subnet, gateway, dns = self.wlan.ifconfig()
                return {
                    'ip': ip,
                    'subnet': subnet,
                    'gateway': gateway,
                    'dns': dns,
                    'mac': ':'.join(['%02x' % i for i in self.wlan.config('mac')]),
                    'hostname': 'esp32',
                    'connected': True,
                    'ssid': WIFI_SSID
                }
        except Exception as e:
            log_message("ERROR", f"Error getting network info: {e}")
        
        return {
            'ip': '0.0.0.0',
            'subnet': '0.0.0.0',
            'gateway': '0.0.0.0',
            'dns': '0.0.0.0',
            'mac': 'unknown',
            'hostname': 'esp32',
            'connected': False,
            'ssid': WIFI_SSID
        }

    def is_connected(self) -> bool:
        """Check if connected to WiFi"""
        return self.wlan.isconnected()

    def disconnect(self):
        """Disconnect from WiFi"""
        try:
            if self.wlan.isconnected():
                self.wlan.disconnect()
                log_message("INFO", "Wi-Fi disconnected")
            self.wlan.active(False)
            log_message("INFO", "Wi-Fi interface deactivated")
            self.connected = False
        except Exception as e:
            log_message("ERROR", f"Error disconnecting Wi-Fi: {e}")

# Instância global
wifi_manager = WiFiManager()