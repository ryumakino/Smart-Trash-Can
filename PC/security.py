import hashlib
import hmac
import json
import time
from config import SystemConfig  # Importação correta
from utils import get_logger

logger = get_logger("Security")

class SecurityManager:
    def __init__(self, auth_key=None):
        self.auth_key = (auth_key or SystemConfig.AUTH_KEY).encode()
    
    def generate_auth_token(self, message_prefix="AUTH"):
        """Gera token de autenticação com timestamp"""
        timestamp = str(int(time.time()))
        message = f"{message_prefix}_{timestamp}".encode()
        signature = hmac.new(self.auth_key, message, hashlib.sha256).hexdigest()
        
        token = {
            'timestamp': timestamp,
            'signature': signature,
            'message': message.decode()
        }
        return json.dumps(token)
    
    def verify_token(self, token_str, message_prefix="AUTH"):
        """Verifica token de autenticação"""
        try:
            token = json.loads(token_str)
            timestamp = int(token['timestamp'])
            current_time = int(time.time())
            
            # Verifica expiração
            if abs(current_time - timestamp) > SystemConfig.TOKEN_TIMEOUT:
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
    
    def encrypt_message(self, msg):
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
    
    def decrypt_message(self, encrypted_str):
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
                return None
            
            # Verifica timestamp
            timestamp = int(encrypted['data']['timestamp'])
            if abs(int(time.time()) - timestamp) > SystemConfig.TOKEN_TIMEOUT:
                return None
                
            return encrypted['data']['message']
        except:
            return None