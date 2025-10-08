# communication_manager.py - CORREÇÕES COMPLETAS
import uasyncio as asyncio
import ujson as json
import time
import machine
from utils import get_logger, Queue

logger = get_logger("CommunicationManager")

class CommunicationProtocol:
    def initialize(self):
        raise NotImplementedError
    
    async def send_message(self, message):
        raise NotImplementedError
    
    async def receive_message(self):
        raise NotImplementedError
    
    def is_connected(self):
        raise NotImplementedError
    
    def cleanup(self):
        raise NotImplementedError

class ServerConnection:
    def __init__(self, network_config):
        self.network_config = network_config
        self.server_ip = None
        self.server_port = None
        self.server_name = "Unknown"
        self.connected = False
        self.last_contact = 0
        self.connection_time = 0
    
    def connect(self, server_ip, server_port, server_name="Unknown"):
        self.server_ip = server_ip
        self.server_port = server_port
        self.server_name = server_name
        self.connected = True
        self.connection_time = time.time()
        self.last_contact = time.time()
        
        logger.success(f"Conectado ao servidor: {server_name} ({server_ip}:{server_port})")
        return True
    
    def disconnect(self):
        if self.connected:
            logger.info(f"Desconectado do servidor: {self.server_name}")
        
        self.server_ip = None
        self.server_port = None
        self.server_name = "Unknown"
        self.connected = False
        self.connection_time = 0
    
    def update_contact(self):
        self.last_contact = time.time()
    
    def is_connected(self):
        if not self.connected:
            return False
        
        if time.time() - self.last_contact > 180:
            self.disconnect()
            return False
        
        return True
    
    def get_info(self):
        return {
            'ip': self.server_ip,
            'port': self.server_port,
            'name': self.server_name,
            'connected': self.connected,
            'connection_time': self.connection_time,
            'last_contact': self.last_contact
        }

class STAProtocol(CommunicationProtocol):
    def __init__(self, device_manager, network_config, server_connection):
        self.device_manager = device_manager
        self.network_config = network_config
        self.server_connection = server_connection
        self.sock = None
        
        self.udp_port = network_config.get('UDP_PORT', 8888)
        self.broadcast_port = network_config.get('BROADCAST_PORT', 8888)
        self.listen_port = network_config.get('LISTEN_PORT', 8888)  # Nova porta para escutar
        
        self.default_server_ip = network_config.get('SERVER_IP')
        self.default_server_port = network_config.get('SERVER_PORT', 8888)
    
    def initialize(self):
        import usocket as socket
        import network
        
        try:
            # CORREÇÃO: Criar socket e fazer bind para receber mensagens
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            
            # Permitir reuso de endereço e broadcast
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            
            # CORREÇÃO CRÍTICA: Fazer bind para receber mensagens
            # Usar 0.0.0.0 para escutar em todas as interfaces
            self.sock.bind(('0.0.0.0', self.listen_port))
            
            # Configurar como não-bloqueante
            self.sock.setblocking(False)
            
            # Obter IP local para logging
            wlan = network.WLAN(network.STA_IF)
            local_ip = wlan.ifconfig()[0] if wlan.isconnected() else "0.0.0.0"
            
            logger.success(f"Socket UDP vinculado à porta {self.listen_port}")
            logger.info(f"📡 IP Local: {local_ip}, Porta: {self.listen_port}")
            
            return True
            
        except Exception as e:
            logger.error(f"Erro ao inicializar socket STA: {e}")
            return False
    
    async def send_message(self, message):
        if not self.server_connection.is_connected():
            return False
        
        try:
            message_str = json.dumps(message) if isinstance(message, dict) else str(message)
            server_info = self.server_connection.get_info()
            
            self.sock.sendto(message_str.encode(), (server_info['ip'], server_info['port']))
            return True
            
        except Exception as e:
            logger.error(f"Erro enviando para servidor: {e}")
            return False
    
    async def receive_message(self):
        try:
            data, addr = await self._receive_with_timeout(0.5)
            if data:
                raw_msg = data.decode().strip()
                if raw_msg.startswith('{'):
                    msg_data = json.loads(raw_msg)
                    source_ip, source_port = addr
                    
                    if self.server_connection.is_connected():
                        server_info = self.server_connection.get_info()
                        if source_ip == server_info['ip'] and source_port == server_info['port']:
                            self.server_connection.update_contact()
                            return msg_data, addr
                    else:
                        await self._process_discovery_response(msg_data, source_ip, source_port)
                    
                    return msg_data, addr
        except Exception as e:
            logger.debug(f"STA receive error: {e}")
        return None, None
    
    async def _process_discovery_response(self, msg_data, ip, port):
        if msg_data.get('type') == 'DISCOVERY_RESPONSE':
            server_name = msg_data.get('server_name', 'Unknown Server')
            server_ip = msg_data.get('server_ip', ip)
            server_port = msg_data.get('server_port', port)
            
            self.server_connection.connect(server_ip, server_port, server_name)
    
    async def _receive_with_timeout(self, timeout=1.0):  # Aumentei timeout para 1 segundo
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                # CORREÇÃO: Tentar receber dados
                self.sock.setblocking(False)
                try:
                    data, addr = self.sock.recvfrom(1024)
                    if data:
                        return data, addr
                except OSError as e:
                    # Errno 11: EAGAIN - não há dados disponíveis (normal)
                    if e.args[0] != 11:  # Não é "recursos temporariamente indisponíveis"
                        logger.debug(f"OSError no recvfrom: {e}")
                    pass
                
                await asyncio.sleep(0.05)  # Pequena pausa entre tentativas
                
            except Exception as e:
                logger.error(f"❌ Erro em _receive_with_timeout: {e}")
                break
        
        return None, None
    
    def is_connected(self):
        return self.server_connection.is_connected()
    
    async def send_discovery(self):
        try:
            # CORREÇÃO: Coletar lixo antes de operações de rede
            import gc
            gc.collect()
            
            device_info = self.device_manager.get_device_info()
            network_status = self.device_manager.get_network_status()
            
            discovery_msg = {
                'type': 'DISCOVERY',
                'device_id': device_info['device_id'],
                'device_name': device_info['device_name'],
                'device_type': "TRASH_CAN",
                'network_mode': network_status.get('mode', 'UNKNOWN'),
                'timestamp': time.time()
            }
            
            message_str = json.dumps(discovery_msg)
            
            # CORREÇÃO: Limitar tamanho da mensagem
            if len(message_str) > 512:
                logger.warning("Mensagem de discovery muito grande")
                return False
            
            targets = []
            
            try:
                targets.append(("255.255.255.255", self.broadcast_port))
            except:
                pass
            
            if self.default_server_ip:
                targets.append((self.default_server_ip, self.default_server_port))
            
            success_count = 0
            for target_ip, target_port in targets:
                try:
                    # CORREÇÃO: Verificar se socket ainda está válido
                    if self.sock:
                        self.sock.sendto(message_str.encode(), (target_ip, target_port))
                        success_count += 1
                        await asyncio.sleep(0.1)  # Pequena pausa entre envios
                except Exception as e:
                    logger.debug(f"Erro enviando para {target_ip}:{target_port}: {e}")
            
            logger.debug("Enviando discoveries")
            return success_count > 0
            
        except Exception as e:
            logger.error(f"Erro enviando discovery: {e}")
            return False
    
    def cleanup(self):
        if self.sock:
            self.sock.close()

class APProtocol(CommunicationProtocol):
    def __init__(self, device_manager, server_connection):
        self.device_manager = device_manager
        self.server_connection = server_connection
        self.sock = None
        self.client_ip = None
        self.client_port = None
        self.connected = False
        self.available = False
        self.ap_ip = '192.168.4.1'
        self.ap_port = 8888
    
    def initialize(self):
        try:
            import usocket as socket
            import network
            
            # CORREÇÃO: Verificar se já estamos no modo AP
            wlan = network.WLAN(network.AP_IF)
            if not wlan.active():
                wlan.active(True)
                # Dar tempo para o AP inicializar
                import time
                time.sleep(2)
            
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.sock.setblocking(False)
            self.sock.bind((self.ap_ip, self.ap_port))
            self.available = True
            
            logger.success(f"AP Protocol - Aguardando servidor em {self.ap_ip}:{self.ap_port}")
            return True
            
        except Exception as e:
            logger.warning(f"AP Protocol não disponível: {e}")
            self.available = False
            return True
    
    async def send_message(self, message):
        if not self.available or not self.connected or not self.client_ip:
            return False
        
        try:
            import gc
            gc.collect()
            
            message_str = json.dumps(message) if isinstance(message, dict) else str(message)
            
            # CORREÇÃO: Limitar tamanho da mensagem
            if len(message_str) > 512:
                logger.warning("Mensagem AP muito grande")
                return False
                
            sent = self.sock.sendto(message_str.encode(), (self.client_ip, self.client_port))
            if sent > 0:
                return True
            return False
            
        except Exception as e:
            logger.debug(f"Erro AP send: {e}")
            return False
    
    async def receive_message(self):
        try:
            data, addr = await self._receive_with_timeout(0.1)
            if data:
                client_ip, client_port = addr
                
                if not self.connected:
                    self.client_ip = client_ip
                    self.client_port = client_port
                    self.connected = True
                    logger.success(f"🔗 Servidor conectado via AP: {client_ip}:{client_port}")
                
                raw_msg = data.decode().strip()
                if raw_msg.startswith('{'):
                    msg_data = json.loads(raw_msg)
                    
                    if msg_data.get('type') == 'DISCOVERY_RESPONSE' and not self.server_connection.is_connected():
                        server_name = msg_data.get('server_name', 'AP Server')
                        self.server_connection.connect(client_ip, client_port, server_name)
                
                return msg_data, addr
        except Exception as e:
            logger.debug(f"AP receive error: {e}")
        return None, None
    
    async def _receive_with_timeout(self, timeout=0.1):
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                self.sock.setblocking(False)
                try:
                    data, addr = self.sock.recvfrom(1024)
                    if data:
                        return data, addr
                except OSError:
                    pass
                await asyncio.sleep(0.01)
            except Exception as e:
                logger.debug(f"Receive timeout error: {e}")
                break
        return None, None
    
    def is_connected(self):
        return self.connected and self.available
    
    def cleanup(self):
        if self.sock:
            self.sock.close()

class SerialProtocol(CommunicationProtocol):
    def __init__(self, device_manager, uart_id=1, baudrate=115200):
        self.device_manager = device_manager
        self.uart_id = uart_id
        self.baudrate = baudrate
        self.uart = None
        self.rx_buffer = ""
        self.available = False
    
    def initialize(self):
        try:
            from machine import UART, Pin
            # Tentar inicialização mais segura da UART
            # No ESP32, UART1 geralmente usa GPIO9 (RX) e GPIO10 (TX)
            # Mas esses pinos podem estar em uso pelo flash, então usaremos UART2
            if self.uart_id == 1:
                # Tentar UART1 com pinos alternativos
                try:
                    self.uart = UART(1, baudrate=self.baudrate, rx=18, tx=19)  # GPIO18, GPIO19
                    self.uart.init(baudrate=self.baudrate, bits=8, parity=None, stop=1, timeout=100, rxbuf=1024)
                except:
                    # Fallback para UART2
                    self.uart = UART(2, baudrate=self.baudrate, rx=16, tx=17)  # GPIO16, GPIO17
                    self.uart.init(baudrate=self.baudrate, bits=8, parity=None, stop=1, timeout=100, rxbuf=1024)
            else:
                self.uart = UART(self.uart_id, baudrate=self.baudrate)
                self.uart.init(baudrate=self.baudrate, bits=8, parity=None, stop=1, timeout=100, rxbuf=1024)
            
            self.available = True
            logger.success(f"Serial UART{self.uart_id} at {self.baudrate} baud")
            return True
            
        except Exception as e:
            logger.warning(f"Serial não disponível: {e}")
            self.available = False
            return True
    
    async def send_message(self, message):
        if not self.available or not self.uart:
            return False
        
        try:
            message_str = json.dumps(message) if isinstance(message, dict) else str(message)
            message_str += '\n'
            written = self.uart.write(message_str.encode())
            return written > 0
        except Exception as e:
            logger.debug(f"Erro Serial send: {e}")
            return False
    
    async def receive_message(self):
        if not self.available or not self.uart:
            return None, None
            
        try:
            # CORREÇÃO: Verificação mais segura de dados disponíveis
            if hasattr(self.uart, 'any') and self.uart.any():
                data = self.uart.read(self.uart.any())
                if data:
                    self.rx_buffer += data.decode('utf-8', errors='ignore')
                    
                    if '\n' in self.rx_buffer:
                        lines = self.rx_buffer.split('\n')
                        self.rx_buffer = lines[-1]
                        
                        for line in lines[:-1]:
                            line = line.strip()
                            if line and line.startswith('{'):
                                try:
                                    msg_data = json.loads(line)
                                    return msg_data, "serial"
                                except ValueError as e:
                                    logger.debug(f"JSON parse error: {e}")
                                    # Tentar processar como comando simples
                                    if line.upper() in ['STATUS', 'RESTART', 'HELP']:
                                        return {'type': 'SERIAL_COMMAND', 'command': line.upper()}, "serial"
        except Exception as e:
            logger.debug(f"Serial receive error: {e}")
        
        return None, None
    
    def is_connected(self):
        return self.available  # CORREÇÃO: Retornar baseado na disponibilidade
    
    def cleanup(self):
        if self.uart:
            try:
                self.uart.deinit()
            except:
                pass
        self.available = False

class MessageRouter:
    def __init__(self, device_manager, hardware_manager, server_connection):
        self.device_manager = device_manager
        self.hardware_manager = hardware_manager
        self.server_connection = server_connection
    
    async def route_message(self, msg_data, source):
        msg_type = msg_data.get('type', 'UNKNOWN')
        
        if self.server_connection.is_connected():
            self.server_connection.update_contact()
        
        handlers = {
            'DISCOVERY_RESPONSE': self._handle_discovery_response,
            'REGISTRATION_ACK': self._handle_registration_ack,
            'HEARTBEAT_ACK': self._handle_heartbeat_ack,
            'HEARTBEAT_REQUEST': self._handle_heartbeat_request,
            'WASTE_TYPE': self._handle_waste_type,
            'SYSTEM_COMMAND': self._handle_system_command,
            'MOVEMENT_ACK': self._handle_movement_ack,
            'SERIAL_COMMAND': self._handle_serial_command,
        }
        
        handler = handlers.get(msg_type)
        if handler:
            response = await handler(msg_data, source)
            if response:
                response['timestamp'] = time.time()
            return response
        
        logger.debug(f"Mensagem não roteada: {msg_type} from {source}")
        return None
    
    async def _handle_discovery_response(self, data, source):
        server_ip = data.get('server_ip')
        server_port = data.get('server_port', 8888)
        server_name = data.get('server_name', 'Unknown Server')
        
        self.server_connection.connect(server_ip, server_port, server_name)
        
        register_msg = await self._create_registration_message()
        
        logger.success(f"Conectado ao servidor: {server_name} ({server_ip}:{server_port})")
        return register_msg
    
    async def _create_registration_message(self):
        device_info = self.device_manager.get_device_info()
        network_status = self.device_manager.get_network_status()
        
        return {
            'type': 'DEVICE_REGISTER',
            'device_info': device_info,
            'network': network_status,
            'timestamp': time.time()
        }
    
    async def _handle_registration_ack(self, data, source):
        status = data.get('status', 'UNKNOWN')
        logger.success(f"Registro confirmado: {status}")
        return None
    
    async def _handle_heartbeat_ack(self, data, source):
        logger.debug("Heartbeat confirmado")
        return None
    
    async def _handle_heartbeat_request(self, data, source):
        device_info = self.device_manager.get_device_info()
        
        return {
            'type': 'HEARTBEAT_RESPONSE',
            'device_id': device_info['device_id'],
            'device_name': device_info['device_name'],
            'timestamp': time.time(),
            'source': source
        }
    
    async def _handle_waste_type(self, data, source):
        try:
            waste_index = data.get('waste_index', 0)
            waste_name = data.get('waste_name', f"Tipo {waste_index}")
            
            logger.info(f"Movendo para: {waste_name}")
            
            servo = self.hardware_manager.get_component('servo')
            if servo:
                servo_config = self.device_manager.get_servo_config()
                success = await self._execute_servo_movement(servo, waste_index, servo_config)
                status = 'SUCCESS' if success else 'ERROR'
            else:
                status = 'NO_SERVO'
            
            return {
                'type': 'WASTE_ACK',
                'waste_index': waste_index,
                'waste_name': waste_name,
                'status': status,
                'timestamp': time.time(),
                'source': source
            }
            
        except Exception as e:
            logger.error(f"❌ Erro ao processar waste type: {e}")
            return {
                'type': 'WASTE_ACK',
                'status': 'ERROR',
                'error': str(e),
                'source': source
            }
    
    async def _execute_servo_movement(self, servo, waste_index, servo_config):
        try:
            angles = servo_config.get('SERVO_ANGLES', [0, 45, 90, 135, 180])
            waste_types = servo_config.get('WASTE_TYPES', ["Repouso", "Plástico", "Papel", "Metal", "Vidro"])
            
            if 0 <= waste_index < len(angles):
                angle = angles[waste_index]
                waste_name = waste_types[waste_index]
                
                logger.info(f"Movendo servo para {waste_name} (ângulo: {angle})")
                success = servo.move(angle)
                
                if success:
                    await asyncio.sleep(servo_config.get('SERVO_RESET_DELAY', 3))
                    servo.move(90)
                    logger.success("Movimento concluído")
                
                return success
            return False
        except Exception as e:
            logger.error(f"Erro no movimento: {e}")
            return False
    
    async def _handle_system_command(self, data, source):
        command = data.get('command', '')
        return await self._process_system_command(command, source)
    
    async def _handle_serial_command(self, data, source):
        command = data.get('command', '')
        return await self._process_system_command(command, source)
    
    async def _process_system_command(self, command, source):
        if command == "STATUS":
            status = self.device_manager.get_complete_status()
            return {
                'type': 'SYSTEM_STATUS',
                'status': status,
                'source': source
            }
        elif command == "RESTART":
            logger.info("Reiniciando...")
            await asyncio.sleep(2)
            machine.reset()
        elif command == "HELP":
            return {
                'type': 'HELP_RESPONSE',
                'commands': ['STATUS', 'RESTART', 'HELP'],
                'source': source
            }
        return None
    
    async def _handle_movement_ack(self, data, source):
        status = data.get('status', 'UNKNOWN')
        logger.debug(f"Movimento confirmado: {status}")
        return None

class MultiProtocolManager:
    def __init__(self, device_manager, hardware_manager, network_config):
        self.device_manager = device_manager
        self.hardware_manager = hardware_manager
        self.network_config = network_config
        
        self.server_connection = ServerConnection(network_config)
        
        self.protocols = {
            'serial': SerialProtocol(device_manager),
            'sta': STAProtocol(device_manager, network_config, self.server_connection),
            'ap': APProtocol(device_manager, self.server_connection)
        }
        
        self.router = MessageRouter(device_manager, hardware_manager, self.server_connection)
        self.running = False
        
        self.last_discovery = 0
        self.discovery_interval = network_config.get('DISCOVERY_INTERVAL', 30)
        self.heartbeat_interval = network_config.get('HEARTBEAT_INTERVAL', 60)
        self.last_heartbeat = 0
        
        self.active_protocol = None
        self.protocol_priority = ['serial', 'sta', 'ap']
        self.protocol_status = {
            'serial': False,
            'sta': False, 
            'ap': False
        }
    
    async def start_communication(self):
        logger.info("Iniciando comunicação...")
        self.running = True
        
        self.active_protocol = await self._initialize_with_fallback()
        
        if not self.active_protocol:
            logger.error("Todos os protocolos falharam!")
            return
        
        logger.success(f"Protocolo ativo: {self.active_protocol.upper()}")
        
        tasks = [
            asyncio.create_task(self._active_protocol_loop()),
            asyncio.create_task(self._maintenance_loop()),
        ]
        
        try:
            await asyncio.gather(*tasks)
        except Exception as e:
            logger.error(f"Erro nas tasks: {e}")
        finally:
            await self.stop_communication()
    
    async def _initialize_with_fallback(self):
        """Inicializar protocolos em ordem de prioridade"""
        for protocol_name in self.protocol_priority:
            try:
                protocol = self.protocols[protocol_name]
                logger.info(f"Tentando protocolo: {protocol_name.upper()}")
                
                if protocol.initialize():
                    self.protocol_status[protocol_name] = True
                    
                    # CORREÇÃO: Teste de conectividade mais tolerante
                    if await self._test_protocol_connectivity(protocol_name, protocol):
                        logger.success(f"Protocolo {protocol_name.upper()} conectado e funcionando")
                        return protocol_name
                    else:
                        logger.warning(f"Protocolo {protocol_name.upper()} inicializado mas sem conectividade imediata")
                        # CORREÇÃO: Não limpar imediatamente, deixar disponível para fallback
                else:
                    logger.error(f"Falha ao inicializar {protocol_name.upper()}")
                    self.protocol_status[protocol_name] = False
                    
            except Exception as e:
                logger.error(f"Erro inicialização {protocol_name}: {e}")
                self.protocol_status[protocol_name] = False
        
        for protocol_name in self.protocol_priority:
            if self.protocol_status.get(protocol_name, False):
                logger.info(f"Usando protocolo {protocol_name.upper()} (sem conectividade imediata)")
                return protocol_name
        
        return None
    
    async def _test_protocol_connectivity(self, protocol_name, protocol):
        try:
            if protocol_name == 'serial':
                return protocol.available
            
            elif protocol_name == 'sta':
                network_status = self.device_manager.get_network_status()
                if not network_status.get('connected', False):
                    logger.debug("STA: Sem conexão de rede")
                    return False

                # Tentar enviar discovery de forma segura
                try:
                    success = await protocol.send_discovery()
                    if success:
                        # Aguardar brevemente por resposta
                        await asyncio.sleep(3)
                    # CORREÇÃO: STA pode funcionar mesmo sem servidor conectado ainda
                    return True
                except Exception as e:
                    logger.debug(f"STA connectivity test failed: {e}")
                    return False
            
            elif protocol_name == 'ap':
                # Para AP, verificar se está disponível
                return protocol.available
            
            return False
            
        except Exception as e:
            logger.debug(f"Connectivity test error for {protocol_name}: {e}")
            return False
    
    async def _active_protocol_loop(self):
        while self.running and self.active_protocol:
            try:
                protocol = self.protocols[self.active_protocol]
                
                msg_data, source_addr = await protocol.receive_message()
                if msg_data:
                    logger.debug(f"📨 [{self.active_protocol}] {msg_data.get('type', 'UNKNOWN')}")
                    
                    response = await self.router.route_message(msg_data, self.active_protocol)
                    if response:
                        await protocol.send_message(response)
                
                if not await self._check_protocol_health(self.active_protocol, protocol):
                    logger.warning(f"⚠️ Protocolo {self.active_protocol} com problemas, tentando fallback...")
                    await self._switch_to_fallback()
                    break
                
                await asyncio.sleep(0.05)
                
            except Exception as e:
                logger.error(f"Erro no loop {self.active_protocol}: {e}")
                await self._switch_to_fallback()
                break
    
    async def _check_protocol_health(self, protocol_name, protocol):
        if protocol_name == 'serial':
            return protocol.is_connected()
        
        elif protocol_name == 'sta':
            network_status = self.device_manager.get_network_status()
            if network_status.get('mode') != 'STA' or not network_status.get('connected'):
                return False
            return protocol.is_connected() or True
        
        elif protocol_name == 'ap':
            network_status = self.device_manager.get_network_status()
            return network_status.get('mode') == 'AP'
        
        return True
    
    async def _switch_to_fallback(self):
        current_index = self.protocol_priority.index(self.active_protocol)
        next_protocols = self.protocol_priority[current_index + 1:]
        
        if self.active_protocol:
            self.protocols[self.active_protocol].cleanup()
            self.protocol_status[self.active_protocol] = False
        
        for protocol_name in next_protocols:
            try:
                protocol = self.protocols[protocol_name]
                logger.info(f"🔄 Fallback para: {protocol_name.upper()}")
                
                if protocol.initialize() and await self._test_protocol_connectivity(protocol_name, protocol):
                    self.active_protocol = protocol_name
                    self.protocol_status[protocol_name] = True
                    logger.success(f"✅ Fallback bem-sucedido para {protocol_name.upper()}")
                    
                    asyncio.create_task(self._active_protocol_loop())
                    return
                    
            except Exception as e:
                logger.error(f"❌ Fallback falhou para {protocol_name}: {e}")
        
        logger.error("❌ Todos os protocolos de fallback falharam!")
        self.active_protocol = None
        self.running = False
    
    async def _maintenance_loop(self):
        while self.running and self.active_protocol:
            try:
                current_time = time.time()
                
                if not self.server_connection.is_connected() and \
                   current_time - self.last_discovery > self.discovery_interval and \
                   self.active_protocol == 'sta':
                    await self._send_discovery()
                    self.last_discovery = current_time
                
                if self.server_connection.is_connected() and \
                   current_time - self.last_heartbeat > self.heartbeat_interval:
                    await self._send_heartbeat()
                    self.last_heartbeat = current_time
                
                await asyncio.sleep(5)
                
            except Exception as e:
                logger.error(f"Erro no maintenance: {e}")
                await asyncio.sleep(10)
    
    async def _send_discovery(self):
        if self.active_protocol == 'sta':
            sta_protocol = self.protocols['sta']
            await sta_protocol.send_discovery()
    
    async def _send_heartbeat(self):
        if not self.server_connection.is_connected() or not self.active_protocol:
            return
        
        device_info = self.device_manager.get_device_info()
        
        heartbeat_msg = {
            'type': 'HEARTBEAT',
            'device_id': device_info['device_id'],
            'uptime': time.time() - self.device_manager.system_metrics.startup_time,
            'timestamp': time.time()
        }
        
        protocol = self.protocols[self.active_protocol]
        if protocol.is_connected():
            await protocol.send_message(heartbeat_msg)
            logger.debug("💓 Heartbeat enviado")
    
    async def send_movement_detected(self):
        if not self.server_connection.is_connected() or not self.active_protocol:
            logger.warning("⚠️ Movimento não reportado (servidor desconectado)")
            return False
        
        device_info = self.device_manager.get_device_info()
        
        movement_msg = {
            'type': 'MOVEMENT_DETECTED',
            'device_id': device_info['device_id'],
            'device_name': device_info['device_name'],
            'timestamp': time.time()
        }
        
        protocol = self.protocols[self.active_protocol]
        success = await protocol.send_message(movement_msg)
        
        if success:
            logger.info("🚨 Movimento reportado para servidor")
        else:
            logger.error("❌ Falha ao reportar movimento")
        
        return success
    
    def get_communication_status(self):
        server_info = self.server_connection.get_info()
        
        status = {
            'running': self.running,
            'active_protocol': self.active_protocol,
            'server_connected': self.server_connection.is_connected(),
            'server': server_info,
            'protocols_status': self.protocol_status,
            'last_discovery': self.last_discovery,
            'last_heartbeat': self.last_heartbeat
        }
        
        return status
    
    def get_server_info(self):
        return self.server_connection.get_info()
    
    async def stop_communication(self):
        logger.info("🛑 Parando comunicação")
        self.running = False
        self.active_protocol = None
        self.server_connection.disconnect()
        
        for protocol_name, protocol in self.protocols.items():
            try:
                protocol.cleanup()
                self.protocol_status[protocol_name] = False
                logger.info(f"Protocolo {protocol_name} limpo")
            except Exception as e:
                logger.error(f"Erro ao limpar {protocol_name}: {e}")