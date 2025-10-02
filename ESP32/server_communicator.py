# server_communicator.py - Comunicação com servidor central (refatorado)
import uasyncio as asyncio
import ujson
import time
import machine
from utils import get_logger
from message_handler import MessageHandler

logger = get_logger("ServerCommunicator")

class ServerCommunicator:
    def __init__(self, udp_communicator, device_manager, config_manager, servo_controller=None):
        self.udp = udp_communicator
        self.device_manager = device_manager
        self.config_mgr = config_manager
        self.network_config = self.config_mgr.get_network_config()
        
        self.server_ip = self.network_config.get('SERVER_IP')
        self.server_port = self.network_config.get('SERVER_PORT', 8888)
        self.auto_discover = self.network_config.get('AUTO_DISCOVER_SERVER', True)
        
        self.connected = False
        self.connection_time = 0
        self.last_heartbeat = 0
        self.heartbeat_interval = 60
        
        # Usar MessageHandler reutilizável
        self.message_handler = MessageHandler(device_manager, udp_communicator, servo_controller)
        
        # Registrar handlers específicos do servidor
        self.message_handler.register_handler('SERVER_ONLINE', self._handle_server_online)
        self.message_handler.register_handler('HEARTBEAT_REQUEST', self._handle_heartbeat_request)
        self.message_handler.register_handler('SYSTEM_COMMAND', self._handle_system_command)

    async def start(self):
        """Iniciar comunicação com servidor"""
        logger.info("Iniciando comunicação com servidor...")
        
        if self.server_ip and not self.auto_discover:
            await self.connect_to_server(self.server_ip)
        else:
            await self.discover_server()
    
    async def connect_to_server(self, server_ip):
        """Conectar a um servidor específico"""
        try:
            device_info = self.device_manager.get_device_info()
            connection_msg = f"DEVICE_CONNECT:{ujson.dumps(device_info)}"
            
            await self.udp.send_message_async(connection_msg, ip=server_ip)
            logger.info(f"Tentando conectar ao servidor: {server_ip}")
            
            await asyncio.sleep(2)
            
        except Exception as e:
            logger.error(f"Erro ao conectar com servidor {server_ip}: {e}")
    
    async def discover_server(self):
        """Descobrir servidor automaticamente na rede"""
        logger.info("Procurando servidor na rede...")
        
        network_prefix = self._get_network_prefix()
        if not network_prefix:
            return
        
        # Tentar IPs comuns de servidor
        server_ips = [
            f"{network_prefix}.1",    # Gateway
            f"{network_prefix}.100",  # IP comum para servidores
            f"{network_prefix}.50",   # Outro IP comum
            f"{network_prefix}.200",  # Possível servidor
            "255.255.255.255"         # Broadcast
        ]
        
        # Adicionar IP específico se configurado
        if self.server_ip:
            server_ips.insert(0, self.server_ip)
        
        for server_ip in server_ips:
            await self.connect_to_server(server_ip)
            await asyncio.sleep(0.5)
    
    async def handle_message(self, msg, addr):
        """Delegar processamento para MessageHandler"""
        await self.message_handler.handle_message(msg, addr)
    
    async def _handle_server_online(self, msg, addr):
        """Servidor respondeu que está online"""
        server_ip = addr[0] if isinstance(addr, tuple) else addr
        
        if not self.connected or server_ip != self.server_ip:
            self.server_ip = server_ip
            self.connected = True
            self.connection_time = time.time()
            
            device_info = self.device_manager.get_device_info()
            await self.udp.send_message_async(
                f"DEVICE_REGISTER:{ujson.dumps(device_info)}", 
                ip=self.server_ip
            )
            
            logger.success(f"Conectado ao servidor: {self.server_ip}")
            await self.send_system_status()
    
    async def _handle_heartbeat_request(self, msg, addr):
        """Responder a heartbeat do servidor"""
        await self.send_heartbeat()
    
    async def _handle_system_command(self, msg, addr):
        """Executar comandos de sistema"""
        try:
            parts = msg.split(":")
            command = parts[1] if len(parts) > 1 else ""
            
            if command == "RESTART":
                logger.info("Reiniciando por comando do servidor...")
                await self.udp.send_message_async("RESTART_ACK", ip=addr[0])
                await asyncio.sleep(2)
                machine.reset()
                
            elif command == "STATUS":
                await self.send_system_status(addr[0])
                
            else:
                # Delegar para o handler padrão
                await self.message_handler._handle_system_command(msg, addr)
                
        except Exception as e:
            logger.error(f"Erro ao executar comando: {e}")
    
    async def send_heartbeat(self):
        """Enviar heartbeat para o servidor"""
        if self.connected:
            try:
                system_status = self._get_system_status()
                heartbeat_msg = f"HEARTBEAT:{ujson.dumps(system_status)}"
                await self.udp.send_message_async(heartbeat_msg, ip=self.server_ip)
                self.last_heartbeat = time.time()
            except Exception as e:
                logger.error(f"Erro ao enviar heartbeat: {e}")
                self.connected = False
    
    async def send_system_status(self, target_ip=None):
        """Enviar status completo do sistema"""
        ip = target_ip or self.server_ip
        if self.connected or target_ip:
            system_status = self._get_system_status()
            status_msg = f"SYSTEM_STATUS:{ujson.dumps(system_status)}"
            await self.udp.send_message_async(status_msg, ip=ip)
    
    async def send_movement_detected(self):
        """Enviar notificação de movimento detectado"""
        if self.connected:
            device_id = self.device_manager.get_device_id()
            movement_msg = f"MOVEMENT_DETECTED:{device_id}"
            await self.udp.send_message_async(movement_msg, ip=self.server_ip)
    
    def _get_system_status(self):
        """Obter status do sistema para relatórios"""
        system_info = self.device_manager.get_system_info()
        device_info = self.device_manager.get_device_info()
        
        return {
            'device': device_info,
            'system': system_info,
            'server_connected': self.connected,
            'server_ip': self.server_ip,
            'uptime': system_info['uptime'],
            'memory_free_percent': (system_info['memory_free'] / 
                                  (system_info['memory_free'] + system_info['memory_allocated'])) * 100,
            'connection_duration': time.time() - self.connection_time if self.connected else 0
        }
    
    def _get_network_prefix(self):
        """Obter prefixo da rede"""
        network_status = self.device_manager.get_network_status()
        ip = network_status.get('ip')
        ap_mode = network_status.get('ap_mode', False)
        
        if ap_mode:
            return "192.168.4"
        elif ip:
            parts = ip.split(".")
            if len(parts) == 4:
                return ".".join(parts[:3])
        
        return "192.168.1"
    
    async def maintenance_task(self):
        """Task de manutenção da conexão com servidor"""
        while True:
            try:
                # Verificar se precisa enviar heartbeat
                current_time = time.time()
                if (self.connected and 
                    current_time - self.last_heartbeat > self.heartbeat_interval):
                    await self.send_heartbeat()
                
                # Verificar se precisa reconectar
                if not self.connected and self.auto_discover:
                    await self.discover_server()
                
                await asyncio.sleep(10)
                
            except Exception as e:
                logger.error(f"Erro na task de manutenção: {e}")
                await asyncio.sleep(10)
    
    def is_connected(self):
        return self.connected
    
    def get_server_info(self):
        return {
            'connected': self.connected,
            'server_ip': self.server_ip,
            'connection_duration': time.time() - self.connection_time if self.connected else 0
        }