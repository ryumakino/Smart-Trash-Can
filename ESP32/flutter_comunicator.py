# flutter_communicator.py - Comunicação com Flutter (com autenticação completa)
import uasyncio as asyncio
import ujson as json
import time
import machine
from utils import get_logger
from system_data import SystemDataBuilder
from security import SecurityManager, AuthenticationManager

logger = get_logger("FlutterCommunicator")

class FlutterCommunicator:
    """Gerenciador de comunicação com aplicativo Flutter com autenticação"""
    
    def __init__(self, udp_communicator, device_manager, server_communicator=None, 
                 wifi_manager=None, system_health=None, servo_controller=None):
        self.udp = udp_communicator
        self.device_manager = device_manager
        self.server_communicator = server_communicator
        self.wifi_manager = wifi_manager
        self.system_health = system_health
        self.servo_controller = servo_controller
        
        # Sistema de autenticação
        network_config = device_manager.get_network_config()
        self.security = SecurityManager(
            network_config.get('AUTH_KEY'),
            network_config.get('TOKEN_TIMEOUT', 30)
        )
        self.auth_manager = AuthenticationManager(self.security)
        
        # Handlers de mensagem (apenas para clientes autenticados)
        self.authenticated_handlers = {
            'GET_ALL_INFO': self._handle_get_all_info,
            'GET_WLAN_INFO': self._handle_get_wlan_info,
            'GET_SENSOR_INFO': self._handle_get_sensor_info,
            'GET_SERVO_INFO': self._handle_get_servo_info,
            'GET_HARDWARE_INFO': self._handle_get_hardware_info,
            'GET_UDP_INFO': self._handle_get_udp_info,
            'PING': self._handle_ping,
            'RESTART_SYSTEM': self._handle_restart_system,
            'TOGGLE_SENSOR': self._handle_toggle_sensor,
            'SET_SERVO_ANGLE': self._handle_set_servo_angle,
            'SET_WASTE_TYPE': self._handle_set_waste_type,
            'SET_SENSOR_MODE': self._handle_set_sensor_mode,
            'SET_WLAN': self._handle_set_wlan_config,
            'LOGOUT': self._handle_logout
        }
        
        # Handlers públicos (não requerem autenticação)
        self.public_handlers = {
            'AUTH_REQUEST': self._handle_auth_request,
            'AUTH_RESPONSE': self._handle_auth_response,
            'DISCOVER_ESP32': self._handle_discovery,
            'PC_ONLINE': self._handle_pc_online
        }
        
        self.sensor_enabled = True
        self.last_movement_time = 0

    async def handle_message(self, msg, addr):
        """Processar mensagens do Flutter com autenticação"""
        try:
            client_ip = addr[0] if isinstance(addr, tuple) else addr
            logger.info(f"Mensagem de {client_ip}: {msg[:50]}...")
            
            # Tentar descriptografar a mensagem
            decrypted_msg = self.security.decrypt_message(msg)
            if decrypted_msg is None:
                # Se não conseguiu descriptografar, tratar como texto simples
                decrypted_msg = msg
            
            # Processar comando
            await self._process_decrypted_message(decrypted_msg, addr, client_ip)
            
        except Exception as e:
            logger.error(f"Erro ao processar mensagem do Flutter: {e}")
            await self._send_error_response('GENERAL', str(e), addr)

    async def _process_decrypted_message(self, msg, addr, client_ip):
        """Processar mensagem descriptografada"""
        # Primeiro verificar handlers públicos
        for command, handler in self.public_handlers.items():
            if msg.startswith(command):
                if ':' in msg:
                    parts = msg.split(':', 1)
                    param = parts[1]
                    await handler(addr, client_ip, param)
                else:
                    await handler(addr, client_ip)
                return
        
        # Verificar se é um comando que requer autenticação
        for command, handler in self.authenticated_handlers.items():
            if msg.startswith(command):
                # Verificar autenticação
                if not await self._check_authentication(addr, client_ip, msg):
                    return
                
                # Executar handler autenticado
                if ':' in msg:
                    parts = msg.split(':', 1)
                    param = parts[1]
                    await handler(addr, client_ip, param)
                else:
                    await handler(addr, client_ip)
                return
        
        # Comando não reconhecido
        await self._send_error_response('UNKNOWN', f'Comando não reconhecido: {msg}', addr)

    async def _check_authentication(self, addr, client_ip, msg) -> bool:
        """Verificar se o cliente está autenticado"""
        # Extrair session_key da mensagem se presente
        session_key = None
        if ':' in msg:
            parts = msg.split(':', 1)
            # Tentar extrair session_key do payload JSON
            try:
                payload = json.loads(parts[1])
                session_key = payload.get('session_key')
            except:
                pass
        
        if not self.auth_manager.validate_client_session(client_ip, session_key):
            await self._send_auth_required_response(addr)
            return False
        return True

    # -------- Handlers Públicos (Não Autenticados) --------
    async def _handle_auth_request(self, addr, client_ip, param=None):
        """Handle para solicitação de autenticação"""
        try:
            auth_data = json.loads(param) if param else {}
            client_id = auth_data.get('client_id', 'flutter_app')
            
            # Iniciar processo de autenticação
            auth_result = self.auth_manager.initiate_auth(client_ip, client_id)
            
            # Enviar resposta criptografada
            encrypted_response = self.security.encrypt_message(json.dumps(auth_result))
            await self.udp.send_message_async(encrypted_response, addr[0], addr[1])
            
        except Exception as e:
            logger.error(f"Erro no auth request: {e}")
            await self._send_error_response('AUTH', str(e), addr)

    async def _handle_auth_response(self, addr, client_ip, param):
        """Handle para resposta de autenticação"""
        try:
            auth_data = json.loads(param)
            client_id = auth_data.get('client_id', 'flutter_app')
            challenge = auth_data.get('challenge')
            response = auth_data.get('response')
            
            if not all([challenge, response]):
                await self._send_error_response('AUTH', 'Dados de autenticação incompletos', addr)
                return
            
            # Completar autenticação
            auth_result = self.auth_manager.complete_auth(
                client_ip, client_id, challenge, response
            )
            
            # Enviar resposta criptografada
            encrypted_response = self.security.encrypt_message(json.dumps(auth_result))
            await self.udp.send_message_async(encrypted_response, addr[0], addr[1])
            
            # Se autenticação bem-sucedida, enviar dados iniciais
            if auth_result['status'] == 'AUTHENTICATED':
                await self._send_all_info(addr, client_ip)
                
        except Exception as e:
            logger.error(f"Erro no auth response: {e}")
            await self._send_error_response('AUTH', str(e), addr)

    async def _handle_discovery(self, addr, client_ip, param=None):
        """Responder a pedidos de discovery"""
        data = SystemDataBuilder.build_discovery_response(self.device_manager)
        # Discovery não requer autenticação, mas pode ser criptografado
        encrypted_response = self.security.encrypt_message(json.dumps(data))
        await self.udp.send_message_async(encrypted_response, addr[0], addr[1])
        logger.info(f"Resposta de discovery enviada para {client_ip}")

    async def _handle_pc_online(self, addr, client_ip, param=None):
        """Handle quando Flutter conecta (requer autenticação)"""
        # PC_ONLINE agora requer autenticação primeiro
        await self._send_auth_required_response(addr)

    # -------- Handlers Autenticados --------
    async def _handle_get_all_info(self, addr, client_ip, param=None):
        """Enviar todas as informações do sistema (autenticado)"""
        await self._send_all_info(addr, client_ip)

    async def _handle_get_wlan_info(self, addr, client_ip, param=None):
        """Enviar informações de rede (autenticado)"""
        data = SystemDataBuilder.build_network_data(self.device_manager, self.wifi_manager)
        await self._send_encrypted_response(data, addr)

    async def _handle_get_sensor_info(self, addr, client_ip, param=None):
        """Enviar informações do sensor (autenticado)"""
        data = SystemDataBuilder.build_sensor_data(
            movement_detected=False,
            last_movement=self.last_movement_time
        )
        await self._send_encrypted_response(data, addr)

    async def _handle_get_servo_info(self, addr, client_ip, param=None):
        """Enviar informações do servo (autenticado)"""
        current_pos = 0
        if self.servo_controller:
            servo_status = self.servo_controller.get_status()
            current_pos = servo_status.get('current_position', 0)
            
        data = SystemDataBuilder.build_servo_data(current_pos)
        await self._send_encrypted_response(data, addr)

    async def _handle_get_hardware_info(self, addr, client_ip, param=None):
        """Enviar informações de hardware (autenticado)"""
        data = SystemDataBuilder.build_hardware_data(self.device_manager, self.system_health)
        await self._send_encrypted_response(data, addr)

    async def _handle_get_udp_info(self, addr, client_ip, param=None):
        """Enviar informações de comunicação (autenticado)"""
        data = {
            'command': 'UDP_INFO',
            'timestamp': time.time(),
            'udp': {
                'port': self.udp.port,
                'broadcast_port': self.udp.broadcast_port,
                'messages_received': 0,
                'last_message': time.time()
            }
        }
        await self._send_encrypted_response(data, addr)

    async def _handle_ping(self, addr, client_ip, param=None):
        """Responder ao ping (autenticado)"""
        data = SystemDataBuilder.build_simple_response('PING', 'SUCCESS', 'pong')
        await self._send_encrypted_response(data, addr)

    async def _handle_restart_system(self, addr, client_ip, param=None):
        """Reiniciar sistema (autenticado)"""
        data = SystemDataBuilder.build_simple_response('RESTART_SYSTEM', 'SUCCESS', 'Reiniciando...')
        await self._send_encrypted_response(data, addr)
        logger.info("Reiniciando sistema por comando do Flutter...")
        await asyncio.sleep(2)
        machine.reset()

    async def _handle_toggle_sensor(self, addr, client_ip, param=None):
        """Alternar sensor (autenticado)"""
        self.sensor_enabled = not self.sensor_enabled
        status = 'ativado' if self.sensor_enabled else 'desativado'
        data = SystemDataBuilder.build_simple_response(
            'TOGGLE_SENSOR', 
            'SUCCESS', 
            f'Sensor {status}'
        )
        await self._send_encrypted_response(data, addr)

    async def _handle_set_servo_angle(self, addr, client_ip, param):
        """Definir ângulo do servo (autenticado)"""
        try:
            angle = int(param)
            if self.servo_controller:
                success = await self.servo_controller.move_to_angle(angle)
                if success:
                    data = SystemDataBuilder.build_simple_response(
                        'SET_SERVO_ANGLE', 
                        'SUCCESS', 
                        f'Servo movido para {angle}°'
                    )
                else:
                    data = SystemDataBuilder.build_error_response(
                        'SET_SERVO_ANGLE',
                        'Falha ao mover servo'
                    )
            else:
                data = SystemDataBuilder.build_error_response(
                    'SET_SERVO_ANGLE',
                    'Servo controller não disponível'
                )
                
            await self._send_encrypted_response(data, addr)
            
        except ValueError:
            data = SystemDataBuilder.build_error_response(
                'SET_SERVO_ANGLE',
                'Ângulo inválido'
            )
            await self._send_encrypted_response(data, addr)

    async def _handle_set_waste_type(self, addr, client_ip, param):
        """Definir tipo de resíduo (autenticado)"""
        try:
            waste_type = int(param)
            if self.servo_controller:
                success = await self.servo_controller.move_to_waste(waste_type)
                if success:
                    data = SystemDataBuilder.build_simple_response(
                        'SET_WASTE_TYPE', 
                        'SUCCESS', 
                        f'Movendo para resíduo tipo {waste_type}'
                    )
                else:
                    data = SystemDataBuilder.build_error_response(
                        'SET_WASTE_TYPE',
                        'Falha ao mover para tipo de resíduo'
                    )
            else:
                data = SystemDataBuilder.build_error_response(
                    'SET_WASTE_TYPE',
                    'Servo controller não disponível'
                )
                
            await self._send_encrypted_response(data, addr)
            
        except ValueError:
            data = SystemDataBuilder.build_error_response(
                'SET_WASTE_TYPE',
                'Tipo de resíduo inválido'
            )
            await self._send_encrypted_response(data, addr)

    async def _handle_set_sensor_mode(self, addr, client_ip, param):
        """Definir modo do sensor (autenticado)"""
        try:
            mode = int(param)
            self.sensor_enabled = (mode == 1)
            status = 'ativado' if self.sensor_enabled else 'desativado'
            data = SystemDataBuilder.build_simple_response(
                'SET_SENSOR_MODE', 
                'SUCCESS', 
                f'Sensor {status}'
            )
            await self._send_encrypted_response(data, addr)
            
        except ValueError:
            data = SystemDataBuilder.build_error_response(
                'SET_SENSOR_MODE',
                'Modo de sensor inválido'
            )
            await self._send_encrypted_response(data, addr)

    async def _handle_set_wlan_config(self, addr, client_ip, param):
        """Configurar WiFi (autenticado)"""
        try:
            parts = param.split(':')
            if len(parts) == 2:
                ssid, password = parts
                
                wifi_updates = {
                    'SSID': ssid,
                    'PASSWORD': password
                }
                
                success = self.device_manager.update_wifi_config(wifi_updates)
                
                if success:
                    data = SystemDataBuilder.build_simple_response(
                        'SET_WLAN', 
                        'SUCCESS', 
                        'Configuração WiFi atualizada. Reconectando...'
                    )
                    
                    asyncio.create_task(self._reconnect_wifi())
                else:
                    data = SystemDataBuilder.build_error_response(
                        'SET_WLAN',
                        'Falha ao salvar configuração WiFi'
                    )
            else:
                data = SystemDataBuilder.build_error_response(
                    'SET_WLAN',
                    'Formato inválido. Use: SSID:senha'
                )
                
            await self._send_encrypted_response(data, addr)
            
        except Exception as e:
            data = SystemDataBuilder.build_error_response(
                'SET_WLAN',
                f'Erro: {str(e)}'
            )
            await self._send_encrypted_response(data, addr)

    async def _handle_logout(self, addr, client_ip, param=None):
        """Logout manual (autenticado)"""
        success = self.auth_manager.logout_client(client_ip)
        if success:
            data = SystemDataBuilder.build_simple_response(
                'LOGOUT', 
                'SUCCESS', 
                'Logout realizado com sucesso'
            )
        else:
            data = SystemDataBuilder.build_error_response(
                'LOGOUT',
                'Cliente não estava autenticado'
            )
        await self._send_encrypted_response(data, addr)

    # -------- Métodos Auxiliares --------
    async def _send_all_info(self, addr, client_ip):
        """Enviar todas as informações para o Flutter (autenticado)"""
        data = SystemDataBuilder.build_complete_system_data(
            self.device_manager,
            self.server_communicator,
            self.wifi_manager,
            self.system_health
        )
        await self._send_encrypted_response(data, addr)

    async def _send_encrypted_response(self, data, addr):
        """Enviar resposta criptografada"""
        try:
            message = json.dumps(data)
            encrypted_message = self.security.encrypt_message(message)
            await self.udp.send_message_async(encrypted_message, addr[0], addr[1])
            logger.debug(f"Resposta criptografada enviada: {data['command']}")
        except Exception as e:
            logger.error(f"Erro ao enviar resposta criptografada: {e}")

    async def _send_error_response(self, command, message, addr):
        """Enviar resposta de erro"""
        data = SystemDataBuilder.build_error_response(command, message)
        try:
            encrypted_message = self.security.encrypt_message(json.dumps(data))
            await self.udp.send_message_async(encrypted_message, addr[0], addr[1])
        except Exception as e:
            logger.error(f"Erro ao enviar resposta de erro: {e}")

    async def _send_auth_required_response(self, addr):
        """Enviar resposta de autenticação necessária"""
        data = {
            'status': 'AUTH_REQUIRED',
            'message': 'Autenticação necessária para acessar este recurso'
        }
        try:
            encrypted_message = self.security.encrypt_message(json.dumps(data))
            await self.udp.send_message_async(encrypted_message, addr[0], addr[1])
        except Exception as e:
            logger.error(f"Erro ao enviar resposta de auth required: {e}")

    async def _reconnect_wifi(self):
        """Reconectar WiFi após mudança de configuração"""
        await asyncio.sleep(2)
        logger.info("Reconectando WiFi com nova configuração...")
        if self.wifi_manager:
            self.wifi_manager.connect()

    def update_movement_detected(self):
        """Atualizar quando movimento for detectado"""
        self.last_movement_time = time.time()
        logger.info("Movimento detectado - atualizando timestamp")

    async def send_movement_notification(self, addr, client_ip):
        """Enviar notificação de movimento para Flutter (autenticado)"""
        if self.auth_manager.validate_client_session(client_ip, None):
            data = {
                'command': 'MOVEMENT_DETECTED',
                'timestamp': time.time(),
                'sensor': {
                    'movement_detected': True,
                    'last_movement': self.last_movement_time
                }
            }
            await self._send_encrypted_response(data, addr)

    def cleanup_expired_sessions(self):
        """Limpar sessões expiradas periodicamente"""
        self.auth_manager.cleanup_expired_sessions()