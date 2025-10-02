# udp_communicator.py - Refatorado para usar DeviceManager
import usocket as socket
import uasyncio as asyncio
import ujson as json
import time
from security import SecurityManager
from utils import get_logger

logger = get_logger("UDPCommunicator")

class UDPCommunicator:
    def __init__(self, device_manager):
        self.device_manager = device_manager
        self.config_mgr = device_manager.get_config_manager()
        network_config = self.config_mgr.get_network_config()
        
        self.port = network_config.get('UDP_PORT', 8888)
        self.broadcast_port = network_config.get('BROADCAST_PORT', 8889)
        self.sock = self._setup_socket()
        
        # Configurações de segurança
        self.security = SecurityManager(
            network_config.get('AUTH_KEY'), 
            network_config.get('TOKEN_TIMEOUT', 30)
        )
        
        # Estado do comunicador
        self.running = True
        self.msg_queue = asyncio.Queue()
        self.last_broadcast = 0
        self.broadcast_interval = network_config.get('DISCOVERY_INTERVAL', 30)

    def _setup_socket(self):
        """Configurar socket UDP de forma reutilizável"""
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.bind(("0.0.0.0", self.port))
        return sock

    async def start(self):
        """Iniciar comunicador UDP"""
        loop = asyncio.get_event_loop()
        loop.create_task(self._listener())
        loop.create_task(self._broadcast_discovery())
        await asyncio.sleep(0)
        logger.info(f"UDPCommunicator iniciado na porta {self.port}")

    def stop(self):
        """Parar comunicador UDP"""
        self.running = False
        try:
            self.sock.close()
        except Exception:
            pass
        logger.info("UDPCommunicator parado")

    async def _listener(self):
        """Task para escutar mensagens UDP"""
        logger.info(f"UDP Listener ativo na porta {self.port}")
        while self.running:
            try:
                data, addr = self.sock.recvfrom(1024)
                await self._process_received_message(data, addr)
            except OSError:
                await asyncio.sleep(0.05)
                continue
            except Exception as e:
                logger.error(f"Erro no listener: {e}")
                await asyncio.sleep(1)

    async def _process_received_message(self, data, addr):
        """Processar mensagem recebida"""
        try:
            raw_msg = data.decode().strip()
            msg = self.security.decrypt_message(raw_msg)
            
            if not msg:
                logger.warning(f"Mensagem inválida de {addr}")
                return
                
            await self.msg_queue.put((msg, addr))
            logger.debug(f"Mensagem recebida de {addr}: {msg[:50]}...")
            
        except Exception as e:
            logger.error(f"Erro ao processar mensagem: {e}")

    async def _broadcast_discovery(self):
        """Task para broadcast periódico de discovery"""
        logger.info("Iniciando broadcast de discovery...")
        while self.running:
            try:
                current_time = time.time()
                if current_time - self.last_broadcast > self.broadcast_interval:
                    await self._send_broadcast_message()
                    self.last_broadcast = current_time
                    
                await asyncio.sleep(5)
                
            except Exception as e:
                logger.error(f"Erro no broadcast: {e}")
                await asyncio.sleep(10)

    async def _send_broadcast_message(self):
        """Enviar mensagem de broadcast"""
        # Usar mensagem padronizada do DeviceManager
        broadcast_data = self.device_manager.get_broadcast_message()
        broadcast_msg = json.dumps(broadcast_data)
        
        await self.send_message_async(broadcast_msg, "255.255.255.255", self.broadcast_port)
        logger.debug("Broadcast de discovery enviado")

    async def send_message_async(self, message, ip="255.255.255.255", port=None):
        """Enviar mensagem de forma assíncrona"""
        try:
            target_port = port or self.port
            encrypted = self.security.encrypt_message(message)
            self.sock.sendto(encrypted.encode(), (ip, target_port))
            logger.debug(f"Enviado para {ip}:{target_port}")
        except Exception as e:
            logger.error(f"Erro ao enviar mensagem: {e}")

    def send_message(self, message, ip="255.255.255.255", port=None):
        """Enviar mensagem de forma síncrona"""
        try:
            target_port = port or self.port
            encrypted = self.security.encrypt_message(message)
            self.sock.sendto(encrypted.encode(), (ip, target_port))
            logger.debug(f"Enviado para {ip}:{target_port}")
        except Exception as e:
            logger.error(f"Erro ao enviar mensagem: {e}")