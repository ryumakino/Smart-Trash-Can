# src/services/device_registry.py - Registro de dispositivos (Corrigido)
import time
import threading
from datetime import datetime, timedelta
from src.core.base_classes import BaseService, ConfigurableMixin

class DeviceRegistry(BaseService, ConfigurableMixin):
    def __init__(self):
        self.connected_devices = {}  # device_id -> device_info
        self.device_lock = threading.Lock()
        self.heartbeat_timeout = 300  # 5 minutos
        
    def register_device(self, device_info, ip_address):
        """Registrar ou atualizar dispositivo"""
        device_id = device_info.get('device_id')
        if not device_id:
            return False
            
        with self.device_lock:
            self.connected_devices[device_id] = {
                **device_info,
                'ip_address': ip_address,
                'connected': True,
                'last_seen': time.time(),
                'first_seen': time.time(),
                'message_count': 0
            }
        return True
    
    def update_heartbeat(self, device_id, heartbeat_data=None):
        """Atualizar heartbeat do dispositivo"""
        with self.device_lock:
            if device_id in self.connected_devices:
                self.connected_devices[device_id]['last_seen'] = time.time()
                self.connected_devices[device_id]['message_count'] += 1
                
                if heartbeat_data:
                    # Atualizar informações adicionais do heartbeat
                    self.connected_devices[device_id].update({
                        'last_heartbeat': time.time(),
                        'uptime': heartbeat_data.get('uptime'),
                        'memory_free': heartbeat_data.get('memory_free'),
                        'network_mode': heartbeat_data.get('network_mode', 'UNKNOWN')
                    })
                return True
        return False
    
    def get_device(self, device_id):
        """Obter informações de um dispositivo específico"""
        with self.device_lock:
            return self.connected_devices.get(device_id, {}).copy()
    
    def get_all_devices(self):
        """Obter todos os dispositivos"""
        with self.device_lock:
            return self.connected_devices.copy()
    
    def get_connected_devices(self):
        """Obter apenas dispositivos conectados"""
        with self.device_lock:
            return {did: info for did, info in self.connected_devices.items() 
                   if info.get('connected', False)}
    
    def disconnect_device(self, device_id):
        """Marcar dispositivo como desconectado"""
        with self.device_lock:
            if device_id in self.connected_devices:
                self.connected_devices[device_id]['connected'] = False
                return True
        return False
    
    def remove_device(self, device_id):
        """Remover dispositivo completamente"""
        with self.device_lock:
            if device_id in self.connected_devices:
                del self.connected_devices[device_id]
                return True
        return False
    
    def broadcast_message(self, devices, message):
        """Enviar mensagem para múltiplos dispositivos"""
        successful = []
        failed = []
        
        for device_id in devices:
            device_info = self.get_device(device_id)
            if device_info and device_info.get('connected'):
                successful.append(device_id)
            else:
                failed.append(device_id)
        
        return {
            'successful': successful,
            'failed': failed,
            'total': len(devices)
        }

    def get_devices_by_network_mode(self, network_mode):
        """Obter dispositivos por modo de rede (STA_MODE, AP_MODE)"""
        return {
            device_id: device_info 
            for device_id, device_info in self.connected_devices.items() 
            if device_info.get('network_mode') == network_mode
        }

    def get_connected_devices(self):
        """Obter apenas dispositivos conectados"""
        return {
            device_id: device_info 
            for device_id, device_info in self.connected_devices.items() 
            if device_info.get('connected', False)
        }

    def get_all_devices(self):
        """Obter todos os dispositivos"""
        return self.connected_devices.copy()

    def update_device_metadata(self, device_id, metadata):
        """Atualizar metadados do dispositivo"""
        if device_id in self.connected_devices:
            if 'metadata' not in self.connected_devices[device_id]:
                self.connected_devices[device_id]['metadata'] = {}
            self.connected_devices[device_id]['metadata'].update(metadata)
            return True
        return False

    def get_devices_with_metadata(self, key, value):
        """Obter dispositivos com metadado específico"""
        result = {}
        for device_id, device_info in self.connected_devices.items():
            metadata = device_info.get('metadata', {})
            if metadata.get(key) == value:
                result[device_id] = device_info
        return result

    def get_device_stats(self):
        """Obter estatísticas dos dispositivos"""
        total_devices = len(self.connected_devices)
        connected_devices = len(self.get_connected_devices())
        sta_devices = len(self.get_devices_by_network_mode('STA_MODE'))
        ap_devices = len(self.get_devices_by_network_mode('AP_MODE'))
        
        return {
            'total_devices': total_devices,
            'connected_devices': connected_devices,
            'sta_devices': sta_devices,
            'ap_devices': ap_devices,
            'unknown_network': total_devices - (sta_devices + ap_devices)
        }

    def cleanup_expired_devices(self, timeout_seconds=300):
        """Limpar dispositivos expirados (5 minutos padrão)"""
        current_time = time.time()
        expired_devices = []
        
        for device_id, device_info in list(self.connected_devices.items()):
            last_seen = device_info.get('last_seen', 0)
            if current_time - last_seen > timeout_seconds:
                expired_devices.append(device_id)
                del self.connected_devices[device_id]
        
        return expired_devices 
    
    def cleanup_disconnected_devices(self, timeout_seconds=None):
        """Compatibilidade: limpar dispositivos desconectados/expirados"""
        if timeout_seconds is None:
            timeout_seconds = self.heartbeat_timeout
        return self.cleanup_expired_devices(timeout_seconds)

    def get_ap_mode_devices(self):
        """Compatibilidade: retornar apenas dispositivos em AP_MODE"""
        return self.get_devices_by_network_mode('AP_MODE')