# wifi_manager.py
import network
import time
from config import WiFiConfig
from utils import get_logger

logger = get_logger("WiFiManager")

class WiFiManager:
    def __init__(self):
        self.sta_if = network.WLAN(network.STA_IF)
        self.connected = False
        self.ip = None

    def connect(self):
        """Conecta ao Wi-Fi"""
        if self.sta_if.isconnected():
            logger.info("✅ Já conectado ao Wi-Fi")
            self.connected = True
            self.ip = self.sta_if.ifconfig()[0]
            return True

        logger.info(f"📡 Conectando ao Wi-Fi: {WiFiConfig.SSID}")
        self.sta_if.active(True)
        
        for attempt in range(WiFiConfig.MAX_RETRIES):
            try:
                self.sta_if.connect(WiFiConfig.SSID, WiFiConfig.PASSWORD)
                
                # Aguarda conexão
                for _ in range(20):  # Aguarda até 20 segundos
                    if self.sta_if.isconnected():
                        self.connected = True
                        self.ip = self.sta_if.ifconfig()[0]
                        logger.success(f"✅ Conectado ao Wi-Fi! IP: {self.ip}")
                        return True
                    time.sleep(1)
                
                logger.warning(f"⏳ Tentativa {attempt + 1} falhou. Tentando novamente...")
                time.sleep(WiFiConfig.RETRY_DELAY)
                
            except Exception as e:
                logger.error(f"❌ Erro na conexão Wi-Fi: {e}")
                time.sleep(WiFiConfig.RETRY_DELAY)

        logger.error("❌ Falha ao conectar ao Wi-Fi")
        return False

    def get_ip(self):
        """Retorna o IP atual"""
        if self.sta_if.isconnected():
            return self.sta_if.ifconfig()[0]
        return None

    def is_connected(self):
        """Verifica se está conectado"""
        return self.sta_if.isconnected()