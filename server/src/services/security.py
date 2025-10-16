# security_refactored.py – DRY + SOLID
import time, json, hmac, hashlib, base64
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes
from src.core.base_classes import BaseService, ConfigurableMixin

class JSONEncryptor:
    def __init__(self, auth_key: str | bytes):
        if isinstance(auth_key, str):
            auth_key = auth_key.encode()
        self._key = hashlib.sha256(auth_key).digest()

    # ---------- public api ---------- #
    def encrypt_json(self, data: dict) -> dict:
        try:
            payload = json.dumps(data).encode()
            iv = get_random_bytes(16)
            cipher = AES.new(self._key, AES.MODE_CBC, iv)
            encrypted = cipher.encrypt(self._pad(payload))
            signature = hmac.new(self._key, iv + encrypted, hashlib.sha256).hexdigest()
            return {
                "encrypted": True,
                "iv": base64.b64encode(iv).decode(),
                "data": base64.b64encode(encrypted).decode(),
                "signature": signature,
                "timestamp": int(time.time())
            }
        except Exception as e:
            print(f"Erro ao criptografar JSON: {e}")
            return data

    def decrypt_json(self, encrypted_data: dict) -> dict | None:
        try:
            if not encrypted_data.get("encrypted", False):
                return encrypted_data
            iv = base64.b64decode(encrypted_data["iv"])
            encrypted = base64.b64decode(encrypted_data["data"])
            signature = encrypted_data["signature"]
            expected = hmac.new(self._key, iv + encrypted, hashlib.sha256).hexdigest()
            if not hmac.compare_digest(signature, expected):
                print("HMAC inválido")
                return None
            cipher = AES.new(self._key, AES.MODE_CBC, iv)
            decrypted = self._unpad(cipher.decrypt(encrypted))
            payload = json.loads(decrypted.decode())
            ts = encrypted_data.get("timestamp", 0)
            if abs(int(time.time()) - ts) > 30:
                print("Mensagem expirada")
                return None
            return payload
        except Exception as e:
            print(f"Erro ao descriptografar JSON: {e}")
            return None

    # ---------- helpers ---------- #
    @staticmethod
    def _pad(s: bytes) -> bytes:
        pad_len = 16 - (len(s) % 16)
        return s + bytes([pad_len]) * pad_len

    @staticmethod
    def _unpad(s: bytes) -> bytes:
        return s[:-s[-1]]

class SecureJSONCommunicator:
    def __init__(self, auth_key: str):
        self._encryptor = JSONEncryptor(auth_key)

    def prepare_outgoing_message(self, data: dict, encrypt: bool = True) -> dict:
        if encrypt:
            return self._encryptor.encrypt_json(data)
        data['timestamp'] = time.time()
        return data

    def process_incoming_message(self, data: dict, decrypt: bool = True) -> dict | None:
        return self._encryptor.decrypt_json(data) if decrypt else data

    def is_encrypted_message(self, data: dict) -> bool:
        return data.get('encrypted', False)

class SecurityManager(BaseService, ConfigurableMixin):
    def __init__(self):
        super().__init__('network')
        key = self.get_config_value('AUTH_KEY', 'DEFAULT_KEY')
        self._communicator = SecureJSONCommunicator(key)
        self._timeout = self.get_config_value('TOKEN_TIMEOUT', 300)
        self._initialized = False

    # ---------- lifecycle ---------- #
    def initialize(self) -> bool:
        if self._initialized: return True
        self._initialized = True
        self.logger.success("SecurityManager inicializado")
        return True

    # ---------- public api ---------- #
    def prepare_outgoing_message(self, data: dict) -> dict:
        if not self._initialized:
            self.logger.warning("SecurityManager não inicializado – enviando sem criptografia")
            data['timestamp'] = time.time()
            return data
        return self._communicator.prepare_outgoing_message(data)

    def process_incoming_message(self, data: dict) -> dict | None:
        if not self._initialized:
            self.logger.warning("SecurityManager não inicializado – processando sem descriptografia")
            return data
        return self._communicator.process_incoming_message(data)

    def is_encrypted_message(self, data: dict) -> bool:
        return self._communicator.is_encrypted_message(data)

    def get_status(self):
        base = super().get_status()
        base.update({
            'encryption_enabled': self._initialized,
            'token_timeout': self._timeout,
            'algorithm': 'AES-256-CBC with HMAC-SHA256',
            'json_communication': True
        })
        return base