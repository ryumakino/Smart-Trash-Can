# core/mqtt_client.py - CLIENTE MQTT COMPLETO COM CLASSES
import uasyncio as asyncio
import ujson as json
import time
from utils import get_logger

logger = get_logger("MQTTManager")

class MQTTManager:
    """Gerenciador MQTT com reconexão automática"""
    
    def __init__(self, config_manager):
        self.config = config_manager
        self.client = None
        self.connected = False
        self.message_handler = None
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 5
    
    async def connect(self):
        """Conecta ao broker MQTT"""
        device_id = self.config.get('device', 'id')
        broker = self.config.get('mqtt', 'broker')
        port = self.config.get('mqtt', 'port')
        
        try:
            # MicroPython: import correto e configuração
            from umqtt.simple import MQTTClient
            
            self.client = MQTTClient(
                client_id=device_id.encode(),
                server=broker.encode(),
                port=port,
                keepalive=60
            )
            
            # Configurar callback
            self.client.set_callback(self._on_message)
            
            # Conectar
            self.client.connect()
            
            # Inscrever nos tópicos (bytes no MicroPython)
            topic_base = self.config.get('mqtt', 'topic_base')
            device_topic = f"{topic_base}/{device_id}/#".encode()
            control_topic = f"{topic_base}/+/control".encode()
            
            self.client.subscribe(device_topic)
            self.client.subscribe(control_topic)
            
            self.connected = True
            self.reconnect_attempts = 0
            
            logger.success(f"✅ MQTT conectado: {broker}:{port}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Falha conexão MQTT: {e}")
            self.connected = False
            return False
    
    def _on_message(self, topic, message):
        """Callback para mensagens recebidas"""
        try:
            topic_str = topic.decode('utf-8') if isinstance(topic, bytes) else str(topic)
            msg_str = message.decode('utf-8') if isinstance(message, bytes) else str(message)
            
            logger.info(f"📨 MQTT RX: {topic_str} -> {msg_str}")
            
            if self.message_handler:
                self.message_handler(topic_str, msg_str)
                
        except Exception as e:
            logger.error(f"❌ Erro processando mensagem: {e}")
    
    async def publish(self, subtopic, message, retain=False):
        """Publica mensagem MQTT"""
        if not self.connected or not self.client:
            logger.warning("⚠️ MQTT não conectado para publicação")
            return False
        
        try:
            topic_base = self.config.get('mqtt', 'topic_base')
            device_id = self.config.get('device', 'id')
            
            topic = f"{topic_base}/{device_id}/{subtopic}"
            
            # Garantir que a mensagem é string
            if isinstance(message, dict):
                message_str = json.dumps(message)
            else:
                message_str = str(message)
            
            result = self.client.publish(topic, message_str, retain=retain)
            
            logger.debug(f"📤 MQTT TX: {topic} -> {message_str}")
            return result == 0
            
        except Exception as e:
            logger.error(f"❌ Erro publicando MQTT: {e}")
            self.connected = False
            return False
    
    async def publish_to_server(self, subtopic, message, retain=False):
        """Publica mensagem para tópico do servidor (sem device_id)"""
        if not self.connected or not self.client:
            logger.warning("⚠️ MQTT não conectado para publicação")
            return False
        
        try:
            topic_base = self.config.get('mqtt', 'topic_base')
            topic = f"{topic_base}/{subtopic}"
            
            # Garantir que a mensagem é string
            if isinstance(message, dict):
                message_str = json.dumps(message)
            else:
                message_str = str(message)
            
            result = self.client.publish(topic, message_str, retain=retain)
            
            logger.debug(f"📤 MQTT TX Server: {topic} -> {message_str}")
            return result == 0
            
        except Exception as e:
            logger.error(f"❌ Erro publicando MQTT para servidor: {e}")
            self.connected = False
            return False
    
    async def start(self, message_handler=None):
        """Inicia cliente MQTT"""
        self.message_handler = message_handler
        
        # Tentar conexão com retry
        while self.reconnect_attempts < self.max_reconnect_attempts:
            if await self.connect():
                return True
            
            self.reconnect_attempts += 1
            wait_time = 2 ** self.reconnect_attempts  # Exponential backoff
            
            logger.warning(f"🔄 Tentativa {self.reconnect_attempts}/{self.max_reconnect_attempts} em {wait_time}s")
            await asyncio.sleep(wait_time)
        
        logger.error("❌ MQTT - Máximo de tentativas atingido")
        return False
    
    async def maintain_connection(self):
        """Mantém conexão MQTT ativa"""
        while True:
            try:
                if self.connected and self.client:
                    # Verificar mensagens (non-blocking)
                    self.client.check_msg()
                else:
                    # Tentar reconectar
                    await self.connect()
                
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.error(f"❌ Erro manutenção MQTT: {e}")
                self.connected = False
                await asyncio.sleep(5)
    
    def disconnect(self):
        """Desconecta do broker"""
        try:
            if self.client:
                self.client.disconnect()
            self.connected = False
            logger.info("✅ MQTT desconectado")
        except Exception as e:
            logger.error(f"❌ Erro desconectando MQTT: {e}")

class MQTTMessageHandler:
    """Processador de mensagens MQTT"""
    
    def __init__(self, hardware_manager, system):
        self.hardware = hardware_manager
        self.system = system
        self.config = system.config
    
    async def handle_message(self, topic, message):
        """Processa mensagens MQTT recebidas"""
        try:
            logger.info(f"🔄 Processando mensagem: {topic}")
            
            # Parse da mensagem
            if message.startswith('{') and message.endswith('}'):
                data = json.loads(message)
                command = data.get('command', '').upper()
                params = data.get('params', {})
            else:
                command = message.strip().upper()
                params = {}
            
            # Roteamento de comandos
            handlers = {
                'STATUS': self._handle_status,
                'MOVE_SERVO': self._handle_servo_move,
                'WASTE_TYPE': self._handle_waste_type,
                'RESET': self._handle_reset,
                'PING': self._handle_ping,
                'CONFIG': self._handle_config
            }
            
            handler = handlers.get(command)
            if handler:
                await handler(params, topic)
            else:
                logger.warning(f"⚠️ Comando desconhecido: {command}")
                await self._send_response(topic, {'error': f'Comando desconhecido: {command}'})
                
        except Exception as e:
            logger.error(f"❌ Erro handle_message: {e}")
            await self._send_response(topic, {'error': str(e)})
    
    async def _handle_status(self, params, topic):
        """Envia status completo do dispositivo"""
        status = {
            'device': self.system.get_device_info(),
            'hardware': self.hardware.get_hardware_info(),
            'memory': self._get_memory_info(),
            'timestamp': time.time()
        }
        
        await self._send_response(topic, status)
    
    async def _handle_servo_move(self, params, topic):
        """Move servo para ângulo específico"""
        angle = params.get('angle', 90)
        
        servo = self.hardware.get_component('servo')
        if servo and servo.available:
            success = servo.move(angle)
            response = {
                'command': 'MOVE_SERVO',
                'angle': angle,
                'success': success
            }
        else:
            response = {
                'command': 'MOVE_SERVO', 
                'error': 'Servo não disponível',
                'success': False
            }
        
        await self._send_response(topic, response)
    
    async def _handle_waste_type(self, params, topic):
        """Move servo para tipo de lixo específico"""
        waste_index = params.get('index', 0)
        waste_types = self.config.get('servo', 'waste_types', ['Repouso', 'Plástico', 'Papel', 'Metal', 'Vidro'])
        
        servo = self.hardware.get_component('servo')
        if servo and servo.available:
            success = servo.move_to_waste_type(waste_index)
            response = {
                'command': 'WASTE_TYPE',
                'index': waste_index,
                'type': waste_types[waste_index] if 0 <= waste_index < len(waste_types) else 'Unknown',
                'success': success
            }
        else:
            response = {
                'command': 'WASTE_TYPE',
                'error': 'Servo não disponível',
                'success': False
            }
        
        await self._send_response(topic, response)
    
    async def _handle_reset(self, params, topic):
        """Reinicia o dispositivo"""
        response = {'command': 'RESET', 'status': 'reiniciando'}
        await self._send_response(topic, response)
        
        # Dar tempo para resposta ser enviada
        await asyncio.sleep(1)
        
        import machine
        machine.reset()
    
    async def _handle_ping(self, params, topic):
        """Resposta ping"""
        response = {
            'command': 'PONG',
            'timestamp': time.time(),
            'device': self.config.get('device', 'id')
        }
        await self._send_response(topic, response)
    
    async def _handle_config(self, params, topic):
        """Manipulação de configuração"""
        action = params.get('action', 'get')
        
        if action == 'get':
            response = {
                'command': 'CONFIG',
                'config': self.config.get_all()
            }
        else:
            response = {
                'command': 'CONFIG', 
                'error': 'Ações de config não implementadas',
                'action': action
            }
        
        await self._send_response(topic, response)
    
    async def _send_response(self, original_topic, response_data):
        """Envia resposta para tópico de resposta"""
        try:
            if self.system.mqtt:
                await self.system.mqtt.publish('response', response_data)
        except Exception as e:
            logger.error(f"❌ Erro enviando resposta: {e}")
    
    def _get_memory_info(self):
        """Obtém informações de memória"""
        import gc
        gc.collect()
        return {
            'free': gc.mem_free(),
            'allocated': gc.mem_alloc() if hasattr(gc, 'mem_alloc') else 0
        }