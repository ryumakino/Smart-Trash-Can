# device_manager.py - Gerenciador centralizado do dispositivo
import time
import machine
from utils import get_logger
from config_manager import ConfigManager

logger = get_logger("DeviceManager")

class DeviceManager:
    """Gerenciador central do dispositivo - Single Source of Truth"""
    
    def __init__(self):
        self.config_mgr = ConfigManager()
        self.device_info = {}
        self.network_status = {}
        self.system_info = {}
        self._initialize_device()
    
    def _initialize_device(self):
        """Inicializar informações do dispositivo"""
        device_config = self.config_mgr.get_device_config()
        
        # Gerar ID do dispositivo se necessário
        if device_config.get('AUTO_GENERATE_ID', True) or not device_config.get('DEVICE_ID'):
            device_id = self._generate_device_id()
            device_config['DEVICE_ID'] = device_id
            self.config_mgr.update_device_config({'DEVICE_ID': device_id})
        
        self.device_info = {
            'device_id': device_config.get('DEVICE_ID'),
            'device_name': device_config.get('DEVICE_NAME', 'Lixeira Inteligente'),
            'device_type': device_config.get('DEVICE_TYPE', 'TRASH_CAN'),
            'device_location': device_config.get('DEVICE_LOCATION', 'Desconhecido'),
            'device_version': device_config.get('DEVICE_VERSION', '1.0.0'),
            'device_manufacturer': device_config.get('DEVICE_MANUFACTURER', 'MAKEDC'),
            'firmware_version': '1.0.0',
            'mac_address': self._get_mac_address(),
            'boot_time': time.time()
        }
        
        logger.info(f"Dispositivo inicializado: {self.device_info['device_name']}")
    
    def _generate_device_id(self):
        """Gerar ID único do dispositivo"""
        import ubinascii
        import machine
        try:
            mac = machine.unique_id()
            return f"TRASH_AI_{ubinascii.hexlify(mac).decode().upper()[-6:]}"
        except:
            return f"TRASH_AI_{int(time.time()) % 10000:04d}"
    
    def _get_mac_address(self):
        """Obter endereço MAC"""
        try:
            import ubinascii
            import network
            sta = network.WLAN(network.STA_IF)
            return ubinascii.hexlify(sta.config('mac')).decode().upper()
        except:
            return "UNKNOWN"
    
    def get_config_manager(self):
        return self.config_mgr
    
    def get_device_info(self):
        return self.device_info.copy()
    
    def get_device_id(self):
        return self.device_info['device_id']
    
    def update_network_info(self, network_info):
        """Atualizar informações de rede"""
        self.network_status = network_info
        logger.debug(f"Network status updated: {network_info.get('connection_status', 'UNKNOWN')}")
    
    def get_network_status(self):
        return self.network_status.copy()
    
    def get_system_info(self):
        """Obter informações do sistema em tempo real"""
        import gc
        self.system_info = {
            'uptime': time.time() - self.device_info['boot_time'],
            'memory_free': gc.mem_free(),
            'memory_allocated': gc.mem_alloc(),
            'reset_cause': machine.reset_cause(),
            'timestamp': time.time()
        }
        return self.system_info
    
    def get_broadcast_message(self):
        """Mensagem padronizada para broadcast"""
        return {
            'device_id': self.device_info['device_id'],
            'device_name': self.device_info['device_name'],
            'device_type': self.device_info['device_type'],
            'firmware_version': self.device_info['firmware_version'],
            'ip': self.network_status.get('ip', '0.0.0.0'),
            'status': self.network_status.get('connection_status', 'DISCONNECTED'),
            'timestamp': time.time()
        }
    
    def get_complete_status(self):
        """Status completo do dispositivo"""
        return {
            'device': self.get_device_info(),
            'network': self.get_network_status(),
            'system': self.get_system_info(),
            'config': self.config_mgr.get_all_configs()
        }
    
    # Métodos de atualização de configuração
    def update_device_config(self, config_updates):
        success = self.config_mgr.update_device_config(config_updates)
        if success and 'DEVICE_NAME' in config_updates:
            self.device_info['device_name'] = config_updates['DEVICE_NAME']
        return success
    
    def update_wifi_config(self, config_updates):
        return self.config_mgr.update_wifi_config(config_updates)
    
    def update_network_config(self, config_updates):
        return self.config_mgr.update_network_config(config_updates)
    
    def update_system_config(self, config_updates):
        return self.config_mgr.update_system_config(config_updates)
    
    # Métodos de acesso direto a configurações
    def get_system_config(self):
        return self.config_mgr.get_system_config()
    
    def get_network_config(self):
        return self.config_mgr.get_network_config()
    
    def get_wifi_config(self):
        return self.config_mgr.get_wifi_config()