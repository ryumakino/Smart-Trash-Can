# security.py
import ujson as json
import hashlib

class SimpleEncryptor:
    """Criptografia simples para MicroPython"""
    
    def __init__(self, key):
        self.key = key.encode()
    
    def encrypt(self, data):
        if isinstance(data, str):
            data = data.encode()
        
        encrypted = bytearray()
        for i, byte in enumerate(data):
            encrypted.append(byte ^ self.key[i % len(self.key)])
        
        return encrypted.hex()
    
    def decrypt(self, encrypted_data):
        encrypted_bytes = bytes.fromhex(encrypted_data)
        decrypted = bytearray()
        
        for i, byte in enumerate(encrypted_bytes):
            decrypted.append(byte ^ self.key[i % len(self.key)])
        
        return decrypted.decode()

class SecurityManager:
    """Gerenciador de segurança simplificado"""
    
    def __init__(self, auth_key='default_key'):
        self.encryptor = SimpleEncryptor(auth_key)
    
    def prepare_message(self, data):
        """Preparar mensagem segura"""
        if isinstance(data, dict):
            data_str = json.dumps(data)
            return {
                'encrypted': True,
                'payload': self.encryptor.encrypt(data_str)
            }
        return data