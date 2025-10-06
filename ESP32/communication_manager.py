# communication_manager.py
import uasyncio as asyncio
import ujson as json
import time
import machine
import usocket as socket
from utils import get_logger
from security import SecurityManager

logger = get_logger("CommunicationManager")

class MessageHandler:
    """SRP: Processar mensagens recebidas"""
    
    def __init__(self, device_manager, hardware_manager):
        self.device_manager = device_manager
        self.hardware_manager = hardware_manager
    
    async def handle_message(self, msg, addr):
        """Processar mensagem baseado no tipo - OCP"""
        handlers = self._get_handlers()
        
        for prefix, handler in handlers.items():
            if msg.startswith(prefix):
                return await handler(msg, addr)
        
        logger.debug(f"Mensagem não processada: {msg[:50]}...")
        return False
    
    def _get_handlers(self):
        """Obter handlers - DRY"""
        return {
            'SERVER_ONLINE': self._handle_server_online,
            'WASTE_TYPE': self._handle_waste_type,
            'HEARTBEAT_REQUEST': self._handle_heartbeat,
            'SYSTEM_COMMAND': self._handle_system_command,
        }
    
    async def _handle_server_online(self, msg, addr):
        """Conectar ao servidor"""
        try:
            server_ip = addr[0]
            parts = msg.split(":")
            server_port = int(parts[1]) if len(parts) > 1 else 8888

            # Atualizar status via device_manager
            self.device_manager.update_communication_status({
                'server_ip': server_ip,
                'server_port': server_port,
                'connected': True,
                'connection_time': time.time()
            })

            device_info = self.device_manager.get_device_info()
            return f"DEVICE_REGISTER:{json.dumps(device_info)}"
            
        except Exception as e:
            logger.error(f"Falha ao conectar: {e}")
            return None
    
    async def _handle_waste_type(self, msg, addr):
        """Processar comando de movimento"""
        try:
            parts = msg.split(":")
            if len(parts) >= 2:
                waste_index = int(parts[1])
                waste_name = parts[2] if len(parts) > 2 else f"Tipo {waste_index}"
                logger.info(f"Comando: Mover para {waste_name}")
                
                servo = self.hardware_manager.get_component('servo')
                if servo:
                    servo_config = self.device_manager.get_servo_config()
                    success = await servo.move_to_waste(waste_index, servo_config)
                    ack_status = 'SUCCESS' if success else 'ERROR'
                else:
                    ack_status = 'NO_SERVO'
                    
                return f"WASTE_ACK:{waste_index}:{ack_status}"
        except Exception as e:
            logger.error(f"Erro ao processar waste type: {e}")
            return "WASTE_ACK:0:ERROR"
    
    async def _handle_heartbeat(self, msg, addr):
        """Responder heartbeat"""
        return "HEARTBEAT_RESPONSE"
    
    async def _handle_system_command(self, msg, addr):
        """Processar comandos de sistema"""
        try:
            parts = msg.split(":")
            command = parts[1] if len(parts) > 1 else ""
            
            if command == "STATUS":
                status = self.device_manager.get_complete_status()
                return f"SYSTEM_STATUS:{json.dumps(status)}"
            elif command == "RESTART":
                logger.info("Reiniciando por comando...")
                await asyncio.sleep(2)
                machine.reset()
                
        except Exception as e:
            logger.error(f"Erro no comando: {e}")
        
        return None

class CommunicationManager:
    """Coordenação central de comunicação - SRP"""
    
    def __init__(self, device_manager, hardware_manager, network_config):
        self.device_manager = device_manager
        self.hardware_manager = hardware_manager
        self.network_config = network_config
        
        # Componentes especializados
        self.message_handler = MessageHandler(device_manager, hardware_manager)
        self.security = SecurityManager(
            network_config.get('AUTH_KEY'), 
            network_config.get('TOKEN_TIMEOUT', 30)
        )
        
        # Estado
        self.port = network_config.get('UDP_PORT', 8888)
        self.sock = self._setup_socket()
        self.running = False
        self.msg_queue = asyncio.Queue()
        
        # Timers
        self.last_broadcast = 0
        self.last_heartbeat = 0
        self.broadcast_interval = network_config.get('DISCOVERY_INTERVAL', 30)
        self.heartbeat_interval = 60
        
        logger.info("CommunicationManager inicializado")
    
    def _setup_socket(self):
        """Configurar socket - SRP"""
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.bind(("0.0.0.0", self.port))
        return sock
    
    async def start_communication(self):
        """Iniciar serviços - SRP"""
        try:
            loop = asyncio.get_event_loop()
            loop.create_task(self._listener())
            loop.create_task(self._broadcast_discovery())
            loop.create_task(self._maintenance_task())
            
            self.running = True
            logger.info("Serviços de comunicação iniciados")
        except Exception as e:
            logger.error(f"Erro ao iniciar: {e}")
            raise
    
    async def _listener(self):
        """Ouvir mensagens - SRP"""
        logger.info(f"UDP Listener ativo na porta {self.port}")
        while self.running:
            try:
                data, addr = self.sock.recvfrom(1024)
                await self._process_received_message(data, addr)
            except OSError:
                await asyncio.sleep(0.05)
            except Exception as e:
                logger.error(f"Erro no listener: {e}")
                await asyncio.sleep(1)
    
    async def _process_received_message(self, data, addr):
        """Processar mensagem recebida - DRY"""
        try:
            raw_msg = data.decode().strip()
            msg = self.security.decrypt_message(raw_msg) or raw_msg
            
            # Processar imediatamente
            response = await self.message_handler.handle_message(msg, addr)
            if response:
                await self._send_message(response, addr[0], addr[1])
            
            logger.debug(f"Mensagem de {addr}: {msg[:50]}...")
        except Exception as e:
            logger.error(f"Erro ao processar: {e}")
    
    async def _send_message(self, message, ip=None, port=None):
        """Método único para envio - DRY"""
        try:
            encrypted = self.security.encrypt_message(message)
            target_ip = ip or "255.255.255.255"
            target_port = port or self.port
            self.sock.sendto(encrypted.encode(), (target_ip, target_port))
            logger.debug(f"Enviado para {target_ip}:{target_port}")
        except Exception as e:
            logger.error(f"Erro ao enviar: {e}")
    
    # Tarefas periódicas
    async def _broadcast_discovery(self):
        """Broadcast periódico - SRP"""
        while self.running:
            try:
                current_time = time.time()
                if current_time - self.last_broadcast > self.broadcast_interval:
                    discovery_msg = json.dumps({"DISCOVERY": True})
                    await self._send_message(discovery_msg, "255.255.255.255", self.port)
                    self.last_broadcast = current_time
                    logger.debug("Broadcast enviado")
                await asyncio.sleep(5)
            except Exception as e:
                logger.error(f"Erro no broadcast: {e}")
                await asyncio.sleep(10)
    
    async def _maintenance_task(self):
        """Manutenção da conexão - SRP"""
        while self.running:
            try:
                comm_status = self.device_manager.get_communication_status()
                
                if comm_status.get('connected') and time.time() - self.last_heartbeat > self.heartbeat_interval:
                    await self._send_heartbeat()
                    
                elif not comm_status.get('connected'):
                    await self._send_message(
                        json.dumps({"DISCOVERY": True}), 
                        "255.255.255.255", 
                        self.port
                    )
                    
                await asyncio.sleep(10)
            except Exception as e:
                logger.error(f"Erro na manutenção: {e}")
                await asyncio.sleep(10)
    
    async def _send_heartbeat(self):
        """Enviar heartbeat - SRP"""
        device_id = self.device_manager.get_device_id()
        await self._send_to_server(f"HEARTBEAT:{device_id}")
        self.last_heartbeat = time.time()
    
    async def _send_to_server(self, message):
        """Enviar para servidor - SRP"""
        comm_status = self.device_manager.get_communication_status()
        if comm_status.get('connected'):
            await self._send_message(message, comm_status['server_ip'], comm_status['server_port'])
        else:
            logger.warning("Tentativa de enviar sem servidor conectado")
    
    # Métodos públicos
    async def send_movement_detected(self):
        """Notificar detecção de movimento"""
        comm_status = self.device_manager.get_communication_status()
        if comm_status.get('connected'):
            device_id = self.device_manager.get_device_id()
            await self._send_to_server(f"MOVEMENT_DETECTED:{device_id}")
    
    def stop_communication(self):
        """Parar serviços - SRP"""
        self.running = False
        if self.sock:
            self.sock.close()
        logger.info("Comunicação parada")
    
    def get_communication_status(self):
        """Obter status - SRP"""
        return self.device_manager.get_communication_status()