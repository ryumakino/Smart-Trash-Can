import socket
import network
import time
import _thread
from machine import UART, Pin, PWM
import hashlib
import hmac
import json
import gc
import sys

from servo_control import Servo
from sensor import IRSensor
from utils import log_info, log_error, log_success, log_warning, log_debug

# ----------- CONFIGURAÇÕES -----------
class Config:
    WIFI_SSID = "makedc"
    WIFI_PASSWORD = "deco747387"
    UDP_PORT = 8888
    UART_PORT = 1
    UART_BAUD = 115200
    AUTH_KEY = "TR4SH_4I_S3CUR3_K3Y_2024_M4K3DC_D3C0747387".encode()
    SERVO_POSITIONS = [0, 30, 60, 90, 120, 150]
    WASTE_TYPES = ["PLASTICO", "PAPEL", "VIDRO", "METAL", "LIXO", "PAPELAO"]
    RECONNECT_ATTEMPTS = 3
    CONNECTION_TIMEOUT = 10

class SecureESP32Messenger:
    def __init__(self):
        # Configurações
        self.config = Config()
        self.auth_key = self.config.AUTH_KEY
        
        # Estado do sistema
        self.authenticated_ips = set()
        self.connection_status = "disconnected"
        self.last_heartbeat = time.time()
        self.running = True
        
        # Hardware
        self._init_hardware()
        
        # Rede
        self.wlan = network.WLAN(network.STA_IF)
        self.sock = None
        self.ip = None
        self.channel = None
        
        # Threads
        self.threads = {}

    def _init_hardware(self):
        """Inicializa componentes de hardware"""
        try:
            # UART/Serial
            self.uart = UART(self.config.UART_PORT, baudrate=self.config.UART_BAUD)
            self.uart.init(baudrate=self.config.UART_BAUD, timeout=1000)
            log_success("UART inicializada")
        except Exception as e:
            log_error(f"Erro na UART: {e}")
            self.uart = None

        try:
            # Servo motor
            self.servo = Servo()
            log_success("Servo inicializado")
        except Exception as e:
            log_error(f"Erro no servo: {e}")
            self.servo = None

        try:
            # Sensor IR
            self.ir_sensor = IRSensor(callback=self.ir_triggered)
            log_success("Sensor IR inicializado")
        except Exception as e:
            log_error(f"Erro no sensor IR: {e}")
            self.ir_sensor = None

    # --- CONEXÃO WIFI ---
    def connect_wifi(self):
        """Conecta ao WiFi com tratamento de erro robusto"""
        if self.wlan.isconnected():
            log_info(f"Já conectado ao WiFi: {self.wlan.ifconfig()[0]}")
            return True
            
        self.wlan.active(True)
        self.wlan.disconnect()
        time.sleep(1)
        
        log_info(f"Conectando ao WiFi: {self.config.WIFI_SSID}")
        
        for attempt in range(self.config.RECONNECT_ATTEMPTS):
            try:
                self.wlan.connect(self.config.WIFI_SSID, self.config.WIFI_PASSWORD)
                
                # Aguarda conexão
                start_time = time.time()
                while not self.wlan.isconnected():
                    if time.time() - start_time > self.config.CONNECTION_TIMEOUT:
                        raise OSError("Timeout na conexão WiFi")
                    time.sleep(0.5)
                
                self.ip = self.wlan.ifconfig()[0]
                log_success(f"Conectado! IP: {self.ip}")
                self.connection_status = "connected"
                return True
                
            except Exception as e:
                log_error(f"Tentativa {attempt + 1} falhou: {e}")
                if attempt < self.config.RECONNECT_ATTEMPTS - 1:
                    log_info("Tentando reconectar...")
                    time.sleep(2)
        
        log_error("Falha ao conectar ao WiFi")
        self.connection_status = "disconnected"
        return False

    # --- CONFIGURAÇÃO UDP ---
    def setup_udp(self):
        """Configura socket UDP"""
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            self.sock.settimeout(1.0)
            self.sock.bind(('', self.config.UDP_PORT))
            log_success(f"Socket UDP na porta {self.config.UDP_PORT}")
            return True
        except Exception as e:
            log_error(f"Erro no UDP: {e}")
            self.sock = None
            return False

    # --- SEGURANÇA ---
    def _verify_auth_token(self, token_str):
        """Verifica token de autenticação"""
        try:
            token = json.loads(token_str)
            timestamp = int(token['timestamp'])
            current_time = int(time.time())
            
            # Prevenção contra replay attacks
            if abs(current_time - timestamp) > 30:
                log_warning("Token expirado")
                return False
            
            # Verifica assinatura
            expected_signature = hmac.new(
                self.auth_key, 
                token['message'].encode(), 
                hashlib.sha256
            ).hexdigest()
            
            return hmac.compare_digest(expected_signature, token['signature'])
        except Exception as e:
            log_error(f"Erro na verificação do token: {e}")
            return False

    def _generate_response_token(self):
        """Gera token de resposta"""
        timestamp = str(int(time.time()))
        message = f"RESP_{timestamp}"
        signature = hmac.new(self.auth_key, message.encode(), hashlib.sha256).hexdigest()
        
        token = {
            'timestamp': timestamp,
            'signature': signature,
            'message': message
        }
        return json.dumps(token)

    def _encrypt_message(self, msg):
        """Criptografa mensagem"""
        timestamp = str(int(time.time()))
        message_data = {'message': msg, 'timestamp': timestamp}
        message_str = json.dumps(message_data)
        signature = hmac.new(self.auth_key, message_str.encode(), hashlib.sha256).hexdigest()
        
        encrypted = {'data': message_data, 'signature': signature}
        return json.dumps(encrypted)

    def _decrypt_message(self, encrypted_str):
        """Descriptografa mensagem"""
        try:
            encrypted = json.loads(encrypted_str)
            data_str = json.dumps(encrypted['data'])
            expected_signature = hmac.new(
                self.auth_key, 
                data_str.encode(), 
                hashlib.sha256
            ).hexdigest()
            
            if not hmac.compare_digest(expected_signature, encrypted['signature']):
                log_warning("Assinatura inválida")
                return None
            
            timestamp = int(encrypted['data']['timestamp'])
            if abs(int(time.time()) - timestamp) > 30:
                log_warning("Mensagem expirada")
                return None
                
            return encrypted['data']['message']
        except Exception as e:
            log_error(f"Erro na descriptografia: {e}")
            return None

    # --- HANDLERS DE COMANDOS ---
    def handle_secure_command(self, msg, addr=None):
        """Processa comandos seguros recebidos"""
        decrypted = self._decrypt_message(msg)
        if not decrypted:
            log_warning("Comando inseguro rejeitado")
            return
        
        log_info(f"Comando recebido: {decrypted}")
        
        if decrypted.startswith("WASTE_TYPE:"):
            self._handle_waste_type(decrypted)
        elif decrypted == "STATUS":
            self._send_status(addr)
        elif decrypted == "PING":
            self._send_pong(addr)

    def _handle_waste_type(self, command):
        """Processa comando de tipo de resíduo"""
        try:
            waste_index = int(command.split(":")[1])
            if 0 <= waste_index < len(self.config.SERVO_POSITIONS):
                angle = self.config.SERVO_POSITIONS[waste_index]
                waste_name = self.config.WASTE_TYPES[waste_index]
                
                log_info(f"Movendo servo para {waste_name} ({angle}°)")
                
                if self.servo:
                    self.servo.move(angle)
                    # Reseta após delay em thread separada
                    _thread.start_new_thread(self._reset_servo_after_delay, (3,))
                else:
                    log_error("Servo não disponível")
            else:
                log_error(f"Índice de resíduo inválido: {waste_index}")
                
        except Exception as e:
            log_error(f"Erro no comando WASTE_TYPE: {e}")

    def _reset_servo_after_delay(self, delay_seconds):
        """Reseta servo após delay (executado em thread)"""
        time.sleep(delay_seconds)
        if self.servo:
            self.servo.reset_servo()

    def _send_status(self, addr):
        """Envia status do sistema"""
        status = {
            "wifi_connected": self.wlan.isconnected(),
            "ip": self.ip,
            "authenticated_ips": list(self.authenticated_ips),
            "memory_free": gc.mem_free(),
            "channel": self.channel
        }
        status_msg = f"STATUS:{json.dumps(status)}"
        self._send_secure_response(status_msg, addr)

    def _send_pong(self, addr):
        """Responde a ping"""
        self._send_secure_response("PONG", addr)

    def _send_secure_response(self, msg, addr):
        """Envia resposta segura"""
        try:
            encrypted_msg = self._encrypt_message(msg)
            if addr:  # UDP
                self.sock.sendto(f"RESP:{encrypted_msg}".encode(), addr)
            else:  # Serial
                self.uart.write(f"RESP:{encrypted_msg}\n")
        except Exception as e:
            log_error(f"Erro ao enviar resposta: {e}")

    # --- AUTENTICAÇÃO ---
    def handle_auth_request(self, token_str, addr=None):
        """Processa pedido de autenticação"""
        if not self._verify_auth_token(token_str):
            log_warning("Autenticação falhou")
            return False
        
        log_info(f"Autenticação solicitada por: {addr[0] if addr else 'Serial'}")
        
        response_token = self._generate_response_token()
        
        try:
            if addr:  # UDP
                self.sock.sendto(f"AUTH_OK:{response_token}".encode(), addr)
                self.authenticated_ips.add(addr[0])
                log_success(f"Cliente {addr[0]} autenticado")
            else:  # Serial
                self.uart.write(f"AUTH_OK:{response_token}\n")
                log_success("Cliente Serial autenticado")
            
            return True
        except Exception as e:
            log_error(f"Erro na autenticação: {e}")
            return False

    # --- LISTENERS ---
    def listen_secure_udp(self):
        """Escuta mensagens UDP"""
        log_info("Iniciando listener UDP...")
        
        while self.running and self.channel == "udp":
            try:
                if not self.sock:
                    if not self.setup_udp():
                        time.sleep(2)
                        continue
                
                data, addr = self.sock.recvfrom(1024)
                msg = data.decode().strip()
                
                if msg.startswith("AUTH:"):
                    token_str = msg.split(":", 1)[1]
                    self.handle_auth_request(token_str, addr)
                    
                elif msg.startswith("CMD:"):
                    cmd_data = msg.split(":", 1)[1]
                    if addr[0] in self.authenticated_ips:
                        self.handle_secure_command(cmd_data, addr)
                    else:
                        log_warning(f"Comando de IP não autenticado: {addr[0]}")
                        
            except socket.timeout:
                continue  # Timeout normal, continua listening
            except Exception as e:
                log_error(f"Erro no listener UDP: {e}")
                time.sleep(1)

    def listen_secure_serial(self):
        """Escuta mensagens Serial"""
        log_info("Iniciando listener Serial...")
        
        while self.running and self.channel == "serial":
            try:
                if not self.uart:
                    time.sleep(2)
                    continue
                
                if self.uart.any():
                    msg = self.uart.readline().decode().strip()
                    
                    if msg.startswith("AUTH:"):
                        token_str = msg.split(":", 1)[1]
                        self.handle_auth_request(token_str)
                        
                    elif msg.startswith("CMD:"):
                        cmd_data = msg.split(":", 1)[1]
                        self.handle_secure_command(cmd_data)
                        
            except Exception as e:
                log_error(f"Erro no listener Serial: {e}")
                time.sleep(1)

    # --- SENSOR IR ---
    def ir_triggered(self):
        """Callback do sensor IR - movimento detectado"""
        msg = "MOVIMENTO DETECTADO"
        log_info(f"[IR] {msg}")
        
        try:
            encrypted_msg = self._encrypt_message(msg)
            
            if self.channel == "serial":
                self.uart.write(f"CMD:{encrypted_msg}\n")
            elif self.channel == "udp" and self.sock:
                # Envia broadcast para IPs autenticados
                for ip in self.authenticated_ips:
                    self.sock.sendto(f"CMD:{encrypted_msg}".encode(), (ip, self.config.UDP_PORT))
                    
        except Exception as e:
            log_error(f"Erro ao enviar detecção IR: {e}")

    # --- GERENCIAMENTO DE CANAIS ---
    def select_channel(self):
        """Seleciona canal de comunicação prioritário"""
        if self.uart:
            self.channel = "serial"
            log_info("Canal selecionado: Serial")
        elif self.setup_udp():
            self.channel = "udp"
            log_info("Canal selecionado: UDP")
        else:
            self.channel = None
            log_error("Nenhum canal disponível")

    def monitor_channels(self):
        """Monitora e gerencia os canais de comunicação"""
        while self.running:
            # Verifica se precisa reconectar WiFi
            if not self.wlan.isconnected():
                log_warning("WiFi desconectado, tentando reconectar...")
                self.connect_wifi()
            
            # Verifica canal atual
            if not self.channel:
                self.select_channel()
            
            # Inicia threads apropriadas
            if self.channel == "serial" and "serial" not in self.threads:
                self.threads["serial"] = _thread.start_new_thread(self.listen_secure_serial, ())
            elif self.channel == "udp" and "udp" not in self.threads:
                self.threads["udp"] = _thread.start_new_thread(self.listen_secure_udp, ())
            
            time.sleep(3)

    def check_connection_status(self):
        """Verifica e reporta status da conexão"""
        current_status = "connected" if self.wlan.isconnected() else "disconnected"
        
        if current_status != self.connection_status:
            self.connection_status = current_status
            if current_status == "connected":
                log_success("WiFi reconectado")
            else:
                log_warning("WiFi desconectado")

    # --- CONTROLE DO SISTEMA ---
    def start(self):
        """Inicia o sistema completo"""
        log_info("Iniciando sistema ESP32...")
        
        # Conecta WiFi
        if not self.connect_wifi():
            log_warning("Modo offline - apenas Serial disponível")
        
        # Seleciona canal
        self.select_channel()
        
        # Inicia monitoramento
        _thread.start_new_thread(self.monitor_channels, ())
        
        # Inicia sensor IR
        if self.ir_sensor:
            self.ir_sensor.start()
        
        log_success("Sistema ESP32 pronto!")

    def stop(self):
        """Para o sistema graciosamente"""
        log_info("Parando sistema ESP32...")
        self.running = False
        
        # Para hardware
        if self.servo:
            self.servo.reset_servo()
        
        if self.ir_sensor:
            self.ir_sensor.stop()
        
        # Fecha conexões
        if self.sock:
            self.sock.close()
        
        self.wlan.disconnect()
        log_info("Sistema ESP32 parado")

# Alias para compatibilidade
ESP32Messenger = SecureESP32Messenger