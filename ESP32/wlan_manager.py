# wlan_manager.py - CORREÇÕES
import network
import time
from utils import get_logger

logger = get_logger("WlanManager")

class NetworkInterface:
    def connect(self):
        raise NotImplementedError
    
    def disconnect(self):
        raise NotImplementedError
    
    def is_connected(self):
        raise NotImplementedError
    
    def get_config(self):
        raise NotImplementedError

class WiFiConnector:
    def __init__(self, ssid, password, max_retries=3, timeout=30):
        self.ssid = ssid
        self.password = password
        self.max_retries = max_retries
        self.timeout = timeout
    
    def connect_with_retry(self, interface):
        for attempt in range(1, self.max_retries + 1):
            logger.info(f"Tentativa {attempt} para {self.ssid}")
            
            # CORREÇÃO: Conexão WiFi correta para MicroPython
            interface.connect(self.ssid, self.password)
            start_time = time.time()
            
            while not interface.isconnected():
                if time.time() - start_time > self.timeout:
                    break
                time.sleep(1)
            
            if interface.isconnected():
                logger.success(f"Conectado na tentativa {attempt}")
                return True
            
            logger.warning(f"Tentativa {attempt} falhou")
            if attempt < self.max_retries:
                time.sleep(5)
        
        return False

class STAInterface(NetworkInterface):
    def __init__(self, ssid, password):
        self.interface = network.WLAN(network.STA_IF)
        self.connector = WiFiConnector(ssid, password)
        self.ip = None
    
    def connect(self):
        self.interface.active(True)
        
        if self.connector.connect_with_retry(self.interface):
            self._update_connection_info()
            return True
        return False
    
    def _update_connection_info(self):
        if self.interface.isconnected():
            # CORREÇÃO: ifconfig retorna (ip, subnet, gateway, dns)
            self.ip = self.interface.ifconfig()[0]
    
    def is_connected(self):
        return self.interface.isconnected()
    
    def get_config(self):
        return {
            'mode': 'STA',
            'ip': self.ip,
            'connected': self.is_connected()
        }
    
    def disconnect(self):
        self.interface.disconnect()
        self.interface.active(False)

class WlanManager:
    def __init__(self, device_manager):
        wifi_config = device_manager.get_config('WiFiConfig')
        
        self.sta = STAInterface(
            wifi_config.get('SSID', ''),
            wifi_config.get('PASSWORD', '')
        )
        self.current_interface = None
    
    def connect(self):
        logger.info("Conectando à rede...")
        
        try:
            import gc
            gc.collect()
            
            if self.sta.connect():
                self.current_interface = self.sta
                logger.success(f"Conectado - IP: {self.sta.ip}")
                return self._build_connection_result(True)
            
            logger.error("Falha na conexão WiFi")
            return self._build_connection_result(False)
            
        except Exception as e:
            logger.error(f"Erro na conexão WiFi: {e}")
            return self._build_connection_result(False)
    
    def _build_connection_result(self, connected):
        return {
            'connected': connected,
            'ap_mode': False,
            'ip': self.sta.ip if connected else '0.0.0.0'
        }
    
    def get_connection_info(self):
        if self.current_interface:
            return self.current_interface.get_config()
        return {'mode': 'DISCONNECTED', 'connected': False}