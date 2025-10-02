# device_registry.py - Registro e gerenciamento de dispositivos ESP32
import time
import threading
from datetime import datetime, timedelta
from utils import get_logger

logger = get_logger("DeviceRegistry")

class DeviceRegistry:
    def __init__(self, device_timeout=300):
        self.devices = {}
        self.device_timeout = device_timeout
        self.lock = threading.Lock()
        
    def register_device(self, device_info, ip_address):
        """Registrar ou atualizar dispositivo"""
        with self.lock:
            device_id = device_info.get('device_id')
            
            if not device_id:
                logger.error("Tentativa de registrar dispositivo sem ID")
                return False
            
            # Verificar se é um novo dispositivo ou atualização
            is_new = device_id not in self.devices
            
            self.devices[device_id] = {
                **device_info,
                'ip_address': ip_address,
                'last_seen': datetime.now(),
                'connected': True,
                'connection_time': datetime.now(),
                'heartbeat_count': self.devices.get(device_id, {}).get('heartbeat_count', 0) + 1
            }
            
            if is_new:
                logger.success(f"Novo dispositivo registrado: {device_info.get('device_name')} ({device_id})")
            else:
                logger.info(f"Dispositivo atualizado: {device_info.get('device_name')} ({device_id})")
            
            return True
    
    def update_heartbeat(self, device_id):
        """Atualizar heartbeat do dispositivo"""
        with self.lock:
            if device_id in self.devices:
                self.devices[device_id]['last_seen'] = datetime.now()
                self.devices[device_id]['heartbeat_count'] += 1
                self.devices[device_id]['connected'] = True
                return True
            return False
    
    def get_device(self, device_id):
        """Obter informações do dispositivo"""
        with self.lock:
            return self.devices.get(device_id)
    
    def get_all_devices(self):
        """Obter todos os dispositivos"""
        with self.lock:
            return self.devices.copy()
    
    def get_connected_devices(self):
        """Obter apenas dispositivos conectados"""
        with self.lock:
            current_time = datetime.now()
            connected_devices = {}
            
            for device_id, device_info in self.devices.items():
                last_seen = device_info.get('last_seen')
                if last_seen and (current_time - last_seen).total_seconds() < self.device_timeout:
                    connected_devices[device_id] = device_info
            
            return connected_devices
    
    def disconnect_device(self, device_id):
        """Desconectar dispositivo"""
        with self.lock:
            if device_id in self.devices:
                self.devices[device_id]['connected'] = False
                logger.info(f"Dispositivo desconectado: {device_id}")
                return True
            return False
    
    def remove_device(self, device_id):
        """Remover dispositivo do registro"""
        with self.lock:
            if device_id in self.devices:
                device_name = self.devices[device_id].get('device_name')
                del self.devices[device_id]
                logger.info(f"Dispositivo removido: {device_name} ({device_id})")
                return True
            return False
    
    def cleanup_expired_devices(self):
        """Limpar dispositivos expirados"""
        with self.lock:
            current_time = datetime.now()
            expired_devices = []
            
            for device_id, device_info in self.devices.items():
                last_seen = device_info.get('last_seen')
                if last_seen and (current_time - last_seen).total_seconds() > self.device_timeout:
                    expired_devices.append(device_id)
            
            for device_id in expired_devices:
                device_name = self.devices[device_id].get('device_name')
                del self.devices[device_id]
                logger.info(f"Dispositivo expirado removido: {device_name} ({device_id})")
            
            return len(expired_devices)
    
    def get_device_stats(self):
        """Obter estatísticas dos dispositivos"""
        with self.lock:
            current_time = datetime.now()
            connected_count = 0
            device_list = []
            
            for device_id, info in self.devices.items():
                last_seen = info.get('last_seen')
                is_connected = last_seen and (current_time - last_seen).total_seconds() < self.device_timeout
                
                if is_connected:
                    connected_count += 1
                
                device_list.append({
                    'device_id': device_id,
                    'device_name': info.get('device_name', 'Unknown'),
                    'device_type': info.get('device_type', 'Unknown'),
                    'location': info.get('location', 'Unknown'),
                    'ip_address': info.get('ip_address'),
                    'connected': is_connected,
                    'last_seen': info.get('last_seen').isoformat() if info.get('last_seen') else 'Never',
                    'connection_duration': str(current_time - info.get('connection_time', current_time)) if info.get('connection_time') else 'Unknown',
                    'heartbeat_count': info.get('heartbeat_count', 0)
                })
            
            return {
                'total_devices': len(self.devices),
                'connected_devices': connected_count,
                'disconnected_devices': len(self.devices) - connected_count,
                'device_list': device_list
            }

# Instância global
DEVICE_REGISTRY = DeviceRegistry()