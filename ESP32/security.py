import uhashlib as hashlib
import ubinascii as binascii
import time
from config import AUTH_KEY
from utils import get_logger

logger = get_logger("Security")

class SecurityManager:
    def __init__(self):
        self.key = AUTH_KEY.encode()
    
    def simple_hash(self, message):
        """Hash simples para MicroPython"""
        return binascii.hexlify(hashlib.sha256(message).digest()).decode()
    
    def verify_token(self, token):
        """Verificação simplificada"""
        try:
            parts = token.split(':')
            if len(parts) != 2:
                return False
            
            timestamp, signature = parts
            current_time = int(time.time())
            
            # Verifica timeout (30 segundos)
            if abs(current_time - int(timestamp)) > 30:
                return False
            
            # Verifica assinatura
            expected = self.simple_hash(timestamp.encode() + self.key)
            return signature == expected
        except:
            return False
    
    def generate_token(self):
        """Gera token simples"""
        timestamp = str(int(time.time()))
        signature = self.simple_hash(timestamp.encode() + self.key)
        return f"{timestamp}:{signature}"