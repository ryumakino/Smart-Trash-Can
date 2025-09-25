import network
import time
from config import WiFiConfig
from utils import get_logger

logger = get_logger("WlanManager")

class WlanManager:
    def __init__(self):
        self.sta_if = network.WLAN(network.STA_IF)
        self.connected = False
        self.ip = None

    def connect(self):
        """Conecta ao Wi-Fi"""
        if self.sta_if.isconnected():
            self.connected = True
            self.ip = self.sta_if.ifconfig()[0]
            return True

        logger.info(f"Conectando ao Wi-Fi: {WiFiConfig.SSID}")
        self.sta_if.active(True)
        
        for _ in range(WiFiConfig.MAX_RETRIES):
            try:
                self.sta_if.connect(WiFiConfig.SSID, WiFiConfig.PASSWORD)
                
                # Aguarda conexão
                for _ in range(20):  # Aguarda até 20 segundos
                    if self.sta_if.isconnected():
                        self.connected = True
                        self.ip = self.sta_if.ifconfig()[0]
                        logger.success(f"Conectado ao Wi-Fi! IP: {self.ip}")
                        return True
                    time.sleep(1)
                time.sleep(WiFiConfig.RETRY_DELAY)
                
            except Exception:
                time.sleep(WiFiConfig.RETRY_DELAY)

        logger.error("Não foi possível conectar ao Wi-Fi. Sistema não pode iniciar.")
        return False

    def get_ip(self):
        """Retorna o IP atual"""
        return self.ip
    
    def get_network_prefix(self):
        """Extrai o prefixo da rede do IP (ex: 192.168.1)"""
        try:
            parts = self.get_ip.split('.')
            if len(parts) == 4:
                return '.'.join(parts[:3])
        except Exception:
            pass
        logger.error("Não foi possível determinar prefixo da rede")
        return None

    def is_connected(self):
        """Verifica se está conectado"""
        return self.connected