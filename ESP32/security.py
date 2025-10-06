# security.py
import ujson as json
import utime as time
import ubinascii
import ucryptolib
import uhashlib
import urandom
from utils import get_logger

logger = get_logger("Security")

class CryptoHelper:
    """SRP: Utilitários criptográficos reutilizáveis"""
    
    @staticmethod
    def pad_data(data: bytes) -> bytes:
        """Aplicar padding PKCS7"""
        pad_len = 16 - (len(data) % 16)
        return data + bytes([pad_len]) * pad_len
    
    @staticmethod
    def unpad_data(data: bytes) -> bytes:
        """Remover padding PKCS7"""
        return data[:-data[-1]]
    
    @staticmethod
    def compare_digest(a: str, b: str) -> bool:
        """Comparação segura de hashes"""
        if len(a) != len(b):
            return False
        result = 0
        for x, y in zip(a, b):
            result |= ord(x) ^ ord(y)
        return result == 0
    
    @staticmethod
    def generate_random_hex(length: int) -> str:
        """Gerar string hexadecimal aleatória"""
        return ubinascii.hexlify(urandom.getrandbits(length * 4).to_bytes(length // 2, 'big')).decode()

class AESEncryptor:
    """SRP: Criptografia AES"""
    
    def __init__(self, auth_key: bytes):
        if isinstance(auth_key, str):
            auth_key = auth_key.encode()
        self.auth_key = uhashlib.sha256(auth_key).digest()
    
    def encrypt(self, plaintext: str) -> str:
        """Criptografar mensagem com AES-CBC + HMAC"""
        try:
            timestamp = int(time.time())
            payload = json.dumps({"message": plaintext, "timestamp": timestamp}).encode()

            # Gerar IV aleatório
            iv = urandom.getrandbits(128).to_bytes(16, 'big')
            cipher = ucryptolib.aes(self.auth_key, 2, iv)  # Mode 2 = CBC
            encrypted = cipher.encrypt(CryptoHelper.pad_data(payload))

            # Calcular HMAC
            h = uhashlib.sha256(iv + encrypted)
            signature = ubinascii.hexlify(h.digest()).decode()

            packet = {
                "iv": ubinascii.b2a_base64(iv).decode().strip(),
                "data": ubinascii.b2a_base64(encrypted).decode().strip(),
                "signature": signature,
            }
            return json.dumps(packet)
        except Exception as e:
            logger.error(f"Erro ao criptografar: {e}")
            return plaintext  # Fallback

    def decrypt(self, enc_str: str) -> str:
        """Descriptografar mensagem com verificação de integridade"""
        try:
            packet = json.loads(enc_str)
            iv = ubinascii.a2b_base64(packet["iv"])
            encrypted = ubinascii.a2b_base64(packet["data"])
            signature = packet["signature"]

            # Verificar HMAC
            h = uhashlib.sha256(iv + encrypted)
            expected_signature = ubinascii.hexlify(h.digest()).decode()
            
            if not CryptoHelper.compare_digest(signature, expected_signature):
                logger.warning("HMAC verification failed")
                return None

            cipher = ucryptolib.aes(self.auth_key, 2, iv)
            decrypted = CryptoHelper.unpad_data(cipher.decrypt(encrypted))
            payload = json.loads(decrypted.decode())

            # Verificar timestamp
            if abs(int(time.time()) - int(payload["timestamp"])) > 30:  # 30s timeout
                logger.warning("Message timestamp expired")
                return None

            return payload["message"]
        except Exception as e:
            logger.error(f"Erro ao descriptografar: {e}")
            return None

class TokenManager:
    """SRP: Gerenciamento de tokens de autenticação"""
    
    def __init__(self, token_timeout: int = 30):
        self.token_timeout = token_timeout
        self.active_tokens = {}
    
    def generate_token(self, client_id: str, client_ip: str) -> str:
        """Gerar token de autenticação seguro"""
        timestamp = str(int(time.time()))
        random_val = CryptoHelper.generate_random_hex(16)
        
        token_data = f"{client_id}:{client_ip}:{timestamp}:{random_val}"
        token = ubinascii.hexlify(
            uhashlib.sha256(token_data.encode()).digest()
        ).decode()
        
        self.active_tokens[token] = {
            'client_id': client_id,
            'client_ip': client_ip,
            'timestamp': int(timestamp),
            'created': time.time(),
        }
        
        logger.debug(f"Token gerado para {client_id}")
        return token
    
    def validate_token(self, token: str, client_ip: str) -> dict:
        """Validar token de autenticação"""
        if token not in self.active_tokens:
            return None
            
        token_data = self.active_tokens[token]
        current_time = time.time()
        
        # Verificar IP
        if token_data['client_ip'] != client_ip:
            logger.warning(f"Token IP mismatch: {token_data['client_ip']} != {client_ip}")
            return None
        
        # Verificar expiração
        if current_time - token_data['created'] > self.token_timeout:
            del self.active_tokens[token]
            logger.debug("Token expirado")
            return None
            
        return token_data
    
    def revoke_token(self, token: str):
        """Revogar token específico"""
        if token in self.active_tokens:
            del self.active_tokens[token]
            logger.debug("Token revogado")
    
    def cleanup_expired_tokens(self):
        """Limpar tokens expirados"""
        current_time = time.time()
        expired_tokens = [
            token for token, data in self.active_tokens.items()
            if current_time - data['created'] > self.token_timeout
        ]
        
        for token in expired_tokens:
            del self.active_tokens[token]
        
        if expired_tokens:
            logger.debug(f"Tokens limpos: {len(expired_tokens)} expirados")

class ChallengeManager:
    """SRP: Gerenciamento de desafios challenge-response"""
    
    def __init__(self, auth_key: bytes):
        self.auth_key = auth_key
        self.auth_challenges = {}
    
    def generate_challenge(self, client_id: str, client_ip: str) -> dict:
        """Gerar desafio para autenticação"""
        challenge = CryptoHelper.generate_random_hex(32)
        timestamp = time.time()
        
        self.auth_challenges[challenge] = {
            'client_id': client_id,
            'client_ip': client_ip,
            'timestamp': timestamp,
            'attempts': 0
        }
        
        logger.debug(f"Desafio gerado para {client_id}")
        return {
            'challenge': challenge,
            'timestamp': timestamp
        }
    
    def validate_response(self, challenge: str, response: str, 
                         client_id: str, client_ip: str) -> bool:
        """Validar resposta ao desafio"""
        if challenge not in self.auth_challenges:
            return False
            
        challenge_data = self.auth_challenges[challenge]
        
        # Verificar dados do cliente
        if (challenge_data['client_id'] != client_id or 
            challenge_data['client_ip'] != client_ip):
            logger.warning("Dados do cliente não correspondem ao desafio")
            return False
        
        # Verificar expiração (2 minutos)
        if time.time() - challenge_data['timestamp'] > 120:
            del self.auth_challenges[challenge]
            logger.debug("Desafio expirado")
            return False
            
        # Limitar tentativas
        challenge_data['attempts'] += 1
        if challenge_data['attempts'] > 3:
            del self.auth_challenges[challenge]
            logger.warning("Muitas tentativas falhas")
            return False
        
        # Calcular resposta esperada
        expected_response = self._calculate_expected_response(challenge, client_id)
        return CryptoHelper.compare_digest(response, expected_response)
    
    def _calculate_expected_response(self, challenge: str, client_id: str) -> str:
        """Calcular resposta esperada para o desafio"""
        data = f"{challenge}:{client_id}:{int(time.time())}"
        h = uhashlib.sha256(data.encode() + self.auth_key)
        return ubinascii.hexlify(h.digest()).decode()
    
    def cleanup_expired_challenges(self):
        """Limpar desafios expirados"""
        current_time = time.time()
        expired_challenges = [
            challenge for challenge, data in self.auth_challenges.items()
            if current_time - data['timestamp'] > 120
        ]
        
        for challenge in expired_challenges:
            del self.auth_challenges[challenge]

class SecurityManager:
    """Facade: Gerenciador de segurança principal"""
    
    def __init__(self, auth_key: str, token_timeout: int = 30):
        self.crypto = AESEncryptor(auth_key)
        self.token_manager = TokenManager(token_timeout)
        self.challenge_manager = ChallengeManager(auth_key.encode() if isinstance(auth_key, str) else auth_key)
    
    def encrypt_message(self, msg: str) -> str:
        return self.crypto.encrypt(msg)
    
    def decrypt_message(self, enc_str: str) -> str:
        return self.crypto.decrypt(enc_str)
    
    def generate_token(self, client_id: str, client_ip: str) -> str:
        return self.token_manager.generate_token(client_id, client_ip)
    
    def validate_token(self, token: str, client_ip: str) -> dict:
        return self.token_manager.validate_token(token, client_ip)
    
    def generate_auth_challenge(self, client_id: str, client_ip: str) -> dict:
        return self.challenge_manager.generate_challenge(client_id, client_ip)
    
    def validate_challenge_response(self, challenge: str, response: str, 
                                  client_id: str, client_ip: str) -> bool:
        return self.challenge_manager.validate_response(challenge, response, client_id, client_ip)
    
    def cleanup_expired(self):
        """Limpar todos os recursos expirados"""
        self.token_manager.cleanup_expired_tokens()
        self.challenge_manager.cleanup_expired_challenges()

class AuthenticationManager:
    """SRP: Gerenciador de autenticação para clientes"""
    
    def __init__(self, security_manager: SecurityManager):
        self.security = security_manager
        self.authenticated_clients = {}
        self.auth_timeout = 300  # 5 minutos
        self.max_sessions_per_ip = 3
    
    def initiate_auth(self, client_ip: str, client_id: str) -> dict:
        """Iniciar processo de autenticação"""
        try:
            # Verificar sessões ativas
            if self._has_too_many_sessions(client_ip):
                return self._build_auth_response('TOO_MANY_SESSIONS', 'Número máximo de sessões')
            
            # Gerar desafio
            challenge_data = self.security.generate_auth_challenge(client_id, client_ip)
            
            return self._build_auth_response(
                'CHALLENGE_REQUIRED',
                'Responda ao desafio',
                challenge=challenge_data['challenge'],
                timestamp=challenge_data['timestamp']
            )
            
        except Exception as e:
            logger.error(f"Erro ao iniciar autenticação: {e}")
            return self._build_auth_response('AUTH_ERROR', f'Erro interno: {str(e)}')
    
    def complete_auth(self, client_ip: str, client_id: str, 
                     challenge: str, response: str) -> dict:
        """Completar autenticação challenge-response"""
        try:
            if self.security.validate_challenge_response(challenge, response, client_id, client_ip):
                # Gerar token de sessão
                session_token = self.security.generate_token(client_id, client_ip)
                
                # Registrar cliente
                self.authenticated_clients[client_ip] = {
                    'client_id': client_id,
                    'session_token': session_token,
                    'authenticated_at': time.time(),
                    'last_activity': time.time(),
                }
                
                logger.info(f"Cliente autenticado: {client_id} ({client_ip})")
                
                return self._build_auth_response(
                    'AUTHENTICATED',
                    'Autenticação bem-sucedida',
                    session_token=session_token
                )
            else:
                return self._build_auth_response('AUTH_FAILED', 'Falha na autenticação')
            
        except Exception as e:
            logger.error(f"Erro na autenticação: {e}")
            return self._build_auth_response('AUTH_ERROR', f'Erro interno: {str(e)}')
    
    def validate_client_session(self, client_ip: str, session_token: str) -> bool:
        """Validar sessão do cliente"""
        if client_ip not in self.authenticated_clients:
            return False
            
        client_data = self.authenticated_clients[client_ip]
        
        # Verificar token
        if not self.security.validate_token(session_token, client_ip):
            self._revoke_client_session(client_ip)
            return False
        
        # Verificar timeout
        if time.time() - client_data['last_activity'] > self.auth_timeout:
            self._revoke_client_session(client_ip)
            return False
        
        # Atualizar atividade
        client_data['last_activity'] = time.time()
        return True
    
    def _has_too_many_sessions(self, client_ip: str) -> bool:
        """Verificar se há muitas sessões para o IP"""
        active_sessions = [
            ip for ip, data in self.authenticated_clients.items()
            if ip == client_ip and 
            time.time() - data['last_activity'] <= self.auth_timeout
        ]
        return len(active_sessions) >= self.max_sessions_per_ip
    
    def _revoke_client_session(self, client_ip: str):
        """Revogar sessão do cliente"""
        if client_ip in self.authenticated_clients:
            client_data = self.authenticated_clients[client_ip]
            self.security.token_manager.revoke_token(client_data['session_token'])
            del self.authenticated_clients[client_ip]
            logger.info(f"Sessão revogada para {client_ip}")
    
    def _build_auth_response(self, status: str, message: str, **kwargs) -> dict:
        """Construir resposta de autenticação - DRY"""
        response = {'status': status, 'message': message}
        response.update(kwargs)
        return response
    
    def logout_client(self, client_ip: str) -> bool:
        """Logout manual do cliente"""
        if client_ip in self.authenticated_clients:
            self._revoke_client_session(client_ip)
            logger.info(f"Logout manual para {client_ip}")
            return True
        return False
    
    def cleanup_expired_sessions(self):
        """Limpar sessões expiradas"""
        current_time = time.time()
        expired_clients = [
            client_ip for client_ip, data in self.authenticated_clients.items()
            if current_time - data['last_activity'] > self.auth_timeout
        ]
        
        for client_ip in expired_clients:
            self._revoke_client_session(client_ip)
        
        # Limpar recursos de segurança
        self.security.cleanup_expired()
        
        if expired_clients:
            logger.debug(f"Sessões limpas: {len(expired_clients)} expiradas")