# server_communicator.py - CORRIGIDO para ESP32
import socket
import threading
import queue
import time
import json
from datetime import datetime

class ServerCommunicator:
    def __init__(self):
        self.udp_port = 8888
        self.logger = self._setup_logger()

        # Configurar socket UDP
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.sock.bind(("", self.udp_port))
        self.sock.settimeout(1.0)
        
        # Gerenciamento de dispositivos
        self.devices = {}
        
        self.running = True
        self.msg_queue = queue.Queue()
        self.heartbeat_interval = 60
        self.last_heartbeat = 0
        self.messages_processed = 0
        
        # Callback para movimento detectado
        self.movement_callback = None
        
        # Controle de discovery
        self.discovery_active = True
        self.discovery_start_time = time.time()
        self.discovery_timeout = 300
        
        # Rede local para comunicação
        self.local_network = self._detect_local_network()
        
        # CORREÇÃO: Adicionar broadcast address
        self.broadcast_address = "255.255.255.255"
        
        # CORREÇÃO: Configurações específicas para ESP32
        self.esp32_network_config = {
            'ap_network': '192.168.4',  # Rede padrão do ESP32 em modo AP
            'sta_timeout': 5,           # Timeout para dispositivos STA
            'ap_timeout': 10,           # Timeout para dispositivos AP
            'max_retries': 3            # Tentativas de envio
        }
        
        # Threads
        self.listener_thread = threading.Thread(target=self._listener_loop, daemon=True)
        self.processor_thread = threading.Thread(target=self._processor_loop, daemon=True)
        self.heartbeat_thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
        self.cleanup_thread = threading.Thread(target=self._cleanup_loop, daemon=True)

    def _setup_logger(self):
        """Logger simplificado"""
        class SimpleLogger:
            def info(self, msg): print(f"[INFO] {msg}")
            def error(self, msg): print(f"[ERROR] {msg}")
            def warning(self, msg): print(f"[WARNING] {msg}")
            def debug(self, msg): print(f"[DEBUG] {msg}")
            def success(self, msg): print(f"[SUCCESS] {msg}")
        return SimpleLogger()

    def _detect_local_network(self):
        """Detectar rede local para comunicação"""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
            
            # Extrair subnet
            subnet = ".".join(local_ip.split(".")[:3])
            self.logger.info(f"🌐 Rede local detectada: {subnet}.x")
            return subnet
        except:
            self.logger.warning("⚠️ Não foi possível detectar rede local")
            return "192.168.1"  # Fallback

    def start(self):
        """Iniciar comunicador do servidor"""
        self.listener_thread.start()
        self.processor_thread.start()
        self.heartbeat_thread.start()
        self.cleanup_thread.start()
        self.start_time = time.time()
        
        self.logger.info(f"Servidor UDP iniciado na porta {self.udp_port}")
        self.logger.info("Aguardando dispositivos ESP32...")
        self.logger.info("Compatibilidade ESP32: ✅ Serial, ✅ STA, ✅ AP")
        self.logger.info(f"Suporte a redes: STA={self.local_network}.x, AP=192.168.4.x")
        return True

    def _listener_loop(self):
        """Loop para receber mensagens dos dispositivos ESP32"""
        self.logger.info("Listener iniciado - Aguardando ESP32...")
        
        while self.running:
            try:
                data, addr = self.sock.recvfrom(1024)
                ip = addr[0]
                
                raw_msg = data.decode().strip()
                
                # CORREÇÃO: Aceitar mensagens JSON e comandos simples
                if raw_msg.startswith('{'):
                    try:
                        msg_data = json.loads(raw_msg)
                        self.msg_queue.put((msg_data, addr))
                        self.messages_processed += 1
                        self.logger.debug(f"📝 JSON de {ip}: {msg_data.get('type', 'UNKNOWN')}")
                            
                    except json.JSONDecodeError as e:
                        self.logger.warning(f"❌ JSON inválido de {ip}: {e}")
                    except Exception as e:
                        self.logger.error(f"❌ Erro ao processar mensagem de {ip}: {e}")
                else:
                    # CORREÇÃO: Processar comandos simples do ESP32
                    self._handle_simple_command(raw_msg, ip, addr)
                        
            except socket.timeout:
                continue
            except Exception as e:
                self.logger.error(f"❌ Erro no listener: {e}")
                time.sleep(1)

    def _handle_simple_command(self, raw_msg, ip, addr):
        """Processar comandos simples do ESP32"""
        try:
            command = raw_msg.upper().strip()
            
            if command in ['STATUS', 'HELP', 'RESTART']:
                msg_data = {
                    'type': 'SERIAL_COMMAND',
                    'command': command,
                    'source': 'serial',
                    'timestamp': time.time()
                }
                self.msg_queue.put((msg_data, addr))
                self.logger.debug(f"🔧 Comando serial de {ip}: {command}")
            else:
                self.logger.debug(f"📨 Mensagem simples de {ip}: {raw_msg[:50]}...")
                
        except Exception as e:
            self.logger.debug(f"Erro ao processar comando simples: {e}")

    def _processor_loop(self):
        """Processar mensagens recebidas"""
        while self.running:
            try:
                msg_data, addr = self.msg_queue.get(timeout=1.0)
                self._handle_json_message(msg_data, addr)
            except queue.Empty:
                continue
            except Exception as e:
                self.logger.error(f"❌ Erro no processador: {e}")

    def _handle_json_message(self, data, addr):
        """Processar mensagem JSON baseada no tipo"""
        ip = addr[0]
        
        if not isinstance(data, dict):
            self.logger.warning(f"⚠️ Mensagem não é dicionário: {type(data)}")
            return
            
        msg_type = self._extract_message_type(data)
        
        # Identificar tipo de rede do dispositivo ESP32
        network_type = self._identify_network_type(ip)
        
        self.logger.info(f"✅ {msg_type} de {ip} ({network_type})")
        
        # ================== DISCOVERY ==================
        if msg_type == 'DISCOVERY':
            self._handle_discovery(data, ip, network_type)

        # ================== DEVICE_REGISTER ==================
        elif msg_type == 'DEVICE_REGISTER':
            self._handle_device_register(data, ip, network_type)
            print(self.devices)

        # ================== HEARTBEAT ==================
        elif msg_type == 'HEARTBEAT':
            self._handle_heartbeat(data, ip, network_type)

        # ================== MOVEMENT_DETECTED ==================
        elif msg_type == 'MOVEMENT_DETECTED':
            self._handle_movement_detected(data, ip, network_type)

        # ================== WASTE_ACK ==================
        elif msg_type == 'WASTE_ACK':
            self._handle_waste_ack(data, ip, network_type)

        # ================== HEARTBEAT_RESPONSE ==================
        elif msg_type == 'HEARTBEAT_RESPONSE':
            self._handle_heartbeat_response(data, ip, network_type)

        # ================== SYSTEM_STATUS ==================
        elif msg_type == 'SYSTEM_STATUS':
            self._handle_system_status(data, ip, network_type)

        # ================== SERIAL_COMMAND ==================
        elif msg_type == 'SERIAL_COMMAND':
            self._handle_serial_command(data, ip, network_type)

        else:
            self.logger.info(f"📨 Mensagem não reconhecida de {ip}: {list(data.keys())}")

    def _identify_network_type(self, ip):
        """Identificar se o ESP32 está em modo AP ou STA"""
        if ip.startswith("192.168.4."):  # Rede AP comum do ESP32
            return "AP_MODE"
        elif ip.startswith(self.local_network + "."):
            return "STA_MODE"
        else:
            return "UNKNOWN_NETWORK"

    def _extract_message_type(self, data):
        """Extrair tipo da mensagem"""
        return data.get('type', 'UNKNOWN')

    def _handle_discovery(self, data, ip, network_type):
        """Processar pedido de discovery do ESP32"""
        device_id = data.get('device_id', 'unknown')
        device_name = data.get('device_name', 'ESP32_Desconhecido')
        
        device_info = {
            'device_id': device_id,
            'device_name': device_name,
            'device_type': data.get('device_type', 'TRASH_CAN'),
            'network_mode': network_type,
            'ip_address': ip,
            'connected': True,
            'last_seen': time.time(),
            'ap_mode': network_type == 'AP_MODE',
            'protocol': data.get('network_mode', 'UNKNOWN')
        }
        
        self.devices[device_id] = device_info
        self.logger.success(f"🔍 DISCOVERY: {device_name} ({device_id}) - {network_type}")
        
        # CORREÇÃO: Responder DISCOVERY_RESPONSE compatível com ESP32
        server_ip = self._get_server_ip_for_device(ip, network_type)
        response = {
            'type': 'DISCOVERY_RESPONSE',
            'server_ip': server_ip,
            'server_port': self.udp_port,
            'server_name': 'Servidor Smart Trash',
            'network_type': network_type,
            'timestamp': time.time()
        }
        
        self.logger.info(f"📤 Enviando DISCOVERY_RESPONSE para {ip}")
        self._send_to_esp32(response, ip)

    def _handle_device_register(self, data, ip, network_type):
        """Processar registro do ESP32"""
        device_info = data.get('device_info', {})
        device_id = device_info.get('device_id', data.get('device_id'))
        
        if device_id:
            device_info.update({
                'network_mode': network_type,
                'ap_mode': network_type == 'AP_MODE',
                'ip_address': ip,
                'last_seen': time.time(),
                'connected': True
            })
            
            self.devices[device_id] = device_info
            device_name = device_info.get('device_name', 'ESP32_Desconhecido')
            self.logger.success(f"📝 ESP32 registrado: {device_name} ({ip})")
            
            # CORREÇÃO: Confirmar registro
            response = {
                'type': 'REGISTRATION_ACK',
                'status': 'SUCCESS',
                'message': 'Registro realizado',
                'timestamp': time.time()
            }
            self._send_to_esp32(response, ip)
        else:
            self.logger.error("❌ Falha no registro: device_id não encontrado")

    def _handle_heartbeat(self, data, ip, network_type):
        """Processar heartbeat do ESP32"""
        device_id = data.get('device_id')
        if device_id in self.devices:
            self.devices[device_id]['last_seen'] = time.time()
            self.devices[device_id]['uptime'] = data.get('uptime', 0)
            self.logger.debug(f"💓 Heartbeat de {device_id}")
            
            # CORREÇÃO: Responder heartbeat
            response = {
                'type': 'HEARTBEAT_ACK',
                'timestamp': time.time(),
                'message': 'Heartbeat OK'
            }
            self._send_to_esp32(response, ip)
        else:
            self.logger.warning(f"⚠️ Heartbeat de ESP32 não registrado: {device_id}")

    def _handle_movement_detected(self, data, ip, network_type):
        """Processar movimento detectado pelo ESP32"""
        device_id = data.get('device_id')
        device_name = data.get('device_name', device_id)
        
        self.logger.info(f"🚨 MOVIMENTO detectado por {device_name} ({ip})")
        
        # Executar callback se definido
        if self.movement_callback:
            try:
                self.movement_callback(device_id, ip, network_type)
            except Exception as e:
                self.logger.error(f"❌ Erro no callback de movimento: {e}")
            
        # CORREÇÃO: Confirmar recebimento
        response = {
            'type': 'MOVEMENT_ACK',
            'status': 'RECEIVED',
            'timestamp': time.time(),
            'message': 'Movimento registrado'
        }
        self._send_to_esp32(response, ip)

    def _handle_waste_ack(self, data, ip, network_type):
        """Processar confirmação de resíduo do ESP32"""
        device_id = data.get('device_id', 'unknown')
        waste_index = data.get('waste_index', 0)
        waste_name = data.get('waste_name', f'Tipo {waste_index}')
        status = data.get('status', 'unknown')
        
        self.logger.info(f"✅ WASTE_ACK: {device_id} processou {waste_name} - Status: {status}")

    def _handle_heartbeat_response(self, data, ip, network_type):
        """Processar resposta de heartbeat"""
        device_id = data.get('device_id')
        self.logger.debug(f"💓 Heartbeat response de {device_id}")

    def _handle_system_status(self, data, ip, network_type):
        """Processar status do sistema do ESP32"""
        device_id = data.get('device_id', 'unknown')
        status = data.get('status', {})
        
        # Atualizar informações do dispositivo
        if device_id in self.devices:
            self.devices[device_id]['last_status'] = status
            self.devices[device_id]['last_seen'] = time.time()
        
        self.logger.info(f"📊 SYSTEM_STATUS de {device_id}: {len(status)} campos")

    def _handle_serial_command(self, data, ip, network_type):
        """Processar comando serial do ESP32"""
        command = data.get('command', 'UNKNOWN')
        device_id = data.get('device_id', 'unknown')
        
        self.logger.info(f"🔧 SERIAL_COMMAND de {device_id}: {command}")
        
        # CORREÇÃO: Responder comandos serial
        if command == "STATUS":
            response = {
                'type': 'SYSTEM_STATUS_RESPONSE',
                'server_status': 'RUNNING',
                'devices_connected': len(self.devices),
                'timestamp': time.time()
            }
            self._send_to_esp32(response, ip)
        elif command == "HELP":
            response = {
                'type': 'HELP_RESPONSE',
                'commands': ['STATUS', 'RESTART', 'HELP'],
                'timestamp': time.time()
            }
            self._send_to_esp32(response, ip)

    def _get_server_ip_for_device(self, device_ip, network_type):
        """Obter IP do servidor apropriado para o ESP32"""
        if network_type == "AP_MODE":
            return "192.168.4.1"  # IP do servidor em rede AP
        else:
            return self._get_server_ip()

    def _get_server_ip(self):
        """Obter IP do servidor"""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            return "127.0.0.1"

    def _send_to_esp32(self, data, ip, port=None):
        """Enviar mensagem para ESP32 - CORREÇÃO: Método robusto"""
        try:
            target_port = self.udp_port
            
            # CORREÇÃO: Garantir que a mensagem seja JSON válido
            if isinstance(data, dict):
                message_str = json.dumps(data)
            else:
                message_str = str(data)
            
            # CORREÇÃO: Limitar tamanho para evitar problemas no ESP32
            if len(message_str) > 512:
                self.logger.warning(f"⚠️ Mensagem muito grande para ESP32: {len(message_str)} bytes")
                message_str = json.dumps({
                    'type': 'ERROR',
                    'message': 'Mensagem muito grande',
                    'timestamp': time.time()
                })
            
            # CORREÇÃO: Múltiplas tentativas de envio
            for attempt in range(3):
                try:
                    self.sock.sendto(message_str.encode('utf-8'), (ip, target_port))
                    self.logger.debug(f"📤 Enviado para {ip}:{target_port} - {data.get('type', 'UNKNOWN')}")
                    return True
                except Exception as e:
                    self.logger.debug(f"⚠️ Tentativa {attempt + 1} falhou para {ip}: {e}")
                    time.sleep(0.1)
            
            self.logger.error(f"❌ Falha ao enviar para {ip} após 3 tentativas")
            return False
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao enviar para ESP32 {ip}: {e}")
            return False

    def _heartbeat_loop(self):
        """Loop para enviar heartbeats para ESP32s"""
        while self.running:
            try:
                current_time = time.time()
                if current_time - self.last_heartbeat > self.heartbeat_interval:
                    self._send_heartbeats_to_esp32s()
                    self.last_heartbeat = current_time
                time.sleep(10)
            except Exception as e:
                self.logger.error(f"❌ Erro no heartbeat loop: {e}")
                time.sleep(30)

    def _send_heartbeats_to_esp32s(self):
        """Enviar heartbeats para ESP32s conectados"""
        for device_id, device_info in self.devices.items():
            try:
                ip = device_info.get('ip_address')
                if ip and device_info.get('connected'):
                    heartbeat_msg = {
                        'type': 'HEARTBEAT_REQUEST',
                        'server_id': 'smart_trash_server',
                        'timestamp': time.time()
                    }
                    self._send_to_esp32(heartbeat_msg, ip)
                    self.logger.debug(f"💓 Heartbeat para {device_id}")
            except Exception as e:
                self.logger.error(f"❌ Erro ao enviar heartbeat para {device_id}: {e}")

    def _cleanup_loop(self):
        """Limpar ESP32s desconectados"""
        while self.running:
            try:
                current_time = time.time()
                disconnected = []
                
                for device_id, device_info in self.devices.items():
                    last_seen = device_info.get('last_seen', 0)
                    if current_time - last_seen > 180:  # 3 minutos
                        disconnected.append(device_id)
                
                for device_id in disconnected:
                    device_name = self.devices[device_id].get('device_name', device_id)
                    del self.devices[device_id]
                    self.logger.warning(f"🔌 ESP32 desconectado: {device_name}")
                    
                time.sleep(60)
            except Exception as e:
                self.logger.error(f"❌ Erro no cleanup loop: {e}")
                time.sleep(60)

    def send_waste_command(self, device_id, waste_index, waste_name):
        """Enviar comando de resíduo para ESP32 específico"""
        if device_id in self.devices:
            device_info = self.devices[device_id]
            ip = device_info.get('ip_address')
            
            if ip:
                command = {
                    'type': 'WASTE_TYPE',
                    'waste_index': waste_index,
                    'waste_name': waste_name,
                    'timestamp': time.time()
                }
                
                success = self._send_to_esp32(command, ip)
                if success:
                    self.logger.info(f"🗑️ Comando enviado para {device_id}: {waste_name}")
                return success
            else:
                self.logger.error(f"❌ IP não encontrado para {device_id}")
                return False
        else:
            self.logger.error(f"❌ ESP32 não encontrado: {device_id}")
            return False

    def send_system_command(self, device_id, command):
        """Enviar comando de sistema para ESP32"""
        if device_id in self.devices:
            device_info = self.devices[device_id]
            ip = device_info.get('ip_address')
            
            if ip:
                system_cmd = {
                    'type': 'SYSTEM_COMMAND',
                    'command': command,
                    'timestamp': time.time()
                }
                
                success = self._send_to_esp32(system_cmd, ip)
                if success:
                    self.logger.info(f"⚙️ Comando para {device_id}: {command}")
                return success
        return False

    def broadcast_discovery(self):
        """Enviar broadcast discovery para encontrar ESP32s"""
        try:
            discovery_msg = {
                'type': 'SERVER_DISCOVERY',
                'server_ip': self._get_server_ip(),
                'server_port': self.udp_port,
                'server_name': 'Smart Trash Server',
                'timestamp': time.time()
            }
            
            message_str = json.dumps(discovery_msg)
            self.sock.sendto(message_str.encode(), (self.broadcast_address, self.udp_port))
            self.logger.info("📡 Broadcast discovery enviado")
            return True
        except Exception as e:
            self.logger.error(f"❌ Erro no broadcast: {e}")
            return False

    def set_movement_callback(self, callback):
        """Definir callback para movimento detectado"""
        self.movement_callback = callback

    def get_connected_devices(self):
        """Obter lista de ESP32s conectados"""
        return self.devices.copy()

    def get_server_stats(self):
        """Obter estatísticas do servidor"""
        uptime = time.time() - self.start_time
        connected_count = sum(1 for device in self.devices.values() if device.get('connected'))
        
        return {
            'uptime': uptime,
            'messages_processed': self.messages_processed,
            'esp32_connected': connected_count,
            'total_esp32': len(self.devices),
            'server_ip': self._get_server_ip(),
            'local_network': self.local_network
        }

    def stop(self):
        """Parar servidor"""
        self.running = False
        if self.sock:
            self.sock.close()
        self.logger.info("🛑 Servidor parado")