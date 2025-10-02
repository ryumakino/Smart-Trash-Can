# security.py - Sistema de autenticação e segurança atualizado
import ujson as json
import utime as time
import ubinascii
import ucryptolib
import uhashlib
import urandom
from utils import get_logger

logger = get_logger("Security")

class SecurityManager:
    def __init__(self, auth_key: str, token_timeout: int = 30):
        if isinstance(auth_key, str):
            auth_key = auth_key.encode()
        self.auth_key = uhashlib.sha256(auth_key).digest()  # 32 bytes
        self.token_timeout = token_timeout
        self.active_tokens = {}
        self.session_keys = {}
        self.auth_challenges = {}

    # -------- AES Helpers --------
    def _pad(self, s: bytes) -> bytes:
        pad_len = 16 - (len(s) % 16)
        return s + bytes([pad_len]) * pad_len

    def _unpad(self, s: bytes) -> bytes:
        return s[:-s[-1]]

    # -------- Encrypt / Decrypt --------
    def encrypt_message(self, msg: str) -> str:
        """Criptografar mensagem com AES-CBC + HMAC"""
        try:
            timestamp = int(time.time())
            payload = json.dumps({"message": msg, "timestamp": timestamp}).encode()

            # Gerar IV aleatório
            iv = urandom.getrandbits(128).to_bytes(16, 'big')
            cipher = ucryptolib.aes(self.auth_key, 2, iv)  # Mode 2 = CBC
            encrypted = cipher.encrypt(self._pad(payload))

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
            return msg  # Fallback para texto simples

    def decrypt_message(self, enc_str: str):
        """Descriptografar mensagem com verificação de integridade"""
        try:
            packet = json.loads(enc_str)
            iv = ubinascii.a2b_base64(packet["iv"])
            encrypted = ubinascii.a2b_base64(packet["data"])
            signature = packet["signature"]

            # Verificar HMAC
            h = uhashlib.sha256(iv + encrypted)
            expected_signature = ubinascii.hexlify(h.digest()).decode()
            
            if not self._compare_digest(signature, expected_signature):
                logger.warning("HMAC verification failed")
                return None

            cipher = ucryptolib.aes(self.auth_key, 2, iv)  # CBC
            decrypted = self._unpad(cipher.decrypt(encrypted))
            payload = json.loads(decrypted.decode())

            # Verificar timestamp
            if abs(int(time.time()) - int(payload["timestamp"])) > self.token_timeout:
                logger.warning("Message timestamp expired")
                return None

            return payload["message"]
        except Exception as e:
            logger.error(f"Erro ao descriptografar: {e}")
            return None

    def _compare_digest(self, a: str, b: str) -> bool:
        """Comparação segura de hashes (timing-attack resistant)"""
        if len(a) != len(b):
            return False
        result = 0
        for x, y in zip(a, b):
            result |= ord(x) ^ ord(y)
        return result == 0

    # -------- Token Management --------
    def generate_token(self, client_id: str, client_ip: str) -> str:
        """Gerar token de autenticação seguro"""
        timestamp = str(int(time.time()))
        random_val = str(urandom.getrandbits(64))
        
        # Criar payload do token
        token_data = f"{client_id}:{client_ip}:{timestamp}:{random_val}"
        token_hmac = self._calculate_hmac(token_data)
        
        token = ubinascii.hexlify(
            uhashlib.sha256(token_data.encode() + self.auth_key).digest()
        ).decode()
        
        # Armazenar token
        self.active_tokens[token] = {
            'client_id': client_id,
            'client_ip': client_ip,
            'timestamp': int(timestamp),
            'created': time.time(),
            'hmac': token_hmac
        }
        
        logger.debug(f"Token gerado para {client_id} ({client_ip})")
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

    def _calculate_hmac(self, data: str) -> str:
        """Calcular HMAC para dados"""
        h = uhashlib.sha256(data.encode() + self.auth_key)
        return ubinascii.hexlify(h.digest()).decode()

    # -------- Challenge-Response Authentication --------
    def generate_auth_challenge(self, client_id: str, client_ip: str) -> dict:
        """Gerar desafio para autenticação challenge-response"""
        challenge = ubinascii.hexlify(urandom.getrandbits(128)).decode()
        timestamp = time.time()
        
        # Armazenar desafio
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

    def validate_challenge_response(self, challenge: str, response: str, 
                                  client_id: str, client_ip: str) -> str:
        """Validar resposta ao desafio de autenticação"""
        if challenge not in self.auth_challenges:
            return None
            
        challenge_data = self.auth_challenges[challenge]
        
        # Verificar dados do cliente
        if (challenge_data['client_id'] != client_id or 
            challenge_data['client_ip'] != client_ip):
            logger.warning("Dados do cliente não correspondem ao desafio")
            return None
        
        # Verificar expiração (2 minutos para desafios)
        if time.time() - challenge_data['timestamp'] > 120:
            del self.auth_challenges[challenge]
            logger.debug("Desafio expirado")
            return None
            
        # Limitar tentativas
        challenge_data['attempts'] += 1
        if challenge_data['attempts'] > 3:
            del self.auth_challenges[challenge]
            logger.warning("Muitas tentativas de autenticação falhas")
            return None
        
        # Calcular resposta esperada
        expected_response = self._calculate_challenge_response(challenge, client_id)
        
        if self._compare_digest(response, expected_response):
            # Autenticação bem-sucedida - gerar token de sessão
            session_token = self.generate_token(client_id, client_ip)
            del self.auth_challenges[challenge]
            logger.info(f"Autenticação bem-sucedida para {client_id}")
            return session_token
            
        logger.warning("Resposta ao desafio incorreta")
        return None

    def _calculate_challenge_response(self, challenge: str, client_id: str) -> str:
        """Calcular resposta esperada para o desafio"""
        data = f"{challenge}:{client_id}:{int(time.time())}"
        h = uhashlib.sha256(data.encode() + self.auth_key)
        return ubinascii.hexlify(h.digest()).decode()

    # -------- Session Management --------
    def generate_session_key(self, client_id: str, client_ip: str) -> str:
        """Gerar chave de sessão segura"""
        session_data = f"{client_id}:{client_ip}:{int(time.time())}:{urandom.getrandbits(128)}"
        session_key = ubinascii.hexlify(
            uhashlib.sha256(session_data.encode() + self.auth_key).digest()
        ).decode()
        
        self.session_keys[session_key] = {
            'client_id': client_id,
            'client_ip': client_ip,
            'created': time.time(),
            'last_used': time.time()
        }
        
        logger.debug(f"Chave de sessão gerada para {client_id}")
        return session_key

    def validate_session_key(self, session_key: str, client_ip: str) -> dict:
        """Validar chave de sessão"""
        if session_key not in self.session_keys:
            return None
            
        session_data = self.session_keys[session_key]
        
        # Verificar IP
        if session_data['client_ip'] != client_ip:
            logger.warning(f"Session IP mismatch: {session_data['client_ip']} != {client_ip}")
            return None
        
        # Atualizar último uso
        session_data['last_used'] = time.time()
        
        # Sessões expiram em 1 hora
        if time.time() - session_data['created'] > 3600:
            del self.session_keys[session_key]
            logger.debug("Sessão expirada")
            return None
            
        return session_data

    def revoke_session(self, session_key: str):
        """Revogar sessão específica"""
        if session_key in self.session_keys:
            del self.session_keys[session_key]
            logger.debug("Sessão revogada")

    # -------- Cleanup --------
    def cleanup_expired_tokens(self):
        """Limpar tokens e sessões expiradas"""
        current_time = time.time()
        cleaned = 0
        
        # Limpar tokens expirados
        expired_tokens = [
            token for token, data in self.active_tokens.items()
            if current_time - data['created'] > self.token_timeout
        ]
        for token in expired_tokens:
            del self.active_tokens[token]
            cleaned += 1
        
        # Limpar sessões expiradas
        expired_sessions = [
            key for key, data in self.session_keys.items()
            if current_time - data['created'] > 3600
        ]
        for session_key in expired_sessions:
            del self.session_keys[session_key]
            cleaned += 1
            
        # Limpar desafios expirados
        expired_challenges = [
            challenge for challenge, data in self.auth_challenges.items()
            if current_time - data['timestamp'] > 120
        ]
        for challenge in expired_challenges:
            del self.auth_challenges[challenge]
            cleaned += 1
            
        if cleaned > 0:
            logger.debug(f"Limpeza de segurança: {cleaned} itens expirados removidos")

class AuthenticationManager:
    """Gerenciador de autenticação para clientes"""
    
    def __init__(self, security_manager: SecurityManager):
        self.security = security_manager
        self.authenticated_clients = {}
        self.auth_timeout = 300  # 5 minutos de inatividade
        self.max_sessions_per_ip = 3

    def initiate_auth(self, client_ip: str, client_id: str) -> dict:
        """Iniciar processo de autenticação"""
        try:
            # Verificar se já existe sessão ativa
            active_sessions = self._get_active_sessions_for_ip(client_ip)
            if len(active_sessions) >= self.max_sessions_per_ip:
                return {
                    'status': 'TOO_MANY_SESSIONS',
                    'message': 'Número máximo de sessões atingido'
                }
            
            # Gerar desafio
            challenge_data = self.security.generate_auth_challenge(client_id, client_ip)
            
            return {
                'status': 'CHALLENGE_REQUIRED',
                'challenge': challenge_data['challenge'],
                'timestamp': challenge_data['timestamp'],
                'message': 'Responda ao desafio para autenticar'
            }
            
        except Exception as e:
            logger.error(f"Erro ao iniciar autenticação: {e}")
            return {
                'status': 'AUTH_ERROR',
                'message': f'Erro interno: {str(e)}'
            }

    def complete_auth(self, client_ip: str, client_id: str, 
                     challenge: str, response: str) -> dict:
        """Completar autenticação com challenge-response"""
        try:
            session_token = self.security.validate_challenge_response(
                challenge, response, client_id, client_ip
            )
            
            if session_token:
                # Gerar chave de sessão
                session_key = self.security.generate_session_key(client_id, client_ip)
                
                # Registrar cliente autenticado
                self.authenticated_clients[client_ip] = {
                    'client_id': client_id,
                    'session_key': session_key,
                    'session_token': session_token,
                    'authenticated_at': time.time(),
                    'last_activity': time.time(),
                    'challenge_used': challenge
                }
                
                logger.info(f"Cliente autenticado: {client_id} ({client_ip})")
                
                return {
                    'status': 'AUTHENTICATED',
                    'session_key': session_key,
                    'session_token': session_token,
                    'message': 'Autenticação bem-sucedida'
                }
            else:
                return {
                    'status': 'AUTH_FAILED',
                    'message': 'Falha na autenticação'
                }
            
        except Exception as e:
            logger.error(f"Erro na autenticação: {e}")
            return {
                'status': 'AUTH_ERROR',
                'message': f'Erro interno: {str(e)}'
            }

    def validate_client_session(self, client_ip: str, session_key: str) -> bool:
        """Validar sessão do cliente"""
        if client_ip not in self.authenticated_clients:
            return False
            
        client_data = self.authenticated_clients[client_ip]
        
        # Verificar chave de sessão
        session_valid = self.security.validate_session_key(session_key, client_ip)
        if not session_valid:
            self._revoke_client_session(client_ip)
            return False
        
        # Verificar token de sessão
        token_valid = self.security.validate_token(
            client_data['session_token'], client_ip
        )
        if not token_valid:
            self._revoke_client_session(client_ip)
            return False
        
        # Verificar timeout de inatividade
        if time.time() - client_data['last_activity'] > self.auth_timeout:
            self._revoke_client_session(client_ip)
            return False
        
        # Atualizar última atividade
        client_data['last_activity'] = time.time()
        
        return True

    def _revoke_client_session(self, client_ip: str):
        """Revogar sessão do cliente"""
        if client_ip in self.authenticated_clients:
            client_data = self.authenticated_clients[client_ip]
            
            # Revogar chave e token de sessão
            if 'session_key' in client_data:
                self.security.revoke_session(client_data['session_key'])
            if 'session_token' in client_data:
                if client_data['session_token'] in self.security.active_tokens:
                    del self.security.active_tokens[client_data['session_token']]
            
            del self.authenticated_clients[client_ip]
            logger.info(f"Sessão revogada para {client_ip}")

    def _get_active_sessions_for_ip(self, client_ip: str) -> list:
        """Obter sessões ativas para um IP"""
        return [
            ip for ip, data in self.authenticated_clients.items()
            if ip == client_ip and 
            time.time() - data['last_activity'] <= self.auth_timeout
        ]

    def get_client_info(self, client_ip: str) -> dict:
        """Obter informações do cliente autenticado"""
        if client_ip in self.authenticated_clients:
            data = self.authenticated_clients[client_ip].copy()
            # Remover informações sensíveis
            data.pop('session_token', None)
            data.pop('challenge_used', None)
            return data
        return None

    def cleanup_expired_sessions(self):
        """Limpar sessões expiradas"""
        current_time = time.time()
        expired_clients = []
        
        for client_ip, data in self.authenticated_clients.items():
            if current_time - data['last_activity'] > self.auth_timeout:
                expired_clients.append(client_ip)
        
        for client_ip in expired_clients:
            self._revoke_client_session(client_ip)
        
        # Limpar tokens expirados no security manager
        self.security.cleanup_expired_tokens()
        
        if expired_clients:
            logger.debug(f"Limpeza: {len(expired_clients)} sessões expiradas")

    def logout_client(self, client_ip: str) -> bool:
        """Logout manual do cliente"""
        if client_ip in self.authenticated_clients:
            self._revoke_client_session(client_ip)
            logger.info(f"Logout manual para {client_ip}")
            return True
        return False