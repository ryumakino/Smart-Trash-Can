# device_manager.py
import time
import machine
import ubinascii
import network
from utils import get_logger
from config_manager import ConfigManager

logger = get_logger("DeviceManager")

class DeviceManager:
    """Gerenciador central do dispositivo - Single Source of Truth"""
    
    def __init__(self, config_filename='config.json'):
        self.config_mgr = ConfigManager(config_filename)
        self.device_info = {}
        self.network_status = {}
        self.system_metrics = {
            'startup_time': time.time(),
            'reset_count': 0,
            'last_health_check': 0
        }
        self._initialize_device()
    
    def _initialize_device(self):
        """Inicializar informações do dispositivo com validação"""
        device_config = self.config_mgr.get_device_config()
        
        # Gerar/validar ID do dispositivo
        device_id = self._ensure_device_id(device_config)
        
        # Coletar informações de hardware
        hardware_info = self._collect_hardware_info()
        
        self.device_info = {
            'device_id': device_id,
            'device_name': device_config.get('DEVICE_NAME', 'Lixeira Inteligente'),
            'device_type': device_config.get('DEVICE_TYPE', 'TRASH_CAN'),
            'device_location': device_config.get('DEVICE_LOCATION', 'Desconhecido'),
            'device_version': device_config.get('DEVICE_VERSION', '1.0.0'),
            'device_manufacturer': device_config.get('DEVICE_MANUFACTURER', 'MAKEDC'),
            'firmware_version': '2.0.0',
            'mac_address': hardware_info['mac_address'],
            'hardware_info': hardware_info,
            'boot_time': time.time(),
            'reset_cause': machine.reset_cause()
        }
        
        logger.info(f"Dispositivo inicializado: {self.device_info['device_name']} ({device_id})")
    
    def _ensure_device_id(self, device_config):
        """Garantir que o dispositivo tenha um ID válido"""
        device_id = device_config.get('DEVICE_ID')
        auto_generate = device_config.get('AUTO_GENERATE_ID', True)
        
        if not device_id or auto_generate:
            device_id = self._generate_device_id()
            self.config_mgr.update_value('DeviceConfig', 'DEVICE_ID', device_id)
            logger.info(f"ID do dispositivo gerado: {device_id}")
        
        return device_id
    
    def _generate_device_id(self):
        """Gerar ID único do dispositivo baseado em hardware"""
        try:
            # Tentar usar MAC address primeiro
            sta = network.WLAN(network.STA_IF)
            if sta.active():
                mac = sta.config('mac')
                return f"TRASH_AI_{ubinascii.hexlify(mac).decode().upper()[-6:]}"
            
            # Fallback para ID único do microcontrolador
            unique_id = machine.unique_id()
            return f"TRASH_AI_{ubinascii.hexlify(unique_id).decode().upper()[-6:]}"
            
        except Exception as e:
            logger.warning(f"Erro ao gerar ID hardware, usando timestamp: {e}")
            return f"TRASH_AI_{int(time.time()) % 100000:05d}"
    
    def _collect_hardware_info(self):
        """Coletar informações de hardware"""
        try:
            import gc
            import os
            
            return {
                'mac_address': self._get_mac_address(),
                'memory_total': gc.mem_alloc() + gc.mem_free(),
                'memory_free': gc.mem_free(),
                'platform': os.uname().sysname,
                'cpu_freq': machine.freq() if hasattr(machine, 'freq') else 0,
                'reset_cause': machine.reset_cause()
            }
        except Exception as e:
            logger.error(f"Erro ao coletar info hardware: {e}")
            return {'mac_address': 'UNKNOWN'}
    
    def _get_mac_address(self):
        """Obter endereço MAC de forma segura"""
        try:
            sta = network.WLAN(network.STA_IF)
            if sta.active():
                return ubinascii.hexlify(sta.config('mac')).decode().upper()
            return "NOT_CONNECTED"
        except:
            return "UNKNOWN"
    
    # Métodos de acesso público
    def get_config_manager(self):
        return self.config_mgr
    
    def get_device_info(self):
        return self.device_info.copy()
    
    def get_device_id(self):
        return self.device_info['device_id']
    
    def update_network_info(self, network_info):
        """Atualizar informações de rede com validação"""
        if isinstance(network_info, dict):
            self.network_status = network_info
            logger.debug(f"Status rede atualizado: {network_info.get('connection_status', 'UNKNOWN')}")
        else:
            logger.error("Network info must be a dictionary")
    
    def get_network_status(self):
        return self.network_status.copy()
    
    def get_system_info(self):
        """Obter informações do sistema em tempo real"""
        import gc
        
        current_time = time.time()
        memory_free = gc.mem_free()
        memory_allocated = gc.mem_alloc()
        total_memory = memory_free + memory_allocated
        
        system_info = {
            'uptime': current_time - self.system_metrics['startup_time'],
            'memory_free': memory_free,
            'memory_allocated': memory_allocated,
            'memory_total': total_memory,
            'memory_percent': (memory_allocated / total_memory) * 100 if total_memory > 0 else 0,
            'reset_cause': machine.reset_cause(),
            'timestamp': current_time,
            'health_check_count': self.system_metrics.get('health_check_count', 0)
        }
        
        return system_info
    
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
        """Status completo do dispositivo para APIs"""
        return {
            'device': self.get_device_info(),
            'network': self.get_network_status(),
            'system': self.get_system_info(),
            'config': self.config_mgr.get_all_configs(),
            'timestamp': time.time()
        }
    
    # Métodos de atualização de configuração
    def update_device_config(self, config_updates):
        """Atualizar configuração do dispositivo"""
        success = self.config_mgr.update_section('DeviceConfig', config_updates)
        if success:
            # Atualizar cache local se necessário
            if 'DEVICE_NAME' in config_updates:
                self.device_info['device_name'] = config_updates['DEVICE_NAME']
            if 'DEVICE_LOCATION' in config_updates:
                self.device_info['device_location'] = config_updates['DEVICE_LOCATION']
        return success
    
    def update_wifi_config(self, config_updates):
        return self.config_mgr.update_section('WiFiConfig', config_updates)
    
    def update_network_config(self, config_updates):
        return self.config_mgr.update_section('NetworkConfig', config_updates)
    
    def update_system_config(self, config_updates):
        return self.config_mgr.update_section('SystemConfig', config_updates)
    
    # Métodos de acesso direto a configurações
    def get_system_config(self):
        return self.config_mgr.get_system_config()
    
    def get_network_config(self):
        return self.config_mgr.get_network_config()
    
    def get_wifi_config(self):
        return self.config_mgr.get_wifi_config()
    
    def get_device_config(self):
        return self.config_mgr.get_device_config()
    
    # Métodos de utilidade
    def health_check(self):
        """Verificar saúde do dispositivo"""
        system_info = self.get_system_info()
        
        health_status = {
            'status': 'HEALTHY',
            'memory_usage': system_info['memory_percent'],
            'uptime': system_info['uptime'],
            'network_status': self.network_status.get('connection_status', 'UNKNOWN'),
            'timestamp': time.time()
        }
        
        # Verificar condições de alerta
        if system_info['memory_percent'] > 80:
            health_status['status'] = 'WARNING'
            health_status['issues'] = ['Memória alta']
        
        if system_info['uptime'] < 10:
            health_status['status'] = 'STARTING'
        
        # Atualizar métricas
        self.system_metrics['health_check_count'] = self.system_metrics.get('health_check_count', 0) + 1
        self.system_metrics['last_health_check'] = time.time()
        
        return health_status
    
    def increment_reset_count(self):
        """Incrementar contador de reset (para debug)"""
        self.system_metrics['reset_count'] += 1
    
    def get_metrics(self):
        """Obter métricas do device manager"""
        return {
            **self.system_metrics,
            'config_stats': self.config_mgr.get_stats(),
            'current_time': time.time()
        }