# server_communicator.py - Comunicação do servidor com ESP32
import socket
import threading
import queue
import time
import json
from datetime import datetime
from security import SecurityManager
from device_registry import DEVICE_REGISTRY
from config_manager import CONFIG_MANAGER
from utils import get_logger

logger = get_logger("ServerCommunicator")

class ServerCommunicator:
    def __init__(self):
        self.config_mgr = CONFIG_MANAGER
        self.network_config = self.config_mgr.get_network_config()
        
        self.udp_port = self.network_config.get('UDP_PORT', 8888)
        self.broadcast_port = self.network_config.get('BROADCAST_PORT', 8889)
        
        # Configurar socket UDP
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.sock.bind(("0.0.0.0", self.udp_port))
        self.sock.settimeout(1.0)
        
        self.security = SecurityManager(
            self.network_config.get('AUTH_KEY'), 
            self.network_config.get('TOKEN_TIMEOUT', 30)
        )
        
        self.running = True
        self.msg_queue = queue.Queue()
        self.heartbeat_interval = self.network_config.get('HEARTBEAT_INTERVAL', 60)
        self.last_heartbeat = 0
        self.messages_processed = 0
        
        # Callback para movimento detectado
        self.movement_callback = None
        
        # Threads
        self.listener_thread = threading.Thread(target=self._listener_loop, daemon=True)
        self.processor_thread = threading.Thread(target=self._processor_loop, daemon=True)
        self.heartbeat_thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
        self.cleanup_thread = threading.Thread(target=self._cleanup_loop, daemon=True)

    def start(self):
        """Iniciar comunicador do servidor"""
        self.listener_thread.start()
        self.processor_thread.start()
        self.heartbeat_thread.start()
        self.cleanup_thread.start()
        self.start_time = time.time()
        logger.info(f"Servidor UDP iniciado na porta {self.udp_port}")

    def stop(self):
        """Parar comunicador do servidor"""
        self.running = False
        try:
            self.sock.close()
        except Exception:
            pass
        logger.info("ServerCommunicator parado")

    def _listener_loop(self):
        """Loop para receber mensagens dos dispositivos"""
        logger.info("Listener do servidor iniciado")
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
                    logger.warning(f"Mensagem inválida de {ip}")
                    
            except socket.timeout:
                continue
            except Exception as e:
                logger.error(f"Erro no listener: {e}")
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
                logger.error(f"Erro no processador: {e}")

    def _handle_message(self, msg, addr):
        """Manipular mensagem recebida do dispositivo"""
        ip = addr[0]
        
        try:
            if msg.startswith("DEVICE_DISCOVERY:"):
                # Mensagem de discovery do dispositivo
                device_info = json.loads(msg.split(":", 1)[1])
                device_id = device_info.get('device_id')
                
                DEVICE_REGISTRY.register_device(device_info, ip)
                self._send_server_response("SERVER_ONLINE", ip)
                logger.info(f"Discovery recebido de {device_info.get('device_name')} ({ip})")
                
            elif msg.startswith("DEVICE_CONNECT:"):
                # Dispositivo tentando conectar
                device_info = json.loads(msg.split(":", 1)[1])
                device_id = device_info.get('device_id')
                
                DEVICE_REGISTRY.register_device(device_info, ip)
                self._send_server_response("SERVER_ONLINE", ip)
                logger.success(f"Dispositivo conectado: {device_info.get('device_name')} ({ip})")
                
            elif msg.startswith("DEVICE_REGISTER:"):
                # Registro formal do dispositivo
                device_info = json.loads(msg.split(":", 1)[1])
                DEVICE_REGISTRY.register_device(device_info, ip)
                logger.info(f"Dispositivo registrado: {device_info.get('device_name')}")
                
            elif msg.startswith("HEARTBEAT:"):
                # Heartbeat do dispositivo
                heartbeat_data = json.loads(msg.split(":", 1)[1])
                device_id = heartbeat_data.get('device_id')
                
                if DEVICE_REGISTRY.update_heartbeat(device_id):
                    logger.debug(f"Heartbeat de {device_id}")
                else:
                    logger.warning(f"Heartbeat de dispositivo não registrado: {device_id}")
                    
            elif msg.startswith("MOVEMENT_DETECTED:"):
                # Movimento detectado pelo dispositivo
                device_id = msg.split(":")[1]
                device_info = DEVICE_REGISTRY.get_device(device_id)
                
                if device_info:
                    logger.info(f"Movimento detectado por {device_info.get('device_name')}")
                    # Acionar callback de movimento
                    if self.movement_callback:
                        self.movement_callback(device_id, ip)
                else:
                    logger.warning(f"Movimento de dispositivo não registrado: {device_id}")
                    
            elif msg.startswith("SYSTEM_STATUS:"):
                # Status do sistema do dispositivo
                status_data = json.loads(msg.split(":", 1)[1])
                device_id = status_data.get('device', {}).get('device_id')
                logger.debug(f"Status recebido de {device_id}")
                
            elif msg.startswith("WASTE_ACK:"):
                # Confirmação de movimento do servo
                parts = msg.split(":")
                device_id = parts[1] if len(parts) > 1 else "unknown"
                status = parts[2] if len(parts) > 2 else "unknown"
                logger.info(f"Confirmação de resíduo do dispositivo {device_id}: {status}")
                
            else:
                logger.info(f"Mensagem não reconhecida de {ip}: {msg}")
                
        except Exception as e:
            logger.error(f"Erro ao processar mensagem de {ip}: {e}")

    def _send_server_response(self, message, ip):
        """Enviar resposta para dispositivo"""
        try:
            encrypted_msg = self.security.encrypt_message(message)
            if encrypted_msg:
                self.sock.sendto(encrypted_msg.encode(), (ip, self.udp_port))
                logger.debug(f"Resposta enviada para {ip}: {message}")
        except Exception as e:
            logger.error(f"Erro ao enviar resposta para {ip}: {e}")

    def send_to_device(self, device_id, message):
        """Enviar mensagem para dispositivo específico"""
        device_info = DEVICE_REGISTRY.get_device(device_id)
        if device_info and device_info.get('connected'):
            ip = device_info.get('ip_address')
            try:
                encrypted_msg = self.security.encrypt_message(message)
                if encrypted_msg:
                    self.sock.sendto(encrypted_msg.encode(), (ip, self.udp_port))
                    logger.debug(f"Mensagem enviada para {device_id} ({ip}): {message}")
                    return True
            except Exception as e:
                logger.error(f"Erro ao enviar para {device_id}: {e}")
                return False
        else:
            logger.warning(f"Tentativa de enviar para dispositivo desconectado: {device_id}")
            return False

    def broadcast_to_devices(self, message):
        """Enviar broadcast para todos os dispositivos"""
        connected_devices = DEVICE_REGISTRY.get_connected_devices()
        success_count = 0
        
        for device_id, device_info in connected_devices.items():
            if self.send_to_device(device_id, message):
                success_count += 1
        
        logger.info(f"Broadcast enviado para {success_count}/{len(connected_devices)} dispositivos")
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
                logger.error(f"Erro no loop de heartbeat: {e}")
                time.sleep(10)

    def _cleanup_loop(self):
        """Loop para limpar dispositivos expirados"""
        while self.running:
            try:
                cleaned_count = DEVICE_REGISTRY.cleanup_expired_devices()
                if cleaned_count > 0:
                    logger.info(f"Dispositivos expirados removidos: {cleaned_count}")
                
                time.sleep(60)  # Verificar a cada minuto
                
            except Exception as e:
                logger.error(f"Erro no loop de cleanup: {e}")
                time.sleep(60)

    def set_movement_callback(self, callback):
        """Definir callback para movimento detectado"""
        self.movement_callback = callback

    def get_communication_stats(self):
        """Obter estatísticas de comunicação"""
        device_stats = DEVICE_REGISTRY.get_device_stats()
        
        return {
            'devices': device_stats,
            'server_uptime': time.time() - self.start_time,
            'messages_processed': self.messages_processed,
            'last_heartbeat': self.last_heartbeat
        }

# Instância global
SERVER_COMMUNICATOR = ServerCommunicator()