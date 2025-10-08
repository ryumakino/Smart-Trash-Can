# security.py - Segurança para servidor (Refatorado para JSON)
import time
import json
import hmac
import hashlib
import base64
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes
from src.core.base_classes import BaseService, ConfigurableMixin

class JSONEncryptor:
    """SRP: Criptografia para mensagens JSON"""
    
    def __init__(self, auth_key):
        if isinstance(auth_key, str):
            auth_key = auth_key.encode()
        self.auth_key = hashlib.sha256(auth_key).digest()  # 32 bytes
        self.available = True

    def _pad(self, s: bytes) -> bytes:
        """Padding PKCS7"""
        pad_len = 16 - (len(s) % 16)
        return s + bytes([pad_len]) * pad_len

    def _unpad(self, s: bytes) -> bytes:
        """Remover padding PKCS7"""
        return s[:-s[-1]]

    def encrypt_json(self, data: dict) -> dict:
        """Criptografar dados JSON"""
        try:
            timestamp = int(time.time())
            payload = json.dumps(data).encode()

            iv = get_random_bytes(16)
            cipher = AES.new(self.auth_key, AES.MODE_CBC, iv)
            encrypted = cipher.encrypt(self._pad(payload))

            # Gera HMAC do conteúdo criptografado
            signature = hmac.new(self.auth_key, iv + encrypted, hashlib.sha256).hexdigest()

            return {
                "encrypted": True,
                "iv": base64.b64encode(iv).decode(),
                "data": base64.b64encode(encrypted).decode(),
                "signature": signature,
                "timestamp": timestamp
            }
        except Exception as e:
            print(f"Erro ao criptografar JSON: {e}")
            return data

    def decrypt_json(self, encrypted_data: dict) -> dict:
        """Descriptografar dados JSON com verificação de integridade"""
        try:
            # Verificar se é um pacote criptografado
            if not encrypted_data.get("encrypted", False):
                return encrypted_data

            iv = base64.b64decode(encrypted_data["iv"])
            encrypted = base64.b64decode(encrypted_data["data"])
            signature = encrypted_data["signature"]

            # Verifica HMAC
            expected_signature = hmac.new(
                self.auth_key, iv + encrypted, hashlib.sha256
            ).hexdigest()
            
            if not hmac.compare_digest(signature, expected_signature):
                print("HMAC inválido na mensagem")
                return None

            cipher = AES.new(self.auth_key, AES.MODE_CBC, iv)
            decrypted = self._unpad(cipher.decrypt(encrypted))
            payload = json.loads(decrypted.decode())

            # Verifica timeout (opcional para JSON)
            timestamp = encrypted_data.get("timestamp", 0)
            if abs(int(time.time()) - timestamp) > 30:  # 30s timeout
                print("Mensagem expirada")
                return None

            return payload
        except Exception as e:
            print(f"Erro ao descriptografar JSON: {e}")
            return None

class SecureJSONCommunicator:
    """Facade simplificada para comunicação JSON segura"""
    
    def __init__(self, auth_key: str):
        self.encryptor = JSONEncryptor(auth_key)
    
    def prepare_outgoing_message(self, data: dict, encrypt: bool = True) -> dict:
        """Preparar mensagem JSON para envio"""
        if encrypt and self.encryptor.available:
            return self.encryptor.encrypt_json(data)
        else:
            # Adicionar timestamp mesmo sem criptografia
            data['timestamp'] = time.time()
            return data
    
    def process_incoming_message(self, data: dict, decrypt: bool = True) -> dict:
        """Processar mensagem JSON recebida"""
        if decrypt and self.encryptor.available:
            return self.encryptor.decrypt_json(data)
        else:
            return data
    
    def is_encrypted_message(self, data: dict) -> bool:
        """Verificar se a mensagem está criptografada"""
        return data.get('encrypted', False)

class SecurityManager(BaseService, ConfigurableMixin):
    def __init__(self):
        super().__init__('network')
        auth_key = self.get_config_value('AUTH_KEY', 'DEFAULT_KEY')
        token_timeout = self.get_config_value('TOKEN_TIMEOUT', 300)
        
        self.json_communicator = SecureJSONCommunicator(auth_key)
        self.token_timeout = token_timeout
        self._initialized = False

    def initialize(self):
        """Inicializar gerenciador de segurança"""
        if self._initialized:
            return True
            
        try:
            self._initialized = True
            self.logger.success("SecurityManager inicializado")
            return True
        except Exception as e:
            self.logger.error(f"Erro na inicialização: {e}")
            return False

    def prepare_outgoing_message(self, data: dict) -> dict:
        """Preparar mensagem JSON para envio"""
        if not self._initialized:
            self.logger.warning("SecurityManager não inicializado - enviando sem criptografia")
            data['timestamp'] = time.time()
            return data
            
        return self.json_communicator.prepare_outgoing_message(data)

    def process_incoming_message(self, data: dict) -> dict:
        """Processar mensagem JSON recebida"""
        if not self._initialized:
            self.logger.warning("SecurityManager não inicializado - processando sem descriptografia")
            return data
            
        return self.json_communicator.process_incoming_message(data)

    def is_encrypted_message(self, data: dict) -> bool:
        """Verificar se a mensagem está criptografada"""
        return self.json_communicator.is_encrypted_message(data)

    def get_status(self):
        """Obter status do gerenciador de segurança"""
        base_status = super().get_status()
        base_status.update({
            'encryption_enabled': self._initialized,
            'token_timeout': self.token_timeout,
            'algorithm': 'AES-256-CBC with HMAC-SHA256',
            'json_communication': True
        })
        return base_status