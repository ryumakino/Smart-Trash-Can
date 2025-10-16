# device_registry_refactored.py – DRY + SOLID
import time
import threading
from datetime import datetime
from typing import Dict, List, Optional
from src.core.base_classes import BaseService, ConfigurableMixin
from src.core.app_config import get_database

class DeviceRegistry(BaseService, ConfigurableMixin):
    def __init__(self):
        super().__init__('device')
        self._devices: Dict[str, dict] = {}
        self._lock = threading.RLock()  # Changed to RLock for nested operations
        self._timeout = 300  # 5 min
        self._db = get_database()

    # ---------- CORE DEVICE OPERATIONS ---------- #
    def register_device(self, info: dict, ip: str) -> bool:
        """Registra ou atualiza um dispositivo com informações completas"""
        device_id = info.get('device_id') or info.get('device_info', {}).get('device_id')
        if not device_id:
            self.logger.error("❌ Device ID não encontrado no registro")
            return False
        
        try:
            with self._lock:
                current_time = time.time()
                iso_time = datetime.now().isoformat()
                
                # Preparar dados completos do dispositivo
                device_data = {
                    # Informações básicas
                    'device_id': device_id,
                    'ip_address': ip,
                    'connected': True,
                    'last_seen': current_time,
                    'last_seen_iso': iso_time,
                    'message_count': 0,
                    
                    # Informações do dispositivo
                    'device_info': info.get('device_info', {}),
                    
                    # Configurações completas
                    'complete_config': info.get('complete_config', {}),
                    
                    # Status de comunicação
                    'communication_status': info.get('communication_status', {}),
                    
                    # Informações de hardware
                    'hardware_info': info.get('hardware_info', {}),
                    
                    # Métricas do sistema
                    'system_metrics': info.get('system_metrics', {}),
                    
                    # Informações de rede
                    'network_info': info.get('network', {})
                }
                
                # Se já existe, manter alguns dados históricos
                if device_id in self._devices:
                    existing = self._devices[device_id]
                    device_data['first_seen'] = existing.get('first_seen', current_time)
                    device_data['message_count'] = existing.get('message_count', 0) + 1
                    device_data['total_messages'] = existing.get('total_messages', 0) + 1
                else:
                    device_data['first_seen'] = current_time
                    device_data['first_seen_iso'] = iso_time
                    device_data['total_messages'] = 1
                
                # Atualizar no registry local
                self._devices[device_id] = device_data
                
                # Salvar no banco de dados
                self._save_to_database(device_data, 'online')
                
                self.logger.info(f"📝 Dispositivo registrado: {device_id} ({ip})")
                return True
                
        except Exception as e:
            self.logger.error(f"❌ Erro ao registrar dispositivo: {e}")
            return False

    def update_heartbeat(self, device_id: str, data: dict | None = None) -> bool:
        """Atualiza heartbeat e informações do dispositivo"""
        with self._lock:
            if device_id not in self._devices:
                self.logger.warning(f"⚠️ Dispositivo não encontrado para heartbeat: {device_id}")
                return False
            
            try:
                dev = self._devices[device_id]
                current_time = time.time()
                
                # Atualizar informações básicas
                dev['last_seen'] = current_time
                dev['last_seen_iso'] = datetime.now().isoformat()
                dev['message_count'] = dev.get('message_count', 0) + 1
                dev['total_messages'] = dev.get('total_messages', 0) + 1
                dev['connected'] = True
                
                # Atualizar com dados fornecidos
                if data:
                    # Informações de sistema
                    if 'uptime' in data:
                        dev['uptime'] = data.get('uptime')
                    if 'memory_free' in data:
                        dev['memory_free'] = data.get('memory_free')
                    if 'network_mode' in data:
                        dev['network_mode'] = data.get('network_mode')
                    
                    # Status de comunicação
                    if 'communication_status' in data:
                        dev['communication_status'] = data['communication_status']
                    
                    # Métricas do sistema
                    if 'system_metrics' in data:
                        dev['system_metrics'] = data['system_metrics']
                
                # Atualizar no banco
                self._update_in_database(device_id, 'online', dev)
                
                return True
                
            except Exception as e:
                self.logger.error(f"❌ Erro ao atualizar heartbeat: {e}")
                return False

    def update_device_data(self, device_id: str, updates: dict) -> bool:
        """Atualiza dados específicos do dispositivo"""
        with self._lock:
            if device_id not in self._devices:
                return False
            
            try:
                self._devices[device_id].update(updates)
                
                # Atualizar no banco se necessário
                if self._db and any(key in updates for key in [
                    'device_info', 'complete_config', 'hardware_info', 
                    'system_metrics', 'network_info'
                ]):
                    self._save_to_database(self._devices[device_id], 'online')
                
                return True
            except Exception as e:
                self.logger.error(f"❌ Erro ao atualizar dados do dispositivo: {e}")
                return False

    # ---------- DEVICE QUERIES ---------- #
    def get_device(self, device_id: str) -> dict:
        """Obtém dispositivo com informações completas"""
        with self._lock:
            device = self._devices.get(device_id, {}).copy()
            
            # Se não encontrou no registry, tenta no banco
            if not device and self._db:
                db_device = self._db.get_device(device_id)
                if db_device:
                    device = db_device
                    # Adicionar ao cache do registry
                    self._devices[device_id] = device
            
            return device

    def get_all_devices(self) -> Dict[str, dict]:
        """Obtém todos os dispositivos"""
        with self._lock:
            return {k: v.copy() for k, v in self._devices.items()}

    def get_connected_devices(self) -> Dict[str, dict]:
        """Obtém apenas dispositivos conectados"""
        with self._lock:
            return {
                k: v.copy() for k, v in self._devices.items() 
                if v.get('connected', False)
            }

    def get_devices_by_status(self, status: str) -> Dict[str, dict]:
        """Filtra dispositivos por status"""
        with self._lock:
            return {
                k: v.copy() for k, v in self._devices.items() 
                if v.get('status') == status
            }

    def get_devices_by_network_mode(self, mode: str) -> Dict[str, dict]:
        """Filtra dispositivos por modo de rede"""
        with self._lock:
            return {
                k: v.copy() for k, v in self._devices.items() 
                if v.get('network_info', {}).get('mode') == mode
            }

    # ---------- DEVICE MANAGEMENT ---------- #
    def disconnect_device(self, device_id: str) -> bool:
        """Marca dispositivo como desconectado"""
        with self._lock:
            if device_id in self._devices:
                self._devices[device_id]['connected'] = False
                self._devices[device_id]['status'] = 'offline'
                
                # Atualizar no banco
                self._update_in_database(device_id, 'offline')
                
                self.logger.info(f"🔌 Dispositivo desconectado: {device_id}")
                return True
            return False

    def remove_device(self, device_id: str) -> bool:
        """Remove completamente um dispositivo"""
        with self._lock:
            if device_id in self._devices:
                # Marcar como removido no banco
                if self._db:
                    self._db.update_device_status(device_id, 'removed')
                
                del self._devices[device_id]
                self.logger.info(f"🗑️ Dispositivo removido: {device_id}")
                return True
            return False

    def cleanup_expired_devices(self, timeout: int | None = None) -> List[str]:
        """Limpa dispositivos expirados"""
        timeout = timeout or self._timeout
        expired = []
        now = time.time()
        
        with self._lock:
            for device_id, info in list(self._devices.items()):
                if now - info.get('last_seen', 0) > timeout:
                    # Marcar como offline no banco
                    self._update_in_database(device_id, 'offline')
                    
                    expired.append(device_id)
                    del self._devices[device_id]
        
        if expired:
            self.logger.info(f"🧹 Dispositivos expirados removidos: {len(expired)}")
        
        return expired

    # ---------- STATISTICS AND ANALYTICS ---------- #
    def get_device_stats(self) -> dict:
        """Estatísticas gerais dos dispositivos"""
        with self._lock:
            total = len(self._devices)
            connected = len(self.get_connected_devices())
            sta = len(self.get_devices_by_network_mode('STA'))
            ap = len(self.get_devices_by_network_mode('AP'))
            
            # Calcular estatísticas de mensagens
            total_messages = sum(dev.get('total_messages', 0) for dev in self._devices.values())
            avg_messages = total_messages / total if total > 0 else 0
            
            return {
                'total_devices': total,
                'connected_devices': connected,
                'disconnected_devices': total - connected,
                'sta_devices': sta,
                'ap_devices': ap,
                'unknown_network': total - (sta + ap),
                'total_messages': total_messages,
                'avg_messages_per_device': round(avg_messages, 2),
                'last_cleanup': datetime.now().isoformat()
            }

    def get_device_communication_stats(self, device_id: str) -> dict:
        """Estatísticas de comunicação específicas do dispositivo"""
        device = self.get_device(device_id)
        if not device:
            return {}
        
        return {
            'device_id': device_id,
            'message_count': device.get('message_count', 0),
            'total_messages': device.get('total_messages', 0),
            'last_seen': device.get('last_seen_iso'),
            'first_seen': device.get('first_seen_iso'),
            'uptime': device.get('uptime'),
            'memory_free': device.get('memory_free'),
            'network_mode': device.get('network_info', {}).get('mode', 'UNKNOWN'),
            'ip_address': device.get('ip_address')
        }

    def get_recently_active_devices(self, hours: int = 24) -> List[dict]:
        """Dispositivos ativos recentemente"""
        cutoff = time.time() - (hours * 3600)
        
        with self._lock:
            recent_devices = [
                dev.copy() for dev in self._devices.values()
                if dev.get('last_seen', 0) > cutoff
            ]
            
            # Ordenar por último contato
            recent_devices.sort(key=lambda x: x.get('last_seen', 0), reverse=True)
            return recent_devices

    # ---------- DATABASE INTEGRATION ---------- #
    def _save_to_database(self, device_data: dict, status: str):
        """Salva dispositivo no banco de dados"""
        if not self._db:
            return
        
        try:
            # Preparar dados para o banco
            db_data = {
                'device_id': device_data['device_id'],
                'ip_address': device_data.get('ip_address'),
                'status': status,
                'last_seen': device_data.get('last_seen_iso'),
                'first_seen': device_data.get('first_seen_iso'),
                
                # Informações completas
                'device_info': device_data.get('device_info', {}),
                'complete_config': device_data.get('complete_config', {}),
                'communication_status': device_data.get('communication_status', {}),
                'hardware_info': device_data.get('hardware_info', {}),
                'system_metrics': device_data.get('system_metrics', {}),
                'network_info': device_data.get('network_info', {}),
                
                # Estatísticas
                'message_count': device_data.get('message_count', 0),
                'total_messages': device_data.get('total_messages', 0),
                'uptime': device_data.get('uptime'),
                'memory_free': device_data.get('memory_free')
            }
            
            success = self._db.save_device(db_data)
            if not success:
                self.logger.warning(f"⚠️ Falha ao salvar dispositivo {device_data['device_id']} no banco")
                
        except Exception as e:
            self.logger.error(f"❌ Erro ao salvar no banco: {e}")

    def _update_in_database(self, device_id: str, status: str, data: dict = None):
        """Atualiza dispositivo no banco de dados"""
        if not self._db:
            return
        
        try:
            update_data = {
                'device_id': device_id,
                'status': status,
                'last_seen': datetime.now().isoformat()
            }
            
            if data:
                update_data.update({
                    'message_count': data.get('message_count'),
                    'total_messages': data.get('total_messages'),
                    'uptime': data.get('uptime'),
                    'memory_free': data.get('memory_free'),
                    'network_mode': data.get('network_info', {}).get('mode')
                })
            
            self._db.save_device(update_data)
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao atualizar no banco: {e}")

    def load_devices_from_database(self):
        """Carrega dispositivos do banco para o registry"""
        if not self._db:
            return
        
        try:
            devices = self._db.get_online_devices()
            with self._lock:
                for device in devices:
                    device_id = device.get('device_id')
                    if device_id:
                        # Converter para formato do registry
                        self._devices[device_id] = {
                            **device,
                            'connected': device.get('status') == 'online',
                            'last_seen': time.time()  # Atualizar timestamp
                        }
            
            self.logger.info(f"📂 Carregados {len(devices)} dispositivos do banco")
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao carregar dispositivos do banco: {e}")

    # ---------- SERVICE LIFECYCLE ---------- #
    def initialize(self) -> bool:
        """Inicializa o registry"""
        if self._initialized:
            return True
        
        try:
            # Carregar dispositivos do banco
            self.load_devices_from_database()
            
            self._initialized = True
            self.logger.success("✅ Device Registry inicializado")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Falha na inicialização do Device Registry: {e}")
            return False

    def get_status(self) -> dict:
        """Status do serviço"""
        base_status = super().get_status()
        stats = self.get_device_stats()
        
        base_status.update({
            'device_count': stats['total_devices'],
            'connected_count': stats['connected_devices'],
            'stats': stats,
            'database_available': self._db is not None
        })
        
        return base_status