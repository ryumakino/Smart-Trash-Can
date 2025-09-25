import ujson as json
import utime as time
import ubinascii
import ucryptolib
import hmac
import hashlib

class SecurityManager:
    def __init__(self, auth_key: str, token_timeout: int = 30):
        if isinstance(auth_key, str):
            auth_key = auth_key.encode()
        self.auth_key = hashlib.sha256(auth_key).digest()  # 32 bytes
        self.token_timeout = token_timeout

    # -------- AES Helpers --------
    def _pad(self, s: bytes) -> bytes:
        pad_len = 16 - (len(s) % 16)
        return s + bytes([pad_len]) * pad_len

    def _unpad(self, s: bytes) -> bytes:
        return s[:-s[-1]]

    # -------- Encrypt / Decrypt --------
    def encrypt_message(self, msg: str) -> str:
        timestamp = int(time.time())
        payload = json.dumps({"message": msg, "timestamp": timestamp}).encode()

        iv = b"1234567890ABCDEF"
        cipher = ucryptolib.aes(self.auth_key, 2, iv)
        encrypted = cipher.encrypt(self._pad(payload))

        signature = hmac.new(self.auth_key, iv + encrypted, hashlib.sha256).hexdigest()

        packet = {
            "iv": ubinascii.b2a_base64(iv).decode().strip(),
            "data": ubinascii.b2a_base64(encrypted).decode().strip(),
            "signature": signature,
        }
        return json.dumps(packet)

    def decrypt_message(self, enc_str: str):
        try:
            packet = json.loads(enc_str)
            iv = ubinascii.a2b_base64(packet["iv"])
            encrypted = ubinascii.a2b_base64(packet["data"])
            signature = packet["signature"]

            expected_signature = hmac.new(
                self.auth_key, iv + encrypted, hashlib.sha256
            ).hexdigest()
            if not hmac.compare_digest(signature, expected_signature):
                return None

            cipher = ucryptolib.aes(self.auth_key, 2, iv)  # CBC
            decrypted = self._unpad(cipher.decrypt(encrypted))
            payload = json.loads(decrypted.decode())

            if abs(int(time.time()) - int(payload["timestamp"])) > self.token_timeout:
                return None

            return payload["message"]
        except Exception:
            return None
