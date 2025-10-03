# security.py - Segurança para servidor (Refatorado)
import time
import json
import hmac
import hashlib
import base64
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes
from src.core.base_classes import BaseService, ConfigurableMixin

class SecurityManager(BaseService, ConfigurableMixin):
    def __init__(self):
        super().__init__('network')
        auth_key = self.get_config_value('AUTH_KEY', 'DEFAULT_KEY')
        token_timeout = self.get_config_value('TOKEN_TIMEOUT', 30)
        
        if isinstance(auth_key, str):
            auth_key = auth_key.encode()
        self.auth_key = hashlib.sha256(auth_key).digest()  # 32 bytes
        self.token_timeout = token_timeout

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

    def _pad(self, s: bytes) -> bytes:
        """Padding PKCS7"""
        pad_len = 16 - (len(s) % 16)
        return s + bytes([pad_len]) * pad_len

    def _unpad(self, s: bytes) -> bytes:
        """Remover padding PKCS7"""
        return s[:-s[-1]]

    def encrypt_message(self, msg: str) -> str:
        """Criptografar mensagem"""
        if not self._initialized:
            self.logger.error("SecurityManager não inicializado")
            return None
            
        try:
            timestamp = int(time.time())
            payload = json.dumps({"message": msg, "timestamp": timestamp}).encode()

            iv = get_random_bytes(16)
            cipher = AES.new(self.auth_key, AES.MODE_CBC, iv)
            encrypted = cipher.encrypt(self._pad(payload))

            # Gera HMAC do conteúdo criptografado
            signature = hmac.new(self.auth_key, iv + encrypted, hashlib.sha256).hexdigest()

            packet = {
                "iv": base64.b64encode(iv).decode(),
                "data": base64.b64encode(encrypted).decode(),
                "signature": signature,
            }
            self.logger.debug(f"Mensagem criptografada: {msg}")
            return json.dumps(packet)
        except Exception as e:
            self.logger.error(f"Erro ao criptografar mensagem: {e}")
            return None

    def decrypt_message(self, enc_str: str):
        """Descriptografar mensagem"""
        if not self._initialized:
            self.logger.error("SecurityManager não inicializado")
            return None
            
        try:
            packet = json.loads(enc_str)
            iv = base64.b64decode(packet["iv"])
            encrypted = base64.b64decode(packet["data"])
            signature = packet["signature"]

            # Verifica HMAC
            expected_signature = hmac.new(
                self.auth_key, iv + encrypted, hashlib.sha256
            ).hexdigest()
            if not hmac.compare_digest(signature, expected_signature):
                self.logger.warning("HMAC inválido na mensagem")
                return None

            cipher = AES.new(self.auth_key, AES.MODE_CBC, iv)
            decrypted = self._unpad(cipher.decrypt(encrypted))
            payload = json.loads(decrypted.decode())

            # Verifica timeout
            if abs(int(time.time()) - int(payload["timestamp"])) > self.token_timeout:
                self.logger.warning("Mensagem expirada")
                return None

            self.logger.debug(f"Mensagem descriptografada: {payload['message']}")
            return payload["message"]
        except Exception as e:
            self.logger.error(f"Erro ao descriptografar mensagem: {e}")
            return None

    def get_status(self):
        """Obter status do gerenciador de segurança"""
        base_status = super().get_status()
        base_status.update({
            'encryption_enabled': True,
            'token_timeout': self.token_timeout,
            'algorithm': 'AES-256-CBC with HMAC-SHA256'
        })
        return base_status