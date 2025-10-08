# device_manager.py - CORREÇÕES
import time
import machine
from utils import get_logger
from config_manager import ConfigManager

logger = get_logger("DeviceManager")

class DeviceInfo:
    def __init__(self, config_manager):
        self.config_manager = config_manager
        self.info = self._initialize_info()
    
    def _initialize_info(self):
        device_config = self.config_manager.get_section('DeviceConfig')
        
        # CORREÇÃO: Gerar device_id único se necessário
        device_id = device_config.get('DEVICE_ID', 'UNKNOWN')
        if device_config.get('AUTO_GENERATE_ID', True) or device_id == 'UNKNOWN':
            import machine
            device_id = f"TRASH_AI_{machine.unique_id().hex()[-6:]}"
        
        return {
            'device_id': device_id,
            'device_name': device_config.get('DEVICE_NAME', 'Lixeira Inteligente'),
            'device_type': device_config.get('DEVICE_TYPE', 'TRASH_CAN'),
            'firmware_version': '2.0.0',
            'boot_time': time.time()
        }
    
    def get_info(self):
        return self.info.copy()
    
    def update_info(self, updates):
        self.info.update(updates)

class SystemMetrics:
    def __init__(self):
        self.startup_time = time.time()
        self.health_check_count = 0
    
    def get_metrics(self):
        import gc
        gc.collect()
        
        return {
            'uptime': time.time() - self.startup_time,
            'memory_free': gc.mem_free(),
            'health_check_count': self.health_check_count,
            'timestamp': time.time()
        }
    
    def increment_health_count(self):
        self.health_check_count += 1

class DeviceManager:
    def __init__(self, config_filename='config.json'):
        self.config_mgr = ConfigManager(config_filename)
        self.device_info = DeviceInfo(self.config_mgr)
        self.system_metrics = SystemMetrics()
        
        self.modules = {}
    
    def load_module(self, module_name, module_class, *args, **kwargs):
        if module_name not in self.modules:
            try:
                self.modules[module_name] = module_class(*args, **kwargs)
                logger.success(f"Módulo {module_name} carregado")
            except Exception as e:
                logger.error(f"Erro ao carregar {module_name}: {e}")
                return None
        
        return self.modules[module_name]
    
    def get_device_info(self):
        return self.device_info.get_info()
    
    def get_system_info(self):
        return self.system_metrics.get_metrics()
    
    def get_config(self, section):
        return self.config_mgr.get_section(section)
    
    def get_complete_status(self):
        return {
            'device': self.get_device_info(),
            'system': self.get_system_info(),
            'timestamp': time.time()
        }

    def get_communication_status(self):
        communication = self.modules.get('communication')
        if communication and hasattr(communication, 'get_communication_status'):
            return communication.get_communication_status()
        
        return {
            'running': False,
            'active_protocol': None,
            'server_connected': False,
            'server': {
                'ip': None,
                'port': None,
                'name': 'Unknown',
                'connected': False
            },
            'protocols_status': {
                'serial': False,
                'sta': False,
                'ap': False
            }
        }
    
    def get_server_info(self):
        communication = self.modules.get('communication')
        if communication and hasattr(communication, 'get_server_info'):
            return communication.get_server_info()
        return {'ip': None, 'port': None, 'name': 'Unknown', 'connected': False}
    
    def get_network_status(self):
        wlan = self.modules.get('wlan')
        if wlan and hasattr(wlan, 'get_connection_info'):
            return wlan.get_connection_info()
        return {'connected': False, 'mode': 'UNKNOWN'}
    
    def get_servo_config(self):
        # CORREÇÃO: Nome da seção correto
        return self.config_mgr.get_section('ServoConfig')
    
    def get_network_config(self):
        return self.config_mgr.get_section('NetworkConfig')
    
    def get_wifi_config(self):
        return self.config_mgr.get_section('WiFiConfig')
    
    def get_system_config(self):
        return self.config_mgr.get_section('SystemConfig')
    
    def get_ir_config(self):
        return self.config_mgr.get_section('IRSensorConfig')