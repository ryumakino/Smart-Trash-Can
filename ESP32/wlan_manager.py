# wlan_manager.py
import network
import time
from utils import get_logger
from network_utils import NetworkInfoBuilder, WiFiConnectionManager, APManager, NetworkStatusUpdater

logger = get_logger("WlanManager")

class WlanManager:
    """Gerenciador WiFi simplificado usando utilitários"""
    
    def __init__(self, device_manager):
        self.device_manager = device_manager
        self.config_mgr = device_manager.get_config_manager()
        self.wifi_config = self.config_mgr.get_wifi_config()
        
        self.sta_if = network.WLAN(network.STA_IF)
        self.ap_if = network.WLAN(network.AP_IF)
        self.connected = False
        self.ip = None
        self.ap_mode = False
        self.connection_attempts = 0

    def connect(self):
        """Conecta ao Wi-Fi ou cria Access Point se falhar"""
        logger.info("Iniciando conexão Wi-Fi...")
        
        # Desativar AP inicialmente
        self.ap_if.active(False)
        self.sta_if.active(True)
        
        # Tentar conectar ao Wi-Fi
        wifi_success = self._connect_to_wifi()
        
        if not wifi_success:
            logger.warning("Falha na conexão Wi-Fi. Iniciando Access Point...")
            ap_result = self.start_ap()
            connection_result = NetworkInfoBuilder.build_connection_info(
                self.sta_if, self.ap_if, self.wifi_config, ap_result, 'AP', 
                self.connected, self.ap_mode, self.ip
            )
        else:
            connection_result = NetworkInfoBuilder.build_connection_info(
                self.sta_if, self.ap_if, self.wifi_config, True, 'STA',
                self.connected, self.ap_mode, self.ip
            )
        
        # Atualizar DeviceManager
        self.device_manager.update_network_info(connection_result)
        
        return connection_result

    def _connect_to_wifi(self):
        """Tenta conectar ao Wi-Fi configurado usando utilitário reutilizável"""
        ssid = self.wifi_config.get('SSID')
        password = self.wifi_config.get('PASSWORD')
        
        if not ssid or not password:
            logger.error("SSID ou senha não configurados")
            return False

        self.connection_attempts += 1
        
        success = WiFiConnectionManager.attempt_connection(
            self.sta_if, 
            ssid, 
            password,
            self.wifi_config.get('MAX_RETRIES', 3),
            self.wifi_config.get('RETRY_DELAY', 5)
        )
        
        if success:
            self.connected = True
            self.ip = self.sta_if.ifconfig()[0]
            NetworkStatusUpdater.update_wifi_status(self.config_mgr, self.sta_if, self.wifi_config)
            logger.success(f"Conectado ao WiFi após {self.connection_attempts} tentativa(s)")
        
        return success

    def start_ap(self):
        """Ativar Access Point usando utilitário reutilizável"""
        try:
            # Desativar STA
            self.sta_if.active(False)
            
            # Configurar AP
            device_id = self.device_manager.get_device_id()
            success, ap_ssid = APManager.setup_ap(self.ap_if, device_id, self.wifi_config)
            
            if success:
                self.ap_mode = True
                self.ip = '192.168.4.1'
                NetworkStatusUpdater.update_ap_status(self.config_mgr, ap_ssid, self.ip)
                
                logger.success("=== MODO ACCESS POINT ATIVADO ===")
                logger.success(f"SSID: {ap_ssid}")
                logger.success(f"IP: {self.ip}")
            
            return success
            
        except Exception as e:
            logger.error(f"Erro ao iniciar Access Point: {e}")
            return False

    def get_ip(self):
        return self.ip

    def get_network_prefix(self):
        return NetworkInfoBuilder.get_network_prefix(self.ip, self.ap_mode)

    def is_connected(self):
        return self.connected

    def is_ap_mode(self):
        return self.ap_mode
    
    def get_connection_info(self):
        """Obter informações detalhadas da conexão"""
        return {
            'connected': self.connected,
            'ap_mode': self.ap_mode,
            'ip': self.ip,
            'ssid': self.wifi_config.get('SSID'),
            'connection_attempts': self.connection_attempts,
            'sta_active': self.sta_if.active(),
            'ap_active': self.ap_if.active()
        }