# main.py - Sistema principal refatorado
import uasyncio as asyncio
import time
import gc
import machine
from machine import Pin
from utils import get_logger
from ir_sensor import IRSensor
from udp_communicator import UDPCommunicator
from servo_control import ServoController
from wlan_manager import WlanManager
from power_manager import PowerManager
from recovery import RecoverySystem
from system_health import SystemHealth
from error_handler import ErrorHandler
from device_manager import DeviceManager
from server_communicator import ServerCommunicator
from flutter_comunicator import FlutterCommunicator

logger = get_logger("ESP32_SYSTEM")

class ESP32System:
    def __init__(self):
        # Inicializar componentes de sistema
        self.recovery = RecoverySystem()
        self.device_manager = DeviceManager()
        self.error_handler = ErrorHandler(self.recovery)
        self.health = SystemHealth()
        self.power = PowerManager()
        
        # Obter configurações do sistema via DeviceManager
        system_config = self.device_manager.get_system_config()
        
        # Variáveis de estado
        self.send_cooldown = 2
        self.last_sent = 0
        self.running = False
        
        # Configurações do sistema
        self.heartbeat_interval = system_config.get('HEARTBEAT_INTERVAL', 60)
        self.last_heartbeat = 0
        self.ap_blink_interval = system_config.get('AP_MODE_BLINK_INTERVAL', 2)
        self.last_blink = 0
        self.led_state = False

        # LED de status
        self.status_led = Pin(system_config.get('STATUS_LED_PIN', 2), Pin.OUT)
        self.status_led.off()

        # Inicializar componentes principais com tratamento de erro
        init_success = self.error_handler.wrap_sync_function(
            self._initialize_components, "System initialization"
        )()
        
        if not init_success:
            logger.error("Failed to initialize system components")
            return

        self.running = True
        logger.info("ESP32System fully initialized")

    def _initialize_components(self):
        """Inicializar todos os componentes do sistema usando DeviceManager"""
        try:
            # --- Wi-Fi ---
            self.wifi = WlanManager(self.device_manager)
            connection_result = self.wifi.connect()
            
            # Obter informações atualizadas do DeviceManager
            network_info = self.device_manager.get_network_status()
            device_info = self.device_manager.get_device_info()
            
            # Log do status de rede
            if network_info.get('ap_mode', False):
                self._log_ap_mode(device_info, network_info)
            elif network_info.get('connected', False):
                self._log_sta_mode(device_info, network_info)
            else:
                self._log_disconnected_mode(device_info)

            # --- Hardware ---
            self.sensor = IRSensor(callback=self.on_movement_async)
            self.udp = UDPCommunicator(self.device_manager)
            self.servo = ServoController()
            
            # --- Comunicação com servidor ---
            self.server = ServerCommunicator(
                self.udp, 
                self.device_manager, 
                self.device_manager.get_config_manager(),
                self.servo
            )

            # --- Comunicação com Flutter ---
            self.flutter_comms = FlutterCommunicator(
                self.udp,
                self.device_manager,
                self.server,
                self.wifi,
                self.health,
                self.servo
            )

            logger.success("Todos os componentes inicializados com sucesso")
            return True
            
        except Exception as e:
            logger.error(f"Falha na inicialização dos componentes: {e}")
            self.recovery.record_failure(f"Init: {str(e)}")
            return False

    def _log_ap_mode(self, device_info, network_info):
        """Log para modo AP"""
        logger.warning("=== SISTEMA EM MODO ACCESS POINT ===")
        logger.warning(f"Dispositivo: {device_info['device_name']}")
        logger.warning(f"ID: {device_info['device_id']}")
        logger.warning(f"IP: {network_info.get('ip', 'N/A')}")
        logger.warning("Aguardando configuração do servidor...")
        logger.warning("=====================================")

    def _log_sta_mode(self, device_info, network_info):
        """Log para modo STA conectado"""
        logger.success("=== SISTEMA CONECTADO AO WI-FI ===")
        logger.success(f"Dispositivo: {device_info['device_name']}")
        logger.success(f"ID: {device_info['device_id']}")
        logger.success(f"IP: {network_info.get('ip', 'N/A')}")
        logger.success("Procurando servidor...")
        logger.success("=================================")

    def _log_disconnected_mode(self, device_info):
        """Log para modo desconectado"""
        logger.error("=== SISTEMA DESCONECTADO ===")
        logger.error(f"Dispositivo: {device_info['device_name']}")
        logger.error("Verifique as configurações de WiFi")

    async def on_movement_async(self):
        """Callback assíncrono do sensor IR"""
        await self.error_handler.safe_execute(
            self._on_movement_impl(), "Movement detection"
        )

    async def _on_movement_impl(self):
        """Implementação real do callback de movimento"""
        now = time.time()
        if now - self.last_sent < self.send_cooldown:
            return
            
        self.last_sent = now
        
        # Atualizar no Flutter communicator
        self.flutter_comms.update_movement_detected()
        
        # Comportamento original (notificar servidor)
        if self.server.is_connected():
            try:
                await self.server.send_movement_detected()
                logger.info("Movimento detectado - notificação enviada ao servidor")
            except Exception as e:
                logger.warning(f"Falha ao enviar para servidor: {e}")
        else:
            logger.info("Movimento detectado - servidor desconectado")

    async def handle_udp_messages(self):
        """Task principal para processar mensagens recebidas"""
        logger.info("UDP message handler started")
        while self.running:
            try:
                msg, addr = await self.udp.msg_queue.get()
                if msg and addr:
                    await self.process_message(msg, addr)
            except Exception as e:
                logger.error(f"Error in UDP handler: {e}")
                await asyncio.sleep(0.1)

    async def process_message(self, msg, addr):
        """Processar mensagens UDP com tratamento de erro"""
        await self.error_handler.safe_execute(
            self._process_message_impl(msg, addr), "Message processing"
        )

    async def _process_message_impl(self, msg, addr):
        """Implementação real do processamento de mensagens"""
        # Primeiro tenta processar como mensagem do Flutter
        flutter_handled = await self.flutter_comms.handle_message(msg, addr)
        
        # Se não for mensagem do Flutter, delega para o servidor
        if not flutter_handled and self.server:
            await self.server.handle_message(msg, addr)

    async def server_connection_task(self):
        """Task para gerenciar conexão com servidor"""
        logger.info("Server connection manager started")
        
        await self.server.start()
        
        while self.running:
            try:
                await self._update_led_status()
                await asyncio.sleep(0.5)
                
            except Exception as e:
                logger.error(f"Server connection task error: {e}")
                await asyncio.sleep(5)

    async def _update_led_status(self):
        """Atualizar status do LED baseado no estado do sistema"""
        network_status = self.device_manager.get_network_status()
        ap_mode = network_status.get('ap_mode', False)
        
        if self.server.is_connected():
            self.status_led.on()
        elif ap_mode:
            current_time = time.time()
            if current_time - self.last_blink > self.ap_blink_interval:
                self.led_state = not self.led_state
                self.status_led.value(self.led_state)
                self.last_blink = current_time
        else:
            self.status_led.off()

    async def health_monitor_task(self):
        """Task para monitoramento contínuo de saúde"""
        logger.info("Health monitor started")
        while self.running:
            try:
                await self._perform_health_checks()
                
                # Limpar sessões expiradas a cada minuto
                self.flutter_comms.cleanup_expired_sessions()
                
                await asyncio.sleep(10)
                
            except Exception as e:
                logger.error(f"Health monitor error: {e}")
                await asyncio.sleep(5)

    async def _perform_health_checks(self):
        """Executar verificações de saúde do sistema"""
        if not self.health.check_health():
            logger.error("System health check failed")
            self.recovery.record_failure("Health monitor")
        
        current_time = time.time()
        if (self.server.is_connected() and 
            current_time - self.last_heartbeat > self.heartbeat_interval):
            await self.server.send_system_status()
            self.last_heartbeat = current_time
            logger.debug("Heartbeat enviado para o servidor")
        
        self.device_manager.get_system_info()

    async def run_async(self):
        """Loop principal assíncrono"""
        logger.info("ESP32 system running...")
        
        self.sensor.start()
        await self.udp.start()
        
        tasks = [
            asyncio.create_task(self.handle_udp_messages()),
            asyncio.create_task(self.health_monitor_task()),
            asyncio.create_task(self.server_connection_task()),
            asyncio.create_task(self.server.maintenance_task())
        ]
        
        while self.running:
            try:
                await asyncio.sleep(1)
                await self._perform_maintenance()
                
            except Exception as e:
                logger.error(f"Main loop error: {e}")
                await asyncio.sleep(1)

        for task in tasks:
            task.cancel()

    async def _perform_maintenance(self):
        """Executar manutenção periódica do sistema"""
        if gc.mem_free() < 20000:
            gc.collect()
            logger.debug("Garbage collection performed")

    def stop(self):
        """Parar o sistema gracefulmente"""
        self.running = False
        self.sensor.stop()
        self.servo.reset()
        self.udp.stop()
        self.status_led.off()
        logger.info("System stopped gracefully")

    def get_system_status(self):
        """Obter status completo do sistema usando DeviceManager"""
        system_info = self.device_manager.get_system_info()
        server_info = self.server.get_server_info()
        device_info = self.device_manager.get_device_info()
        network_info = self.device_manager.get_network_status()
        
        return {
            'device': device_info,
            'system': system_info,
            'server': server_info,
            'network': network_info,
            'running': self.running,
            'timestamp': time.time()
        }

    def update_system_config(self, config_updates):
        """Atualizar configurações do sistema em tempo real via DeviceManager"""
        try:
            success = True
            
            device_updates = self._extract_config_keys(config_updates, 
                ['DEVICE_NAME', 'DEVICE_LOCATION', 'DEVICE_TYPE', 'DEVICE_ID'])
            wifi_updates = self._extract_config_keys(config_updates,
                ['SSID', 'PASSWORD', 'MAX_RETRIES', 'RETRY_DELAY'])
            network_updates = self._extract_config_keys(config_updates,
                ['SERVER_IP', 'SERVER_PORT', 'AUTO_DISCOVER_SERVER'])
            system_updates = self._extract_config_keys(config_updates,
                ['STATUS_LED_PIN', 'HEARTBEAT_INTERVAL', 'AP_MODE_BLINK_INTERVAL'])
            
            success &= self._apply_config_updates(device_updates, wifi_updates, 
                                                network_updates, system_updates)
            
            return success
                
        except Exception as e:
            logger.error(f"Erro ao atualizar configurações do sistema: {e}")
            return False

    def _extract_config_keys(self, config_dict, keys):
        """Extrair chaves específicas do dicionário de configuração"""
        return {k: v for k, v in config_dict.items() if k in keys}

    def _apply_config_updates(self, device_updates, wifi_updates, network_updates, system_updates):
        """Aplicar atualizações de configuração"""
        success = True
        
        if device_updates:
            success &= self.device_manager.update_device_config(device_updates)
            
        if wifi_updates:
            success &= self.device_manager.update_wifi_config(wifi_updates)
            if any(key in wifi_updates for key in ['SSID', 'PASSWORD']):
                logger.info("Configurações WiFi alteradas - reconectando...")
                asyncio.create_task(self._reconnect_wifi())
            
        if network_updates:
            success &= self.device_manager.update_network_config(network_updates)
            network_config = self.device_manager.get_network_config()
            self.server.server_ip = network_config.get('SERVER_IP')
            self.server.auto_discover = network_config.get('AUTO_DISCOVER_SERVER', True)
        
        if system_updates:
            success &= self.device_manager.update_system_config(system_updates)
            self._update_local_system_config(system_updates)
        
        if success:
            logger.info("Configurações do sistema atualizadas com sucesso")
        else:
            logger.error("Falha ao atualizar algumas configurações")
            
        return success

    def _update_local_system_config(self, system_updates):
        """Atualizar configurações locais do sistema"""
        if 'HEARTBEAT_INTERVAL' in system_updates:
            self.heartbeat_interval = system_updates['HEARTBEAT_INTERVAL']
        if 'AP_MODE_BLINK_INTERVAL' in system_updates:
            self.ap_blink_interval = system_updates['AP_MODE_BLINK_INTERVAL']

    async def _reconnect_wifi(self):
        """Reconectar ao WiFi com novas configurações"""
        try:
            logger.info("Reconectando WiFi com novas configurações...")
            await asyncio.sleep(2)
            
            self.wifi = WlanManager(self.device_manager)
            self.wifi.connect()
            
            logger.success("Reconexão WiFi concluída")
                
        except Exception as e:
            logger.error(f"Erro na reconexão WiFi: {e}")

    def get_detailed_status(self):
        """Obter status detalhado do sistema para debug"""
        complete_status = self.device_manager.get_complete_status()
        server_info = self.server.get_server_info()
        
        return {
            **complete_status,
            'server': server_info,
            'tasks': {
                'running': self.running,
                'last_heartbeat': self.last_heartbeat,
                'last_movement': self.last_sent
            }
        }

    def soft_reset(self):
        """Reinicialização suave do sistema"""
        logger.info("Iniciando soft reset do sistema...")
        self.stop()
        asyncio.create_task(self._perform_soft_reset())

    async def _perform_soft_reset(self):
        """Executar reinicialização suave"""
        await asyncio.sleep(2)
        logger.info("Reiniciando sistema...")
        machine.reset()

if __name__ == "__main__":
    system = ESP32System()
    
    if system.running:
        try:
            status = system.get_system_status()
            logger.info(f"Sistema inicializado: {status['device']['device_name']}")
            logger.info(f"IP: {status['network'].get('ip', 'N/A')}")
            logger.info(f"Modo: {'AP' if status['network'].get('ap_mode') else 'STA'}")
            
            asyncio.run(system.run_async())
            
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received")
        except Exception as e:
            logger.error(f"Fatal error: {e}")
        finally:
            system.stop()
    else:
        logger.error("System failed to initialize. Stopping.")
        logger.info("Entering recovery mode...")