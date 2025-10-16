# server_communicator_refactored.py – DRY + SOLID (TCP-only)
import socket
import threading
import queue
import time
import json
from datetime import datetime
from typing import Dict, List, Optional, Callable
from src.core.app_config import get_device_registry

class ServerCommunicator:
    """TCP-based communicator for ESP32 devices using DeviceRegistry."""

    def __init__(self):
        self._tcp_port = 8889
        self._udp_port = 8888
        self._registry = get_device_registry()
        self._running = True
        self._queue: queue.Queue[tuple[dict, str]] = queue.Queue()
        self._movement_callback = None
        self._classification_callback = None
        self._device_callbacks: Dict[str, List[Callable]] = {}
        
        self._threads = [
            threading.Thread(target=self._tcp_server_loop, daemon=True),
            threading.Thread(target=self._udp_server_loop, daemon=True),
            threading.Thread(target=self._processor_loop, daemon=True),
            threading.Thread(target=self._heartbeat_loop, daemon=True),
            threading.Thread(target=self._cleanup_loop, daemon=True),
        ]
        
        self._local_network = self._detect_local_network()
        self._logger = self._setup_logger()
        self._tcp_sock = self._create_tcp_socket()
        self._udp_sock = self._create_udp_socket()

    # ---------- PUBLIC API (SIMPLIFIED) ---------- #
    def start(self) -> bool:
        """Inicia todos os serviços do comunicador"""
        for t in self._threads:
            t.start()
        self._logger.info(f"🔄 Servidor iniciado - TCP:{self._tcp_port}, UDP:{self._udp_port}")
        return True

    def stop(self):
        """Para todos os serviços do comunicador"""
        self._running = False
        if self._tcp_sock:
            self._tcp_sock.close()
        if self._udp_sock:
            self._udp_sock.close()
        self._logger.info("🛑 Servidor parado")

    def set_movement_callback(self, callback: Callable):
        self._movement_callback = callback

    def set_classification_callback(self, callback: Callable):
        self._classification_callback = callback

    def register_device_callback(self, device_id: str, callback: Callable):
        if device_id not in self._device_callbacks:
            self._device_callbacks[device_id] = []
        self._device_callbacks[device_id].append(callback)

    def send_to_device(self, device_id: str, message: dict) -> bool:
        """Envia mensagem para dispositivo específico via TCP"""
        device = self._registry.get_device(device_id)
        if not device:
            self._logger.error(f"❌ Dispositivo não encontrado: {device_id}")
            return False
        
        ip = device.get('ip_address')
        if not ip:
            self._logger.error(f"❌ IP não disponível para: {device_id}")
            return False

        try:
            message_str = json.dumps(message) + '\n' if isinstance(message, dict) else str(message) + '\n'

            with socket.create_connection((ip, self._tcp_port), timeout=5) as sock:
                sock.sendall(message_str.encode())
            
            self._logger.debug(f"📤 Enviado para {device_id}: {message_str[:100]}...")
            return True
            
        except Exception as e:
            self._logger.error(f"❌ Erro ao enviar para {device_id}: {e}")
            self._registry.disconnect_device(device_id)
            return False

    # ---------- OPERAÇÕES DE DISPOSITIVOS (DELEGADAS AO REGISTRY) ---------- #
    def get_device_info(self, device_id: str) -> dict:
        """Obtém informações completas do dispositivo"""
        return self._registry.get_device(device_id)

    def get_all_devices(self, include_offline: bool = False) -> List[dict]:
        """Lista todos os dispositivos"""
        if include_offline:
            return list(self._registry.get_all_devices().values())
        else:
            return list(self._registry.get_connected_devices().values())

    def update_device_config(self, device_id: str, config: dict) -> bool:
        """Atualiza configuração do dispositivo"""
        success = self._registry.update_device_data(device_id, {'complete_config': config})
        if success:
            # Enviar configuração para o dispositivo
            config_msg = {
                'type': 'CONFIG_UPDATE',
                'device_id': device_id,
                'config': config,
                'timestamp': datetime.now().isoformat()
            }
            return self.send_to_device(device_id, config_msg)
        return False

    def restart_device(self, device_id: str) -> bool:
        """Solicita reinicialização do dispositivo"""
        restart_msg = {
            'type': 'SYSTEM_COMMAND',
            'command': 'RESTART',
            'timestamp': datetime.now().isoformat()
        }
        return self.send_to_device(device_id, restart_msg)

    def control_servo(self, device_id: str, waste_index: int, waste_name: str = "") -> bool:
        """Controla o servo motor do dispositivo"""
        servo_msg = {
            'type': 'WASTE_TYPE',
            'waste_index': waste_index,
            'waste_name': waste_name,
            'timestamp': datetime.now().isoformat()
        }
        return self.send_to_device(device_id, servo_msg)

    def request_device_status(self, device_id: str) -> bool:
        """Solicita status do dispositivo"""
        status_msg = {
            'type': 'SYSTEM_COMMAND',
            'command': 'STATUS',
            'timestamp': datetime.now().isoformat()
        }
        return self.send_to_device(device_id, status_msg)

    def broadcast_to_devices(self, message: dict, device_ids: List[str] = None) -> Dict[str, bool]:
        """Envia mensagem para múltiplos dispositivos"""
        results = {}
        devices = self._registry.get_connected_devices()
        
        if device_ids:
            devices = {did: self._registry.get_device(did) for did in device_ids if did in devices}

        for device_id, device in devices.items():
            if device.get('connected'):
                success = self.send_to_device(device_id, message)
                results[device_id] = {
                    'success': success,
                    'ip': device.get('ip_address'),
                    'timestamp': datetime.now().isoformat()
                }

        self._logger.info(f"📢 Broadcast para {len(devices)} dispositivos")
        return results

    # ---------- MESSAGE HANDLERS (SIMPLIFICADOS) ---------- #
    def _handle_json_message(self, data: dict, ip: str):
        """Processa mensagem JSON recebida"""
        msg_type = data.get('type', 'UNKNOWN').upper()
        device_id = data.get('device_id', 'unknown')
        
        self._logger.info(f"📨 {msg_type} de {device_id} ({ip})")
        
        # Handler específico por tipo
        handler_name = f"_handle_{msg_type.lower()}"
        handler = getattr(self, handler_name, self._handle_unknown)
        handler(data, ip)
        
        # Executar callbacks específicos do dispositivo
        self._execute_device_callbacks(device_id, msg_type, data)

    def _handle_discovery(self, data: dict, ip: str):
        """Processa mensagem de discovery"""
        self._registry.register_device(data, ip)
        
        # Responder ao discovery
        response = {
            'type': 'DISCOVERY_RESPONSE',
            'server_name': 'TrashAI_Server',
            'server_ip': self._local_network + '.1',
            'server_port': self._tcp_port,
            'timestamp': datetime.now().isoformat()
        }
        
        try:
            self._udp_sock.sendto(json.dumps(response).encode(), (ip, self._udp_port))
        except Exception as e:
            self._logger.warning(f"⚠️ Não foi responder ao discovery: {e}")

    def _handle_device_register(self, data: dict, ip: str):
        """Processa registro completo do dispositivo"""
        self._registry.register_device(data, ip)

    def _handle_heartbeat(self, data: dict, ip: str):
        """Processa heartbeat do dispositivo"""
        device_id = data.get('device_id')
        if device_id:
            self._registry.update_heartbeat(device_id, data)

    def _handle_movement_detected(self, data: dict, ip: str):
        """Processa detecção de movimento"""
        device_id = data.get('device_id')
        
        # Executar callback de movimento
        if self._movement_callback:
            try:
                self._movement_callback(device_id, ip, data)
            except Exception as e:
                self._logger.error(f"❌ Erro no callback de movimento: {e}")
        
        # Atualizar no registry
        self._registry.update_heartbeat(device_id, data)

    def _handle_waste_ack(self, data: dict, ip: str):
        """Processa confirmação de movimento do servo"""
        device_id = data.get('device_id')
        self._registry.update_heartbeat(device_id, data)

    def _handle_system_status(self, data: dict, ip: str):
        """Processa status do sistema do dispositivo"""
        device_id = data.get('device_id')
        self._registry.update_heartbeat(device_id, data.get('status', {}))

    def _handle_unknown(self, data: dict, ip: str):
        """Processa mensagem desconhecida"""
        msg_type = data.get('type', 'UNKNOWN')
        self._logger.warning(f"❓ Mensagem não reconhecida: {msg_type}")

    # ---------- SERVER INFRASTRUCTURE (MANTIDO) ---------- #
    def _create_tcp_socket(self) -> socket.socket:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(("", self._tcp_port))
        sock.listen(50)
        sock.settimeout(1.0)
        return sock

    def _create_udp_socket(self) -> socket.socket:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.bind(("", self._udp_port))
        sock.settimeout(1.0)
        return sock

    def _tcp_server_loop(self):
        self._logger.info(f"🔌 TCP aguardando conexões na porta {self._tcp_port}...")
        while self._running:
            try:
                conn, addr = self._tcp_sock.accept()
                client_ip = addr[0]
                threading.Thread(
                    target=self._handle_tcp_client, 
                    args=(conn, client_ip), 
                    daemon=True
                ).start()
            except socket.timeout:
                continue
            except Exception as e:
                if self._running:
                    self._logger.error(f"❌ Erro no accept TCP: {e}")

    def _udp_server_loop(self):
        self._logger.info(f"🔍 UDP escutando na porta {self._udp_port}...")
        while self._running:
            try:
                data, addr = self._udp_sock.recvfrom(1024)
                client_ip = addr[0]
                raw_msg = data.decode().strip()
                
                if raw_msg.startswith('{'):
                    try:
                        msg_data = json.loads(raw_msg)
                        self._queue.put((msg_data, client_ip))
                    except json.JSONDecodeError:
                        self._logger.warning(f"📨 JSON inválido de {client_ip}")
                else:
                    self._handle_simple_udp(raw_msg, client_ip)
                    
            except socket.timeout:
                continue
            except Exception as e:
                if self._running:
                    self._logger.error(f"❌ Erro no servidor UDP: {e}")

    def _handle_tcp_client(self, conn: socket.socket, ip: str):
        buffer = ""
        with conn:
            while self._running:
                try:
                    data = conn.recv(4096)
                    if not data:
                        break
                    
                    buffer += data.decode('utf-8', errors='ignore')
                    
                    while '\n' in buffer:
                        line, buffer = buffer.split('\n', 1)
                        line = line.strip()
                        
                        if line.startswith('{'):
                            try:
                                msg_data = json.loads(line)
                                self._queue.put((msg_data, ip))
                            except json.JSONDecodeError:
                                self._logger.warning(f"📨 JSON TCP inválido de {ip}")
                        else:
                            self._handle_simple_tcp(line, ip)
                            
                except Exception as e:
                    self._logger.error(f"❌ Erro no cliente TCP {ip}: {e}")
                    break

    def _processor_loop(self):
        while self._running:
            try:
                data, ip = self._queue.get(timeout=0.1)
                self._handle_json_message(data, ip)
            except queue.Empty:
                continue
            except Exception as e:
                self._logger.error(f"❌ Erro no processador: {e}")

    def _heartbeat_loop(self):
        while self._running:
            time.sleep(60)
            try:
                connected_devices = self._registry.get_connected_devices()
                for device_id, device in connected_devices.items():
                    if device.get('connected'):
                        heartbeat_msg = {
                            'type': 'HEARTBEAT_REQUEST',
                            'timestamp': datetime.now().isoformat()
                        }
                        success = self.send_to_device(device_id, heartbeat_msg)
                        if not success:
                            self._registry.disconnect_device(device_id)
            except Exception as e:
                self._logger.error(f"❌ Erro no heartbeat loop: {e}")

    def _cleanup_loop(self):
        while self._running:
            time.sleep(120)
            try:
                expired = self._registry.cleanup_expired_devices()
                if expired:
                    self._logger.info(f"🧹 Dispositivos expirados removidos: {len(expired)}")
            except Exception as e:
                self._logger.error(f"❌ Erro no cleanup loop: {e}")

    # ---------- UTILITY METHODS ---------- #
    def _execute_device_callbacks(self, device_id: str, msg_type: str, data: dict):
        if device_id in self._device_callbacks:
            for callback in self._device_callbacks[device_id]:
                try:
                    callback(device_id, msg_type, data)
                except Exception as e:
                    self._logger.error(f"❌ Erro no callback do {device_id}: {e}")

    def _handle_simple_tcp(self, raw: str, ip: str):
        cmd = raw.upper().strip()
        if cmd in ('STATUS', 'HELP', 'RESTART', 'PING'):
            self._queue.put(({
                'type': 'SERIAL_COMMAND', 
                'command': cmd, 
                'timestamp': datetime.now().isoformat()
            }, ip))

    def _handle_simple_udp(self, raw: str, ip: str):
        cmd = raw.upper().strip()
        if cmd in ('DISCOVERY', 'PING'):
            self._queue.put(({
                'type': 'DISCOVERY',
                'timestamp': datetime.now().isoformat()
            }, ip))

    def _detect_local_network(self) -> str:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.connect(("8.8.8.8", 80))
                return ".".join(s.getsockname()[0].split(".")[:3])
        except:
            return "192.168.1"

    def _setup_logger(self):
        class Logger:
            def info(self, msg): print(f"[INFO] {msg}")
            def error(self, msg): print(f"[ERROR] {msg}")
            def debug(self, msg): print(f"[DEBUG] {msg}")
            def warning(self, msg): print(f"[WARNING] {msg}")
        return Logger()

    # ---------- STATISTICS ---------- #
    def get_communication_stats(self) -> dict:
        stats = self._registry.get_device_stats()
        stats.update({
            'local_network': self._local_network,
            'tcp_port': self._tcp_port,
            'udp_port': self._udp_port,
            'server_running': self._running
        })
        return stats

    def get_detailed_stats(self) -> dict:
        return self._registry.get_device_stats()