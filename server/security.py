# security.py - Segurança para servidor
import time
import json
import hmac
import hashlib
import base64
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes
from utils import get_logger

logger = get_logger("Security")

class SecurityManager:
    def __init__(self, auth_key: str, token_timeout: int):
        if isinstance(auth_key, str):
            auth_key = auth_key.encode()
        self.auth_key = hashlib.sha256(auth_key).digest()  # 32 bytes
        self.token_timeout = token_timeout

    def _pad(self, s: bytes) -> bytes:
        """Padding PKCS7"""
        pad_len = 16 - (len(s) % 16)
        return s + bytes([pad_len]) * pad_len

    def _unpad(self, s: bytes) -> bytes:
        """Remover padding PKCS7"""
        return s[:-s[-1]]

    def encrypt_message(self, msg: str) -> str:
        """Criptografar mensagem"""
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
            return json.dumps(packet)
        except Exception as e:
            logger.error(f"Erro ao criptografar mensagem: {e}")
            return None

    def decrypt_message(self, enc_str: str):
        """Descriptografar mensagem"""
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
                logger.warning("HMAC inválido na mensagem")
                return None

            cipher = AES.new(self.auth_key, AES.MODE_CBC, iv)
            decrypted = self._unpad(cipher.decrypt(encrypted))
            payload = json.loads(decrypted.decode())

            # Verifica timeout
            if abs(int(time.time()) - int(payload["timestamp"])) > self.token_timeout:
                logger.warning("Mensagem expirada")
                return None

            return payload["message"]
        except Exception as e:
            logger.error(f"Erro ao descriptografar mensagem: {e}")
            return None