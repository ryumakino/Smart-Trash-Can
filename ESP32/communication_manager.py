# communication_manager.py
import uasyncio as asyncio
import ujson as json
import time
import machine
import usocket as socket
from utils import get_logger
from security import SecurityManager, AuthenticationManager

logger = get_logger("CommunicationManager")

class CommunicationManager:
    """Gerenciador unificado de comunicação - Responsabilidade Centralizada"""
    
    def __init__(self, device_manager, hardware_manager):
        self.device_manager = device_manager
        self.hardware_manager = hardware_manager
        
        # Componentes de comunicação
        self.udp_communicator = UDPCommunicator(self.device_manager)
        self.server_communicator = ServerCommunicator(
            self.udp_communicator,
            self.device_manager,
            self.hardware_manager.get_component('servo')
        )
        self.flutter_communicator = FlutterCommunicator(
            self.udp_communicator,
            self.device_manager,
            self.server_communicator,
            self.hardware_manager.get_component('servo')
        )
        
        # Estado
        self.running = False
        
        logger.info("CommunicationManager inicializado")

    async def start_communication(self):
        """Iniciar todos os serviços de comunicação"""
        try:
            await self.udp_communicator.start()
            await self.server_communicator.start()
            self.running = True
            logger.info("Serviços de comunicação iniciados")
        except Exception as e:
            logger.error(f"Erro ao iniciar comunicação: {e}")
            raise

    async def handle_incoming_message(self, msg, addr):
        """Processar mensagem recebida de forma unificada"""
        try:
            # Primeiro tentar processar como mensagem do Flutter
            flutter_handled = await self.flutter_communicator.handle_message(msg, addr)
            if flutter_handled:
                return True
                
            # Depois tentar como mensagem do servidor
            server_handled = await self.server_communicator.handle_message(msg, addr)
            if server_handled:
                return True
                
            logger.debug(f"Mensagem não processada de {addr}: {msg[:50]}...")
            return False
            
        except Exception as e:
            logger.error(f"Erro no processamento de mensagem: {e}")
            return False

    def stop_communication(self):
        """Parar todos os serviços de comunicação"""
        self.running = False
        self.udp_communicator.stop()
        logger.info("Serviços de comunicação parados")

    def get_communication_status(self):
        """Obter status da comunicação"""
        return {
            'udp': {
                'running': self.udp_communicator.running,
                'port': self.udp_communicator.port,
                'messages_queued': self.udp_communicator.msg_queue.qsize() if hasattr(self.udp_communicator.msg_queue, 'qsize') else 0
            },
            'server': {
                'connected': self.server_communicator.is_connected(),
                'server_ip': self.server_communicator.server_ip,
                'connection_duration': self.server_communicator.get_connection_duration()
            },
            'flutter': {
                'active_sessions': len(self.flutter_communicator.auth_manager.authenticated_clients),
                'sensor_enabled': self.flutter_communicator.sensor_enabled
            },
            'overall': 'RUNNING' if self.running else 'STOPPED'
        }


class UDPCommunicator:
    """Comunicador UDP refatorado"""
    
    def __init__(self, device_manager):
        self.device_manager = device_manager
        self.config_mgr = device_manager.get_config_manager()
        network_config = self.config_mgr.get_network_config()
        
        self.port = network_config.get('UDP_PORT', 8888)
        self.broadcast_port = network_config.get('BROADCAST_PORT', 8889)
        self.sock = self._setup_socket()
        
        # Configurações de segurança
        self.security = SecurityManager(
            network_config.get('AUTH_KEY'), 
            network_config.get('TOKEN_TIMEOUT', 30)
        )
        
        # Estado do comunicador
        self.running = True
        self.msg_queue = asyncio.Queue()
        self.last_broadcast = 0
        self.broadcast_interval = network_config.get('DISCOVERY_INTERVAL', 30)

    def _setup_socket(self):
        """Configurar socket UDP"""
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.bind(("0.0.0.0", self.port))
        return sock

    async def start(self):
        """Iniciar comunicador UDP"""
        loop = asyncio.get_event_loop()
        loop.create_task(self._listener())
        loop.create_task(self._broadcast_discovery())
        logger.info(f"UDPCommunicator iniciado na porta {self.port}")

    def stop(self):
        """Parar comunicador UDP"""
        self.running = False
        try:
            self.sock.close()
        except Exception:
            pass
        logger.info("UDPCommunicator parado")

    async def _listener(self):
        """Task para escutar mensagens UDP"""
        logger.info(f"UDP Listener ativo na porta {self.port}")
        while self.running:
            try:
                data, addr = self.sock.recvfrom(1024)
                await self._process_received_message(data, addr)
            except OSError:
                await asyncio.sleep(0.05)
                continue
            except Exception as e:
                logger.error(f"Erro no listener: {e}")
                await asyncio.sleep(1)

    async def _process_received_message(self, data, addr):
        """Processar mensagem recebida"""
        try:
            raw_msg = data.decode().strip()
            msg = self.security.decrypt_message(raw_msg)
            
            if not msg:
                logger.warning(f"Mensagem inválida de {addr}")
                return
                
            await self.msg_queue.put((msg, addr))
            logger.debug(f"Mensagem recebida de {addr}: {msg[:50]}...")
            
        except Exception as e:
            logger.error(f"Erro ao processar mensagem: {e}")

    async def _broadcast_discovery(self):
        """Task para broadcast periódico de discovery"""
        logger.info("Iniciando broadcast de discovery...")
        while self.running:
            try:
                current_time = time.time()
                if current_time - self.last_broadcast > self.broadcast_interval:
                    await self._send_broadcast_message()
                    self.last_broadcast = current_time
                    
                await asyncio.sleep(5)
                
            except Exception as e:
                logger.error(f"Erro no broadcast: {e}")
                await asyncio.sleep(10)

    async def _send_broadcast_message(self):
        """Enviar mensagem de broadcast"""
        broadcast_data = self.device_manager.get_broadcast_message()
        broadcast_msg = json.dumps(broadcast_data)
        
        await self.send_message_async(broadcast_msg, "255.255.255.255", self.broadcast_port)
        logger.debug("Broadcast de discovery enviado")

    async def send_message_async(self, message, ip="255.255.255.255", port=None):
        """Enviar mensagem de forma assíncrona"""
        try:
            target_port = port or self.port
            encrypted = self.security.encrypt_message(message)
            self.sock.sendto(encrypted.encode(), (ip, target_port))
            logger.debug(f"Enviado para {ip}:{target_port}")
        except Exception as e:
            logger.error(f"Erro ao enviar mensagem: {e}")

    def send_message(self, message, ip="255.255.255.255", port=None):
        """Enviar mensagem de forma síncrona"""
        try:
            target_port = port or self.port
            encrypted = self.security.encrypt_message(message)
            self.sock.sendto(encrypted.encode(), (ip, target_port))
            logger.debug(f"Enviado para {ip}:{target_port}")
        except Exception as e:
            logger.error(f"Erro ao enviar mensagem: {e}")


class ServerCommunicator:
    """Comunicador com servidor central refatorado"""
    
    def __init__(self, udp_communicator, device_manager, servo_controller=None):
        self.udp = udp_communicator
        self.device_manager = device_manager
        self.servo_controller = servo_controller
        self.config_mgr = device_manager.get_config_manager()
        self.network_config = self.config_mgr.get_network_config()
        
        self.server_ip = self.network_config.get('SERVER_IP')
        self.server_port = self.network_config.get('SERVER_PORT', 8888)
        self.auto_discover = self.network_config.get('AUTO_DISCOVER_SERVER', True)
        
        self.connected = False
        self.connection_time = 0
        self.last_heartbeat = 0
        self.heartbeat_interval = 60

    async def start(self):
        """Iniciar comunicação com servidor"""
        logger.info("Iniciando comunicação com servidor...")
        
        if self.server_ip and not self.auto_discover:
            await self.connect_to_server(self.server_ip)
        else:
            await self.discover_server()

    async def connect_to_server(self, server_ip):
        """Conectar a um servidor específico"""
        try:
            device_info = self.device_manager.get_device_info()
            connection_msg = f"DEVICE_CONNECT:{json.dumps(device_info)}"
            
            await self.udp.send_message_async(connection_msg, ip=server_ip)
            logger.info(f"Tentando conectar ao servidor: {server_ip}")
            
            await asyncio.sleep(2)
            
        except Exception as e:
            logger.error(f"Erro ao conectar com servidor {server_ip}: {e}")

    async def discover_server(self):
        """Descobrir servidor automaticamente na rede"""
        logger.info("Procurando servidor na rede...")
        
        network_status = self.device_manager.get_network_status()
        network_prefix = self._get_network_prefix(network_status)
        if not network_prefix:
            return
        
        # Tentar IPs comuns de servidor
        server_ips = [
            f"{network_prefix}.1",    # Gateway
            f"{network_prefix}.100",  # IP comum para servidores
            f"{network_prefix}.50",   # Outro IP comum
            f"{network_prefix}.200",  # Possível servidor
            "255.255.255.255"         # Broadcast
        ]
        
        # Adicionar IP específico se configurado
        if self.server_ip:
            server_ips.insert(0, self.server_ip)
        
        for server_ip in server_ips:
            await self.connect_to_server(server_ip)
            await asyncio.sleep(0.5)

    async def handle_message(self, msg, addr):
        """Processar mensagem do servidor"""
        try:
            if msg.startswith('SERVER_ONLINE'):
                await self._handle_server_online(msg, addr)
            elif msg.startswith('WASTE_TYPE'):
                await self._handle_waste_type(msg, addr)
            elif msg.startswith('HEARTBEAT_REQUEST'):
                await self._handle_heartbeat_request(msg, addr)
            elif msg.startswith('SYSTEM_COMMAND'):
                await self._handle_system_command(msg, addr)
            else:
                return False
                
            return True
            
        except Exception as e:
            logger.error(f"Erro ao processar mensagem do servidor: {e}")
            return False

    async def _handle_server_online(self, msg, addr):
        """Servidor respondeu que está online"""
        server_ip = addr[0] if isinstance(addr, tuple) else addr
        
        if not self.connected or server_ip != self.server_ip:
            self.server_ip = server_ip
            self.connected = True
            self.connection_time = time.time()
            
            device_info = self.device_manager.get_device_info()
            await self.udp.send_message_async(
                f"DEVICE_REGISTER:{json.dumps(device_info)}", 
                ip=self.server_ip
            )
            
            logger.success(f"Conectado ao servidor: {self.server_ip}")

    async def _handle_waste_type(self, msg, addr):
        """Processar comando de tipo de resíduo"""
        try:
            parts = msg.split(":")
            if len(parts) >= 2:
                waste_index = int(parts[1])
                waste_name = parts[2] if len(parts) > 2 else f"Tipo {waste_index}"
                
                logger.info(f"Comando do servidor: Mover para {waste_name}")
                
                # Executar movimento do servo se disponível
                if self.servo_controller:
                    servo_config = self.device_manager.get_config_manager().get_servo_config()
                    success = await self.servo_controller.move_to_waste(waste_index, servo_config)
                    ack_status = 'SUCCESS' if success else 'ERROR'
                else:
                    ack_status = 'NO_SERVO'
                
                # Enviar confirmação
                ack_msg = f"WASTE_ACK:{waste_index}:{ack_status}"
                await self.udp.send_message_async(ack_msg, ip=addr[0])
                    
        except Exception as e:
            logger.error(f"Erro ao processar waste type: {e}")
            await self.udp.send_message_async(f"WASTE_ACK:0:ERROR", ip=addr[0])

    async def _handle_heartbeat_request(self, msg, addr):
        """Responder a heartbeat do servidor"""
        await self.send_heartbeat()

    async def _handle_system_command(self, msg, addr):
        """Executar comandos de sistema"""
        try:
            parts = msg.split(":")
            command = parts[1] if len(parts) > 1 else ""
            
            if command == "STATUS":
                await self.send_system_status(addr[0])
            elif command == "RESTART":
                logger.info("Reiniciando por comando do servidor...")
                await self.udp.send_message_async("RESTART_ACK", ip=addr[0])
                await asyncio.sleep(2)
                machine.reset()
                
        except Exception as e:
            logger.error(f"Erro ao executar comando: {e}")

    async def send_heartbeat(self):
        """Enviar heartbeat para o servidor"""
        if self.connected:
            try:
                system_status = self._get_system_status()
                heartbeat_msg = f"HEARTBEAT:{json.dumps(system_status)}"
                await self.udp.send_message_async(heartbeat_msg, ip=self.server_ip)
                self.last_heartbeat = time.time()
            except Exception as e:
                logger.error(f"Erro ao enviar heartbeat: {e}")
                self.connected = False

    async def send_system_status(self, target_ip=None):
        """Enviar status completo do sistema"""
        ip = target_ip or self.server_ip
        if self.connected or target_ip:
            system_status = self._get_system_status()
            status_msg = f"SYSTEM_STATUS:{json.dumps(system_status)}"
            await self.udp.send_message_async(status_msg, ip=ip)

    async def send_movement_detected(self):
        """Enviar notificação de movimento detectado"""
        if self.connected:
            device_id = self.device_manager.get_device_id()
            movement_msg = f"MOVEMENT_DETECTED:{device_id}"
            await self.udp.send_message_async(movement_msg, ip=self.server_ip)

    def _get_system_status(self):
        """Obter status do sistema para relatórios"""
        system_info = self.device_manager.get_system_info()
        device_info = self.device_manager.get_device_info()
        
        return {
            'device': device_info,
            'system': system_info,
            'server_connected': self.connected,
            'server_ip': self.server_ip,
            'uptime': system_info['uptime'],
            'memory_free_percent': (system_info['memory_free'] / 
                                  (system_info['memory_free'] + system_info['memory_allocated'])) * 100,
            'connection_duration': time.time() - self.connection_time if self.connected else 0
        }

    def _get_network_prefix(self, network_status):
        """Obter prefixo da rede"""
        ip = network_status.get('ip')
        ap_mode = network_status.get('ap_mode', False)
        
        if ap_mode:
            return "192.168.4"
        elif ip:
            parts = ip.split(".")
            if len(parts) == 4:
                return ".".join(parts[:3])
        
        return "192.168.1"

    async def maintenance_task(self):
        """Task de manutenção da conexão com servidor"""
        while True:
            try:
                # Verificar se precisa enviar heartbeat
                current_time = time.time()
                if (self.connected and 
                    current_time - self.last_heartbeat > self.heartbeat_interval):
                    await self.send_heartbeat()
                
                # Verificar se precisa reconectar
                if not self.connected and self.auto_discover:
                    await self.discover_server()
                
                await asyncio.sleep(10)
                
            except Exception as e:
                logger.error(f"Erro na task de manutenção: {e}")
                await asyncio.sleep(10)

    def is_connected(self):
        return self.connected

    def get_server_info(self):
        return {
            'connected': self.connected,
            'server_ip': self.server_ip,
            'connection_duration': time.time() - self.connection_time if self.connected else 0,
            'last_heartbeat': self.last_heartbeat
        }
    
    def get_connection_duration(self):
        return time.time() - self.connection_time if self.connected else 0


class FlutterCommunicator:
    """Comunicador com Flutter refatorado"""
    
    def __init__(self, udp_communicator, device_manager, server_communicator=None, servo_controller=None):
        self.udp = udp_communicator
        self.device_manager = device_manager
        self.server_communicator = server_communicator
        self.servo_controller = servo_controller
        
        # Sistema de autenticação
        network_config = device_manager.get_network_config()
        self.security = SecurityManager(
            network_config.get('AUTH_KEY'),
            network_config.get('TOKEN_TIMEOUT', 30)
        )
        self.auth_manager = AuthenticationManager(self.security)
        
        # Estado
        self.sensor_enabled = True
        self.last_movement_time = 0

    async def handle_message(self, msg, addr):
        """Processar mensagens do Flutter"""
        try:
            client_ip = addr[0] if isinstance(addr, tuple) else addr
            
            # Tentar descriptografar
            decrypted_msg = self.security.decrypt_message(msg)
            if decrypted_msg is None:
                decrypted_msg = msg
            
            # Processar comando
            if decrypted_msg.startswith('GET_ALL_INFO'):
                await self._send_all_info(addr)
            elif decrypted_msg.startswith('PING'):
                await self._send_ping_response(addr)
            elif decrypted_msg.startswith('SET_SERVO_ANGLE'):
                await self._handle_set_servo_angle(decrypted_msg, addr)
            elif decrypted_msg.startswith('SET_WASTE_TYPE'):
                await self._handle_set_waste_type(decrypted_msg, addr)
            elif decrypted_msg.startswith('TOGGLE_SENSOR'):
                await self._handle_toggle_sensor(addr)
            elif decrypted_msg.startswith('RESTART_SYSTEM'):
                await self._handle_restart_system(addr)
            else:
                return False
                
            return True
            
        except Exception as e:
            logger.error(f"Erro ao processar mensagem do Flutter: {e}")
            return False

    async def _send_all_info(self, addr):
        """Enviar todas as informações para o Flutter"""
        try:
            device_info = self.device_manager.get_device_info()
            network_status = self.device_manager.get_network_status()
            system_info = self.device_manager.get_system_info()
            server_info = self.server_communicator.get_server_info() if self.server_communicator else {}
            
            data = {
                'command': 'SYSTEM_DATA',
                'timestamp': time.time(),
                'device': device_info,
                'network': network_status,
                'system': system_info,
                'server': server_info,
                'sensor': {
                    'enabled': self.sensor_enabled,
                    'last_movement': self.last_movement_time
                },
                'servo': self.servo_controller.get_status() if self.servo_controller else {}
            }
            
            await self._send_encrypted_response(data, addr)
            
        except Exception as e:
            logger.error(f"Erro ao enviar informações: {e}")

    async def _send_ping_response(self, addr):
        """Responder ao ping"""
        data = {
            'command': 'PING_ACK',
            'status': 'SUCCESS',
            'message': 'pong',
            'timestamp': time.time()
        }
        await self._send_encrypted_response(data, addr)

    async def _handle_set_servo_angle(self, msg, addr):
        """Definir ângulo do servo"""
        try:
            parts = msg.split(":")
            if len(parts) > 1:
                angle = int(parts[1])
                if self.servo_controller:
                    success = self.servo_controller.move(angle)
                    status = 'SUCCESS' if success else 'ERROR'
                    message = f'Servo movido para {angle}°' if success else 'Falha ao mover servo'
                else:
                    status = 'ERROR'
                    message = 'Servo controller não disponível'
                
                data = {
                    'command': 'SET_SERVO_ANGLE_ACK',
                    'status': status,
                    'message': message,
                    'timestamp': time.time()
                }
                await self._send_encrypted_response(data, addr)
                
        except ValueError:
            data = {
                'command': 'SET_SERVO_ANGLE_ERROR',
                'status': 'ERROR',
                'message': 'Ângulo inválido',
                'timestamp': time.time()
            }
            await self._send_encrypted_response(data, addr)

    async def _handle_set_waste_type(self, msg, addr):
        """Definir tipo de resíduo"""
        try:
            parts = msg.split(":")
            if len(parts) > 1:
                waste_type = int(parts[1])
                if self.servo_controller:
                    servo_config = self.device_manager.get_config_manager().get_servo_config()
                    success = await self.servo_controller.move_to_waste(waste_type, servo_config)
                    status = 'SUCCESS' if success else 'ERROR'
                    message = f'Movendo para resíduo tipo {waste_type}' if success else 'Falha ao mover'
                else:
                    status = 'ERROR'
                    message = 'Servo controller não disponível'
                
                data = {
                    'command': 'SET_WASTE_TYPE_ACK',
                    'status': status,
                    'message': message,
                    'timestamp': time.time()
                }
                await self._send_encrypted_response(data, addr)
                
        except ValueError:
            data = {
                'command': 'SET_WASTE_TYPE_ERROR',
                'status': 'ERROR',
                'message': 'Tipo de resíduo inválido',
                'timestamp': time.time()
            }
            await self._send_encrypted_response(data, addr)

    async def _handle_toggle_sensor(self, addr):
        """Alternar sensor"""
        self.sensor_enabled = not self.sensor_enabled
        status = 'ativado' if self.sensor_enabled else 'desativado'
        
        data = {
            'command': 'TOGGLE_SENSOR_ACK',
            'status': 'SUCCESS',
            'message': f'Sensor {status}',
            'timestamp': time.time()
        }
        await self._send_encrypted_response(data, addr)

    async def _handle_restart_system(self, addr):
        """Reiniciar sistema"""
        data = {
            'command': 'RESTART_SYSTEM_ACK',
            'status': 'SUCCESS',
            'message': 'Reiniciando sistema...',
            'timestamp': time.time()
        }
        await self._send_encrypted_response(data, addr)
        logger.info("Reiniciando sistema por comando do Flutter...")
        await asyncio.sleep(2)
        machine.reset()

    async def _send_encrypted_response(self, data, addr):
        """Enviar resposta criptografada"""
        try:
            message = json.dumps(data)
            encrypted_message = self.security.encrypt_message(message)
            await self.udp.send_message_async(encrypted_message, addr[0], addr[1])
        except Exception as e:
            logger.error(f"Erro ao enviar resposta criptografada: {e}")

    def update_movement_detected(self):
        """Atualizar quando movimento for detectado"""
        self.last_movement_time = time.time()

    def cleanup_expired_sessions(self):
        """Limpar sessões expiradas"""
        self.auth_manager.cleanup_expired_sessions()