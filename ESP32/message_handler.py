# message_handler.py - Gerenciador central de mensagens
import ujson
import time
from utils import get_logger

logger = get_logger("MessageHandler")

class MessageHandler:
    """Gerenciador reutilizável de mensagens"""
    
    def __init__(self, device_manager, udp_communicator, servo_controller=None):
        self.device_manager = device_manager
        self.udp = udp_communicator
        self.servo_controller = servo_controller
        self.message_handlers = {}
        self._register_default_handlers()
    
    def _register_default_handlers(self):
        """Registrar handlers padrão"""
        self.register_handler('SERVER_ONLINE', self._handle_server_online)
        self.register_handler('SERVER_OFFLINE', self._handle_server_offline)
        self.register_handler('WASTE_TYPE', self._handle_waste_type)
        self.register_handler('HEARTBEAT_REQUEST', self._handle_heartbeat_request)
        self.register_handler('DEVICE_CONFIG', self._handle_device_config)
        self.register_handler('SYSTEM_COMMAND', self._handle_system_command)
    
    def register_handler(self, message_type, handler_function):
        """Registrar novo handler de mensagem"""
        self.message_handlers[message_type] = handler_function
        logger.debug(f"Handler registrado para: {message_type}")
    
    async def handle_message(self, msg, addr):
        """Processar mensagens recebidas"""
        try:
            for msg_type, handler in self.message_handlers.items():
                if msg.startswith(msg_type):
                    await handler(msg, addr)
                    return True
            
            # Mensagem não reconhecida
            logger.debug(f"Mensagem não reconhecida: {msg}")
            return False
            
        except Exception as e:
            logger.error(f"Erro ao processar mensagem: {e}")
            return False
    
    async def _handle_server_online(self, msg, addr):
        """Handler reutilizável para servidor online"""
        server_ip = addr[0] if isinstance(addr, tuple) else addr
        logger.info(f"Servidor online detectado: {server_ip}")
        
        # Esta função seria implementada no ServerCommunicator
        # É mantida aqui para mostrar o padrão
    
    async def _handle_server_offline(self, msg, addr):
        """Handler reutilizável para servidor offline"""
        logger.warning("Servidor desconectou")
    
    async def _handle_waste_type(self, msg, addr):
        """Handler reutilizável para tipo de resíduo"""
        try:
            parts = msg.split(":")
            if len(parts) >= 2:
                waste_index = int(parts[1])
                waste_name = parts[2] if len(parts) > 2 else f"Tipo {waste_index}"
                
                logger.info(f"Comando do servidor: Mover para {waste_name}")
                
                # Executar movimento do servo se disponível
                if self.servo_controller:
                    success = await self.servo_controller.move_to_waste(waste_index)
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
        """Handler reutilizável para heartbeat"""
        # Será implementado pelo ServerCommunicator
        pass
    
    async def _handle_device_config(self, msg, addr):
        """Handler reutilizável para configuração de dispositivo"""
        try:
            parts = msg.split(":", 1)
            if len(parts) > 1:
                config_data = ujson.loads(parts[1])
                success = self.device_manager.update_device_config(config_data)
                
                ack_data = {
                    'status': 'success' if success else 'error',
                    'device': self.device_manager.get_device_info()
                }
                await self.udp.send_message_async(
                    f"CONFIG_ACK:{ujson.dumps(ack_data)}", 
                    ip=addr[0]
                )
                
        except Exception as e:
            logger.error(f"Erro ao atualizar configurações: {e}")
    
    async def _handle_system_command(self, msg, addr):
        """Handler reutilizável para comandos de sistema"""
        try:
            parts = msg.split(":")
            command = parts[1] if len(parts) > 1 else ""
            
            if command == "STATUS":
                # Será implementado pelo ServerCommunicator
                pass
            elif command == "DISCOVER":
                await self._send_device_discovery(addr[0])
                
        except Exception as e:
            logger.error(f"Erro ao executar comando: {e}")
    
    async def _send_device_discovery(self, target_ip):
        """Enviar mensagem de discovery"""
        discovery_data = self.device_manager.get_broadcast_message()
        discovery_msg = f"DEVICE_DISCOVERY:{ujson.dumps(discovery_data)}"
        await self.udp.send_message_async(discovery_msg, ip=target_ip)