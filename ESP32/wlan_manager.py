# wlan_manager.py
import network
import time
import ubinascii
from utils import get_logger

logger = get_logger("WlanManager")

class NetworkInterface:
    """Interface base para interfaces de rede - LSP"""
    
    def is_connected(self):
        raise NotImplementedError
    
    def get_config(self):
        raise NotImplementedError
    
    def connect(self):
        raise NotImplementedError
    
    def disconnect(self):
        raise NotImplementedError

class STAInterface(NetworkInterface):
    """SRP: Interface Station (cliente WiFi)"""
    
    def __init__(self, ssid, password, max_retries=3, retry_delay=5):
        self.interface = network.WLAN(network.STA_IF)
        self.ssid = ssid
        self.password = password
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.mac = None
        self.ip = None
    
    def connect(self):
        """Conectar à rede WiFi"""
        logger.info(f"Conectando ao WiFi: {self.ssid}")
        
        self.interface.active(True)
        
        for attempt in range(self.max_retries):
            try:
                if not self.interface.isconnected():
                    self.interface.connect(self.ssid, self.password)
                    
                    # Aguardar conexão
                    for _ in range(20):
                        if self.interface.isconnected():
                            self._update_connection_info()
                            logger.success(f"Conectado: IP {self.ip}")
                            return True
                        time.sleep(1)
                    
                    time.sleep(self.retry_delay)
                    
            except Exception as e:
                logger.error(f"Tentativa {attempt + 1} falhou: {e}")
                time.sleep(self.retry_delay)
        
        return False
    
    def _update_connection_info(self):
        """Atualizar informações de conexão - SRP"""
        if self.interface.isconnected():
            ip, subnet, gateway, dns = self.interface.ifconfig()
            self.mac = ubinascii.hexlify(self.interface.config('mac')).decode().upper()
            self.ip = ip
            self.subnet_mask = subnet
            self.gateway = gateway
            self.dns = dns
    
    def is_connected(self):
        return self.interface.isconnected()
    
    def get_config(self):
        return {
            'mode': 'STA',
            'mac': self.mac,
            'ip': self.ip,
            'subnet_mask': self.subnet_mask,
            'gateway': self.gateway,
            'dns': self.dns,
            'ssid': self.ssid
        }
    
    def disconnect(self):
        self.interface.disconnect()
        self.interface.active(False)

class APInterface(NetworkInterface):
    """SRP: Interface Access Point"""
    
    def __init__(self, ssid_prefix, password, channel=6):
        self.interface = network.WLAN(network.AP_IF)
        self.ssid_prefix = ssid_prefix
        self.password = password
        self.channel = channel
        self.ip = None
    
    def connect(self, device_id):
        """Configurar Access Point"""
        try:
            ap_ssid = f"{self.ssid_prefix}{device_id[-4:]}"
            
            self.interface.active(True)
            self.interface.config(
                essid=ap_ssid,
                password=self.password,
                authmode=3,
                channel=self.channel
            )
            
            # IP fixo para AP
            self.interface.ifconfig(('192.168.4.1', '255.255.255.0', '192.168.4.1', '8.8.8.8'))
            self._update_ap_info()
            
            logger.success(f"AP ativo: SSID {ap_ssid}, IP {self.ip}")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao configurar AP: {e}")
            return False
    
    def _update_ap_info(self):
        """Atualizar informações do AP - SRP"""
        if self.interface.active():
            ip, subnet, gateway, dns = self.interface.ifconfig()
            self.ip = ip
            self.subnet_mask = subnet
            self.gateway = gateway
            self.dns = dns
    
    def is_connected(self):
        return self.interface.active()
    
    def get_config(self):
        return {
            'mode': 'AP',
            'ip': self.ip,
            'subnet_mask': self.subnet_mask,
            'gateway': self.gateway,
            'dns': self.dns
        }
    
    def disconnect(self):
        self.interface.active(False)

class WlanManager:
    """Composite: Gerenciar interfaces de rede"""
    
    def __init__(self, device_manager):
        self.device_manager = device_manager
        wifi_config = device_manager.get_wifi_config()
        
        # Criar interfaces
        self.sta = STAInterface(
            wifi_config.get('SSID'),
            wifi_config.get('PASSWORD'),
            wifi_config.get('MAX_RETRIES', 3),
            wifi_config.get('RETRY_DELAY', 5)
        )
        
        self.ap = APInterface(
            wifi_config.get('AP_SSID_PREFIX', 'TRASH_AI_'),
            wifi_config.get('AP_PASSWORD', 'trashai2024'),
            wifi_config.get('AP_CHANNEL', 6)
        )
        
        self.current_interface = None
    
    def connect(self):
        """Conectar à rede - estratégia: STA primeiro, depois AP"""
        logger.info("Iniciando conexão de rede...")
        
        # Desativar AP inicialmente
        self.ap.disconnect()
        
        # Tentar STA primeiro
        if self.sta.connect():
            self.current_interface = self.sta
            return self._build_connection_result(True, False)
        else:
            # Fallback para AP
            device_id = self.device_manager.get_device_id()
            if self.ap.connect(device_id):
                self.current_interface = self.ap
                return self._build_connection_result(False, True)
        
        return self._build_connection_result(False, False)
    
    def _build_connection_result(self, sta_connected, ap_connected):
        """Construir resultado de conexão - DRY"""
        if self.current_interface:
            config = self.current_interface.get_config()
            return {
                'connected': sta_connected or ap_connected,
                'ap_mode': ap_connected,
                'connection_status': 'CONNECTED',
                **config
            }
        else:
            return {
                'connected': False,
                'ap_mode': False,
                'connection_status': 'DISCONNECTED',
                'ip': '0.0.0.0'
            }
    
    def get_network_prefix(self):
        """Obter prefixo da rede"""
        if self.current_interface and self.current_interface.ip:
            parts = self.current_interface.ip.split(".")
            if len(parts) == 4:
                return ".".join(parts[:3])
        return None
    
    def get_connection_info(self):
        """Obter informações detalhadas"""
        if self.current_interface:
            return self.current_interface.get_config()
        return {'mode': 'DISCONNECTED'}