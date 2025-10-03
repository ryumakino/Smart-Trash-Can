# server_communicator.py - Comunicação do servidor com ESP32 (Refatorado)
import socket
import threading
import queue
import time
import json
from datetime import datetime
from src.core.base_classes import BaseService, ConfigurableMixin, MessageHandlerMixin

class ServerCommunicator(BaseService, ConfigurableMixin, MessageHandlerMixin):
    def __init__(self):
        super().__init__('network')
        self.udp_port = self.get_config_value('UDP_PORT', 8888)
        self.broadcast_port = self.get_config_value('BROADCAST_PORT', 8889)
        
        # Configurar socket UDP
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.sock.bind(("0.0.0.0", self.udp_port))
        self.sock.settimeout(1.0)
        
        from src.services.security import SecurityManager
        self.security = SecurityManager()
        
        self.running = True
        self.msg_queue = queue.Queue()
        self.heartbeat_interval = self.get_config_value('HEARTBEAT_INTERVAL', 60)
        self.last_heartbeat = 0
        self.messages_processed = 0
        
        # Callback para movimento detectado
        self.movement_callback = None
        
        # Threads
        self.listener_thread = threading.Thread(target=self._listener_loop, daemon=True)
        self.processor_thread = threading.Thread(target=self._processor_loop, daemon=True)
        self.heartbeat_thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
        self.cleanup_thread = threading.Thread(target=self._cleanup_loop, daemon=True)

    def initialize(self):
        """Inicializar comunicador do servidor"""
        if self._initialized:
            return True
            
        try:
            self._initialized = True
            self.logger.success("ServerCommunicator inicializado")
            return True
        except Exception as e:
            self.logger.error(f"Erro na inicialização: {e}")
            return False

    def start(self):
        """Iniciar comunicador do servidor"""
        if not self.initialize():
            return False
            
        self.listener_thread.start()
        self.processor_thread.start()
        self.heartbeat_thread.start()
        self.cleanup_thread.start()
        self.start_time = time.time()
        self.logger.info(f"Servidor UDP iniciado na porta {self.udp_port}")
        return True

    def stop(self):
        """Parar comunicador do servidor"""
        self.running = False
        try:
            self.sock.close()
        except Exception:
            pass
        self.logger.info("ServerCommunicator parado")

    def _listener_loop(self):
        """Loop para receber mensagens dos dispositivos"""
        self.logger.info("Listener do servidor iniciado")
        while self.running:
            try:
                data, addr = self.sock.recvfrom(1024)
                ip = addr[0]
                
                raw_msg = data.decode().strip()
                msg = self.security.decrypt_message(raw_msg)
                
                if msg:
                    self.msg_queue.put((msg, addr))
                    self.messages_processed += 1
                else:
                    self.logger.warning(f"Mensagem inválida de {ip}")
                    
            except socket.timeout:
                continue
            except Exception as e:
                self.logger.error(f"Erro no listener: {e}")
                time.sleep(1)

    def _processor_loop(self):
        """Processar mensagens recebidas"""
        while self.running:
            try:
                msg, addr = self.msg_queue.get(timeout=1.0)
                self._handle_message(msg, addr)
            except queue.Empty:
                continue
            except Exception as e:
                self.logger.error(f"Erro no processador: {e}")

    def _handle_message(self, msg, addr):
        """Manipular mensagem recebida do dispositivo"""
        ip = addr[0]
        
        try:
            from src.core.app_config import get_device_registry
            device_registry = get_device_registry()
            
            # Padrões de mensagem (DRY)
            message_patterns = {
                "DEVICE_DISCOVERY:": lambda m, p, a: self._handle_device_discovery(m, p, a),
                "DEVICE_CONNECT:": lambda m, p, a: self._handle_device_connect(m, p, a),
                "DEVICE_REGISTER:": lambda m, p, a: self._handle_device_register(m, p, a),
                "HEARTBEAT:": lambda m, p, a: self._handle_heartbeat(m, p, a),
                "MOVEMENT_DETECTED:": lambda m, p, a: self._handle_movement(m, p, a),
                "SYSTEM_STATUS:": lambda m, p, a: self._handle_system_status(m, p, a),
                "WASTE_ACK:": lambda m, p, a: self._handle_waste_ack(m, p, a)
            }
            
            result = self.handle_message_pattern(msg, addr, message_patterns)
            if result is None:
                self.logger.info(f"Mensagem não reconhecida de {ip}: {msg}")
                
        except Exception as e:
            self.logger.error(f"Erro ao processar mensagem de {ip}: {e}")

    def _handle_device_discovery(self, msg, prefix, addr):
        """Manipular discovery do dispositivo"""
        ip = addr[0]
        device_info = self.extract_json_payload(msg, prefix)
        if device_info:
            from src.core.app_config import get_device_registry
            device_registry = get_device_registry()
            device_registry.register_device(device_info, ip)
            self._send_server_response("SERVER_ONLINE", ip)
            self.logger.info(f"Discovery recebido de {device_info.get('device_name')} ({ip})")

    def _handle_device_connect(self, msg, prefix, addr):
        """Manipular conexão do dispositivo"""
        ip = addr[0]
        device_info = self.extract_json_payload(msg, prefix)
        if device_info:
            from src.core.app_config import get_device_registry
            device_registry = get_device_registry()
            device_registry.register_device(device_info, ip)
            self._send_server_response("SERVER_ONLINE", ip)
            self.logger.success(f"Dispositivo conectado: {device_info.get('device_name')} ({ip})")

    def _handle_device_register(self, msg, prefix, addr):
        """Manipular registro do dispositivo"""
        ip = addr[0]
        device_info = self.extract_json_payload(msg, prefix)
        if device_info:
            from src.core.app_config import get_device_registry
            device_registry = get_device_registry()
            device_registry.register_device(device_info, ip)
            self.logger.info(f"Dispositivo registrado: {device_info.get('device_name')}")

    def _handle_heartbeat(self, msg, prefix, addr):
        """Manipular heartbeat"""
        ip = addr[0]
        heartbeat_data = self.extract_json_payload(msg, prefix)
        if heartbeat_data:
            from src.core.app_config import get_device_registry
            device_registry = get_device_registry()
            device_id = heartbeat_data.get('device_id')
            
            if device_registry.update_heartbeat(device_id):
                self.logger.debug(f"Heartbeat de {device_id}")
            else:
                self.logger.warning(f"Heartbeat de dispositivo não registrado: {device_id}")

    def _handle_movement(self, msg, prefix, addr):
        """Manipular movimento detectado"""
        ip = addr[0]
        device_id = msg.split(":")[1]
        from src.core.app_config import get_device_registry
        device_registry = get_device_registry()
        device_info = device_registry.get_device(device_id)
        
        if device_info:
            self.logger.info(f"Movimento detectado por {device_info.get('device_name')}")
            if self.movement_callback:
                self.movement_callback(device_id, ip)
        else:
            self.logger.warning(f"Movimento de dispositivo não registrado: {device_id}")

    def _handle_system_status(self, msg, prefix, addr):
        """Manipular status do sistema"""
        ip = addr[0]
        status_data = self.extract_json_payload(msg, prefix)
        if status_data:
            device_id = status_data.get('device', {}).get('device_id')
            self.logger.debug(f"Status recebido de {device_id}")

    def _handle_waste_ack(self, msg, prefix, addr):
        """Manipular confirmação de resíduo"""
        ip = addr[0]
        parts = msg.split(":")
        device_id = parts[1] if len(parts) > 1 else "unknown"
        status = parts[2] if len(parts) > 2 else "unknown"
        self.logger.info(f"Confirmação de resíduo do dispositivo {device_id}: {status}")

    def _send_server_response(self, message, ip):
        """Enviar resposta para dispositivo"""
        try:
            encrypted_msg = self.security.encrypt_message(message)
            if encrypted_msg:
                self.sock.sendto(encrypted_msg.encode(), (ip, self.udp_port))
                self.logger.debug(f"Resposta enviada para {ip}: {message}")
        except Exception as e:
            self.logger.error(f"Erro ao enviar resposta para {ip}: {e}")

    def send_to_device(self, device_id, message):
        """Enviar mensagem para dispositivo específico"""
        from src.core.app_config import get_device_registry
        device_registry = get_device_registry()
        device_info = device_registry.get_device(device_id)
        if device_info and device_info.get('connected'):
            ip = device_info.get('ip_address')
            try:
                encrypted_msg = self.security.encrypt_message(message)
                if encrypted_msg:
                    self.sock.sendto(encrypted_msg.encode(), (ip, self.udp_port))
                    self.logger.debug(f"Mensagem enviada para {device_id} ({ip}): {message}")
                    return True
            except Exception as e:
                self.logger.error(f"Erro ao enviar para {device_id}: {e}")
                return False
        else:
            self.logger.warning(f"Tentativa de enviar para dispositivo desconectado: {device_id}")
            return False

    def broadcast_to_devices(self, message):
        """Enviar broadcast para todos os dispositivos"""
        from src.core.app_config import get_device_registry
        device_registry = get_device_registry()
        connected_devices = device_registry.get_connected_devices()
        success_count = 0
        
        for device_id, device_info in connected_devices.items():
            if self.send_to_device(device_id, message):
                success_count += 1
        
        self.logger.info(f"Broadcast enviado para {success_count}/{len(connected_devices)} dispositivos")
        return success_count

    def _heartbeat_loop(self):
        """Loop para enviar heartbeats periódicos"""
        while self.running:
            try:
                current_time = time.time()
                if current_time - self.last_heartbeat > self.heartbeat_interval:
                    self.broadcast_to_devices("HEARTBEAT_REQUEST")
                    self.last_heartbeat = current_time
                
                time.sleep(10)
                
            except Exception as e:
                self.logger.error(f"Erro no loop de heartbeat: {e}")
                time.sleep(10)

    def _cleanup_loop(self):
        """Loop para limpar dispositivos expirados"""
        while self.running:
            try:
                from src.core.app_config import get_device_registry
                device_registry = get_device_registry()
                cleaned_count = device_registry.cleanup_expired_devices()
                if cleaned_count > 0:
                    self.logger.info(f"Dispositivos expirados removidos: {cleaned_count}")
                
                time.sleep(60)
                
            except Exception as e:
                self.logger.error(f"Erro no loop de cleanup: {e}")
                time.sleep(60)

    def set_movement_callback(self, callback):
        """Definir callback para movimento detectado"""
        self.movement_callback = callback

    def get_communication_stats(self):
        """Obter estatísticas de comunicação"""
        from src.core.app_config import get_device_registry
        device_registry = get_device_registry()
        device_stats = device_registry.get_device_stats()
        
        return {
            'devices': device_stats,
            'server_uptime': time.time() - self.start_time,
            'messages_processed': self.messages_processed,
            'last_heartbeat': self.last_heartbeat
        }