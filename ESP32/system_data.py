# system_data.py - Modelos de dados para comunicação com Flutter
import ujson as json
import time
from utils import get_logger

logger = get_logger("SystemData")

class SystemDataBuilder:
    """Construtor de dados do sistema para o Flutter"""
    
    @staticmethod
    def build_complete_system_data(device_manager, server_communicator, wifi_manager, system_health):
        """Construir dados completos do sistema"""
        device_info = device_manager.get_device_info()
        network_status = device_manager.get_network_status()
        system_info = device_manager.get_system_info()
        server_info = server_communicator.get_server_info() if server_communicator else {}
        
        return {
            'command': 'SYSTEM_DATA',
            'timestamp': time.time(),
            'device': device_info,
            'network': network_status,
            'system': system_info,
            'server': server_info,
            'sensor': {
                'movement_detected': False,
                'last_movement': 0,
                'enabled': True
            },
            'servo': {
                'current_position': 0,
                'waste_positions': {
                    1: 'Plástico',
                    2: 'Papel',
                    3: 'Metal', 
                    4: 'Vidro'
                }
            },
            'status': {
                'overall': 'OPERATIONAL',
                'wifi_connected': network_status.get('connected', False),
                'server_connected': server_info.get('connected', False) if server_info else False,
                'ap_mode': network_status.get('ap_mode', False)
            }
        }
    
    @staticmethod
    def build_network_data(device_manager, wifi_manager):
        """Construir dados específicos de rede"""
        network_status = device_manager.get_network_status()
        
        return {
            'command': 'WLAN_INFO',
            'timestamp': time.time(),
            'network': network_status,
            'wifi_config': device_manager.get_wifi_config(),
            'connection_status': network_status.get('connection_status', 'DISCONNECTED')
        }
    
    @staticmethod
    def build_hardware_data(device_manager, system_health):
        """Construir dados de hardware"""
        system_info = device_manager.get_system_info()
        
        return {
            'command': 'HARDWARE_INFO',
            'timestamp': time.time(),
            'hardware': {
                'uptime': system_info['uptime'],
                'memory_free': system_info['memory_free'],
                'memory_allocated': system_info['memory_allocated'],
                'memory_free_percent': (system_info['memory_free'] / (system_info['memory_free'] + system_info['memory_allocated'])) * 100,
                'reset_cause': system_info['reset_cause'],
                'cpu_frequency': 240,
                'flash_size': 4096,
                'sdk_version': 'MicroPython 1.19'
            },
            'health': {
                'status': 'HEALTHY' if system_health.check_health() else 'WARNING',
                'last_check': system_health.last_check,
                'memory_status': 'OK' if system_info['memory_free'] > 8000 else 'LOW'
            }
        }
    
    @staticmethod
    def build_discovery_response(device_manager):
        """Construir resposta para discovery do Flutter"""
        device_info = device_manager.get_device_info()
        network_status = device_manager.get_network_status()
        
        return {
            'command': 'DISCOVERY_RESPONSE',
            'device_id': device_info['device_id'],
            'device_name': device_info['device_name'],
            'device_type': device_info['device_type'],
            'firmware_version': device_info['device_version'],
            'mac': device_info.get('mac_address', 'UNKNOWN'),
            'ip': network_status.get('ip', '0.0.0.0'),
            'rssi': network_status.get('rssi', 0),
            'ap_mode': network_status.get('ap_mode', False),
            'connection_status': network_status.get('connection_status', 'DISCONNECTED'),
            'timestamp': time.time()
        }
    
    @staticmethod
    def build_sensor_data(movement_detected=False, last_movement=0):
        """Construir dados do sensor"""
        return {
            'command': 'SENSOR_INFO',
            'timestamp': time.time(),
            'sensor': {
                'movement_detected': movement_detected,
                'last_movement': last_movement,
                'enabled': True,
                'type': 'IR Sensor',
                'cooldown': 2
            }
        }
    
    @staticmethod
    def build_servo_data(current_position=0, waste_type=None):
        """Construir dados do servo"""
        data = {
            'command': 'SERVO_INFO',
            'timestamp': time.time(),
            'servo': {
                'current_position': current_position,
                'waste_positions': {
                    0: 'Repouso',
                    1: 'Plástico (45°)',
                    2: 'Papel (90°)',
                    3: 'Metal (135°)', 
                    4: 'Vidro (180°)'
                },
                'last_movement': time.time()
            }
        }
        
        if waste_type is not None:
            data['servo']['target_waste_type'] = waste_type
            
        return data
    
    @staticmethod
    def build_simple_response(command, status='SUCCESS', message=''):
        """Resposta simples para comandos"""
        return {
            'command': f'{command}_ACK',
            'status': status,
            'message': message,
            'timestamp': time.time()
        }
    
    @staticmethod
    def build_error_response(command, error_message):
        """Resposta de erro"""
        return {
            'command': f'{command}_ERROR',
            'status': 'ERROR',
            'message': error_message,
            'timestamp': time.time()
        }