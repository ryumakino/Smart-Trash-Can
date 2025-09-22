import socket
import platform
import threading
import serial
import time
import serial.tools.list_ports
import hashlib
import hmac
import json

#  OPERATING SYSTEM
OS_WINDOWS = "Windows"
OS_LINUX = "Linux"
OS_MAC = "Darwin"
OS_UNKNOWN = "Unknown"

OPERATION_SYSTEM: str = platform.system()

# Serial
SERIAL_BAUDRATE: int = 115200
SERIAL_TIMEOUT = 1
TIME_SERIAL_WAIT = 2
if OPERATION_SYSTEM == OS_WINDOWS:
    SERIAL_PORT: str = "COM3"
elif OPERATION_SYSTEM == OS_LINUX:
    SERIAL_PORT: str = "/dev/ttyUSB0"
elif OPERATION_SYSTEM == OS_MAC:
    SERIAL_PORT: str = "/dev/tty.SLAB_USBtoUART"
else:
    SERIAL_PORT: str = ""

# UDP / Wi-Fi
UDP_PORT = 8888

AUTH_KEY = "TR4SH_4I_S3CUR3_K3Y_2024_M4K3DC_D3C0747387"

class SecurePCMessenger:
    """
    Comunicação UDP + Serial com ESP32 com autenticação segura.
    - Autenticação HMAC-SHA256
    - Tokens com timestamp para prevenir replay attacks
    - Prioridade: Serial > UDP
    """

    def __init__(self, udp_port=UDP_PORT):
        # --- Segurança ---
        self.auth_key = AUTH_KEY.encode()
        self.session_token = None
        self.authenticated = False
        
        # --- UDP ---
        self.udp_port = udp_port
        self.sock = None
        self.esp_ip = None
        self._stop_flag = False
        self._init_udp()

        # --- Serial ---
        self.serial = None
        self._init_serial()

    def _generate_auth_token(self):
        """Gera token de autenticação com timestamp"""
        timestamp = str(int(time.time()))
        message = f"AUTH_{timestamp}".encode()
        signature = hmac.new(self.auth_key, message, hashlib.sha256).hexdigest()
        token = {
            'timestamp': timestamp,
            'signature': signature,
            'message': message.decode()
        }
        return json.dumps(token)

    def _verify_response_token(self, token_str):
        """Verifica token de resposta do ESP32"""
        try:
            token = json.loads(token_str)
            timestamp = int(token['timestamp'])
            current_time = int(time.time())
            
            # Verifica expiração (30 segundos)
            if current_time - timestamp > 30:
                print("[PC] Token expirado")
                return False
            
            # Verifica assinatura
            expected_signature = hmac.new(
                self.auth_key, 
                token['message'].encode(), 
                hashlib.sha256
            ).hexdigest()
            
            return hmac.compare_digest(expected_signature, token['signature'])
        except:
            return False

    def _encrypt_message(self, msg):
        """Criptografa mensagem com HMAC"""
        timestamp = str(int(time.time()))
        message_data = {
            'message': msg,
            'timestamp': timestamp
        }
        message_str = json.dumps(message_data)
        signature = hmac.new(self.auth_key, message_str.encode(), hashlib.sha256).hexdigest()
        
        encrypted = {
            'data': message_data,
            'signature': signature
        }
        return json.dumps(encrypted)

    def _decrypt_message(self, encrypted_str):
        """Descriptografa e verifica mensagem"""
        try:
            encrypted = json.loads(encrypted_str)
            data_str = json.dumps(encrypted['data'])
            expected_signature = hmac.new(
                self.auth_key, 
                data_str.encode(), 
                hashlib.sha256
            ).hexdigest()
            
            if not hmac.compare_digest(expected_signature, encrypted['signature']):
                print("[PC] Assinatura inválida")
                return None
            
            # Verifica timestamp (mensagem não pode ser muito antiga)
            timestamp = int(encrypted['data']['timestamp'])
            if int(time.time()) - timestamp > 30:
                print("[PC] Mensagem expirada")
                return None
                
            return encrypted['data']['message']
        except:
            return None

    # ======================================================================
    # --- Inicialização UDP ---
    # ======================================================================
    def _init_udp(self):
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.sock.bind(('', self.udp_port))
            print(f"[PC] Socket UDP seguro criado na porta {self.udp_port}")
        except Exception as e:
            print(f"[PC] Falha ao criar socket UDP: {e}")
            self.sock = None

    # ======================================================================
    # --- Inicialização Serial ---
    # ======================================================================
    def _init_serial(self):
        ports = list(serial.tools.list_ports.comports())
        for p in ports:
            try:
                self.serial = serial.Serial(p.device, SERIAL_BAUDRATE, timeout=SERIAL_TIMEOUT)
                time.sleep(TIME_SERIAL_WAIT)
                print(f"[PC] Serial segura inicializada em {p.device}")
                
                # Autenticação via Serial
                auth_msg = self._generate_auth_token()
                self.serial.write((f"AUTH:{auth_msg}\n").encode())
                time.sleep(1)
                return
            except Exception as e:
                print(f"[PC] Falha ao abrir {p.device}: {e}")
                continue
        print("[PC] Nenhuma Serial disponível")
        self.serial = None

    def _reconnect_serial(self):
        """Reconecta Serial com reautenticação"""
        if self.serial and not self.serial.is_open:
            try:
                self.serial.open()
                print("[PC] Reconectando Serial...")
                # Reautenticação
                auth_msg = self._generate_auth_token()
                self.serial.write((f"AUTH:{auth_msg}\n").encode())
                time.sleep(1)
            except Exception as e:
                print(f"[PC] Falha ao reconectar Serial: {e}")
                time.sleep(2)
        elif self.serial is None:
            self._init_serial()

    # ======================================================================
    # --- Envio seguro de mensagens ---
    # ======================================================================
    def send_to_esp32_serial(self, msg):
        if not self.serial or not self.serial.is_open:
            self._reconnect_serial()
            if not self.serial:
                return False
        
        if not self.authenticated:
            print("[PC] Não autenticado, tentando autenticar...")
            if not self._authenticate_serial():
                return False
        
        try:
            encrypted_msg = self._encrypt_message(msg)
            self.serial.write((f"CMD:{encrypted_msg}\n").encode())
            print(f"[PC] Enviado via Serial segura: {msg}")
            return True
        except Exception as e:
            print(f"[PC] Erro ao enviar Serial: {e}")
            self.serial = None
            return False

    def send_to_esp32_udp(self, msg):
        if not self.sock:
            return False
        
        if not self.esp_ip:
            self.discover_esp32()
            if not self.esp_ip:
                return False
        
        if not self.authenticated:
            if not self._authenticate_udp():
                return False
        
        try:
            encrypted_msg = self._encrypt_message(msg)
            self.sock.sendto(f"CMD:{encrypted_msg}".encode(), (self.esp_ip, self.udp_port))
            print(f"[PC] Enviado via UDP seguro para {self.esp_ip}: {msg}")
            return True
        except Exception as e:
            print(f"[PC] Erro ao enviar UDP: {e}")
            return False

    def send_command(self, msg):
        """Envio seguro priorizando Serial"""
        if self.serial and self.serial.is_open:
            return self.send_to_esp32_serial(msg)
        elif self.esp_ip:
            return self.send_to_esp32_udp(msg)
        else:
            print("[PC] Nenhum canal seguro disponível")
            return False

    # ======================================================================
    # --- Autenticação ---
    # ======================================================================
    def _authenticate_serial(self):
        """Autenticação via Serial"""
        try:
            auth_msg = self._generate_auth_token()
            self.serial.write((f"AUTH:{auth_msg}\n").encode())
            
            # Aguarda resposta
            timeout = time.time() + 5
            while time.time() < timeout:
                if self.serial.in_waiting:
                    response = self.serial.readline().decode().strip()
                    if response.startswith("AUTH_OK:"):
                        token_str = response.split(":", 1)[1]
                        if self._verify_response_token(token_str):
                            self.authenticated = True
                            print("[PC] Autenticação Serial bem-sucedida")
                            return True
                time.sleep(0.1)
        except Exception as e:
            print(f"[PC] Erro na autenticação Serial: {e}")
        
        self.authenticated = False
        return False

    def _authenticate_udp(self):
        """Autenticação via UDP"""
        try:
            auth_msg = self._generate_auth_token()
            self.sock.sendto(f"AUTH:{auth_msg}".encode(), (self.esp_ip, self.udp_port))
            
            # Aguarda resposta
            self.sock.settimeout(5)
            try:
                data, addr = self.sock.recvfrom(1024)
                response = data.decode().strip()
                if response.startswith("AUTH_OK:") and addr[0] == self.esp_ip:
                    token_str = response.split(":", 1)[1]
                    if self._verify_response_token(token_str):
                        self.authenticated = True
                        print("[PC] Autenticação UDP bem-sucedida")
                        return True
            except socket.timeout:
                print("[PC] Timeout na autenticação UDP")
        except Exception as e:
            print(f"[PC] Erro na autenticação UDP: {e}")
        
        self.authenticated = False
        return False

    # ======================================================================
    # --- Descoberta segura do ESP32 ---
    # ======================================================================
    def discover_esp32(self, timeout=5):
        if not self.sock:
            return None
        
        print("[PC] Descobrindo ESP32 de forma segura...")
        self.sock.settimeout(timeout)
        
        try:
            # Envia PING criptografado
            ping_msg = self._encrypt_message("PING")
            self.sock.sendto(f"PING:{ping_msg}".encode(), ('255.255.255.255', self.udp_port))
            
            data, addr = self.sock.recvfrom(1024)
            response = data.decode().strip()
            
            if response.startswith("PONG:"):
                pong_data = response.split(":", 1)[1]
                decrypted = self._decrypt_message(pong_data)
                if decrypted == "PONG":
                    self.esp_ip = addr[0]
                    print(f"[PC] ESP32 seguro encontrado em {self.esp_ip}")
                    return self.esp_ip
                    
        except socket.timeout:
            print("[PC] Timeout na descoberta segura")
        except Exception as e:
            print(f"[PC] Erro na descoberta: {e}")
        
        return None

    # ======================================================================
    # --- Listeners seguros ---
    # ======================================================================
    def listen_udp(self):
        while not self._stop_flag:
            if not self.sock:
                time.sleep(1)
                continue
            
            try:
                data, addr = self.sock.recvfrom(1024)
                msg = data.decode(errors="ignore").strip()
                
                if msg.startswith("PONG:"):
                    pong_data = msg.split(":", 1)[1]
                    decrypted = self._decrypt_message(pong_data)
                    if decrypted == "PONG":
                        self.esp_ip = addr[0]
                        print(f"[PC] ESP32 seguro encontrado em {self.esp_ip}")
                
                elif msg.startswith("AUTH_OK:"):
                    # Processa autenticação
                    token_str = msg.split(":", 1)[1]
                    if self._verify_response_token(token_str):
                        self.authenticated = True
                        print("[PC] Autenticado via UDP")
                
                elif msg.startswith("CMD:"):
                    # Mensagem criptografada
                    cmd_data = msg.split(":", 1)[1]
                    decrypted = self._decrypt_message(cmd_data)
                    if decrypted:
                        self.handle_secure_message(decrypted, addr)
                
            except socket.timeout:
                continue
            except Exception as e:
                print(f"[PC] Erro UDP seguro: {e}")

    def listen_serial(self):
        while not self._stop_flag:
            if not self.serial:
                time.sleep(1)
                continue
            
            try:
                if self.serial.is_open and self.serial.in_waiting:
                    msg = self.serial.readline().decode(errors="ignore").strip()
                    
                    if msg.startswith("AUTH_OK:"):
                        token_str = msg.split(":", 1)[1]
                        if self._verify_response_token(token_str):
                            self.authenticated = True
                            print("[PC] Autenticado via Serial")
                    
                    elif msg.startswith("CMD:"):
                        cmd_data = msg.split(":", 1)[1]
                        decrypted = self._decrypt_message(cmd_data)
                        if decrypted:
                            self.handle_secure_message(decrypted)
                
                elif not self.serial.is_open:
                    self._reconnect_serial()
                    
            except Exception as e:
                print(f"[PC] Erro Serial seguro: {e}")
                self.serial = None
                time.sleep(1)

    # ======================================================================
    # --- Tratamento de mensagens seguras ---
    # ======================================================================
    def handle_secure_message(self, msg, addr=None):
        """Método para processar mensagens descriptografadas"""
        print(f"[PC] Mensagem segura recebida: {msg}")
        
        if msg == "MOVIMENTO DETECTADO":
            from main import on_movement_detected
            on_movement_detected(self)

    # ======================================================================
    # --- Controle da aplicação ---
    # ======================================================================
    def start(self):
        if self.sock:
            self.sock.settimeout(1.0)
            threading.Thread(target=self.listen_udp, daemon=True).start()
        
        if self.serial:
            threading.Thread(target=self.listen_serial, daemon=True).start()
        
        # Descoberta inicial
        if self.sock:
            threading.Thread(target=self.discover_esp32, daemon=True).start()
        
        print("[PC] Sistema de comunicação seguro iniciado!")

    def stop(self):
        self._stop_flag = True
        if self.serial:
            self.serial.close()
        if self.sock:
            self.sock.close()
        print("[PC] Comunicação segura encerrada")

# Alias para compatibilidade
PCMessenger = SecurePCMessenger