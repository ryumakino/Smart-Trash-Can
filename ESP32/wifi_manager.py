# wifi_manager.py - VERSÃO SEGURA
import network
import time
from hardware_utils import log_message
from config import WIFI_SSID, WIFI_PASSWORD, WIFI_CONNECTION_TIMEOUT_MS

class WiFiManager:
    def __init__(self):
        self.wlan = None
        self.connected = False
        self.initialized = False

    def initialize(self) -> bool:
        """Initialize WiFi connection SAFELY"""
        if self.initialized:
            return True
            
        log_message("INFO", "Setting up Wi-Fi...")
        
        try:
            # ⭐⭐ CRÍTICO: Cria nova instância
            self.wlan = network.WLAN(network.STA_IF)
            
            # ⭐⭐ CRÍTICO: Desativa completamente primeiro
            if self.wlan.active():
                self.wlan.active(False)
                time.sleep_ms(1000)
            
            # ⭐⭐ CRÍTICO: Ativa com timeout
            self.wlan.active(True)
            time.sleep_ms(2000)
            
            if not self.wlan.active():
                log_message("ERROR", "Wi-Fi interface failed to activate")
                return False
            
            # ⭐⭐ NÃO configura ifconfig ainda
            log_message("INFO", "Wi-Fi interface activated")
            
            # ⭐⭐ Opcional: Tenta conectar apenas se credenciais existem
            if WIFI_SSID and WIFI_PASSWORD and WIFI_SSID != "YOUR_NETWORK_NAME":
                return self._connect_to_wifi()
            else:
                log_message("WARNING", "WiFi credentials not configured")
                self.initialized = True
                return True
                
        except Exception as e:
            log_message("ERROR", f"Wi-Fi setup failed: {e}")
            return False

    def _connect_to_wifi(self) -> bool:
        """Try to connect to WiFi"""
        try:
            log_message("INFO", f"Connecting to: {WIFI_SSID}")
            self.wlan.connect(WIFI_SSID, WIFI_PASSWORD)
            
            # Aguarda a conexão
            start_time = time.ticks_ms()
            while not self.wlan.isconnected():
                if time.ticks_diff(time.ticks_ms(), start_time) > WIFI_CONNECTION_TIMEOUT_MS:
                    log_message("ERROR", "Wi-Fi connection timeout")
                    return False
                
                log_message("DEBUG", "Waiting for Wi-Fi connection...")
                time.sleep_ms(2000)
            
            # Conexão bem-sucedida
            ip_info = self.wlan.ifconfig()
            log_message("INFO", "Wi-Fi connected successfully!")
            log_message("INFO", f"IP Address: {ip_info[0]}")
            self.connected = True
            self.initialized = True
            return True
            
        except Exception as e:
            log_message("ERROR", f"Wi-Fi connection failed: {e}")
            return False

    def get_ip_address(self) -> str:
        if self.wlan and self.wlan.isconnected():
            return self.wlan.ifconfig()[0]
        return "0.0.0.0"

    def is_connected(self) -> bool:
        return self.connected and self.wlan and self.wlan.isconnected()

    def disconnect(self):
        try:
            if self.wlan:
                if self.wlan.isconnected():
                    self.wlan.disconnect()
                self.wlan.active(False)
                self.connected = False
                self.initialized = False
                log_message("INFO", "Wi-Fi completely disconnected")
        except Exception as e:
            log_message("ERROR", f"Error disconnecting Wi-Fi: {e}")

# ⭐⭐ CRÍTICO: NÃO inicializa automaticamente
wifi_manager = WiFiManager()