# main.py
import uasyncio as asyncio
import time
import gc
import machine
from utils import get_logger
from device_manager import DeviceManager
from hardware_manager import HardwareManager
from communication_manager import CommunicationManager
from wlan_manager import WlanManager
from system_health import SystemHealth
from error_handler import ErrorHandler
from recovery import RecoverySystem
from power_manager import PowerManager

logger = get_logger("ESP32System")

class ESP32System:
    """Sistema principal refatorado - Coordenação Central"""
    
    def __init__(self):
        # Sistema de recuperação e erro
        self.recovery = RecoverySystem()
        self.error_handler = ErrorHandler(self.recovery)
        
        # Gerenciadores principais
        self.device_manager = DeviceManager()
        self.hardware_manager = HardwareManager(self.device_manager.get_config_manager())
        self.wifi_manager = WlanManager(self.device_manager)
        self.system_health = SystemHealth()
        self.power_manager = PowerManager()
        
        # Comunicação (depende dos outros gerenciadores)
        self.communication_manager = CommunicationManager(
            self.device_manager, 
            self.hardware_manager
        )
        
        # Estado do sistema
        self.running = False
        self.startup_time = time.time()
        self.movement_cooldown = 2
        self.last_movement_time = 0
        
        # Inicializar sistema
        self._initialize_system()
    
    def _initialize_system(self):
        """Inicializar sistema completo"""
        try:
            # 1. Conectar rede
            logger.info("Iniciando conexão de rede...")
            connection_result = self.wifi_manager.connect()
            self.device_manager.update_network_info(connection_result)
            
            # 2. Log do status
            self._log_system_status()
            
            # 3. Configurar sensor IR
            self.hardware_manager.ir_sensor.start(callback=self.on_movement_detected)
            
            self.running = True
            logger.success("Sistema inicializado com sucesso")
            
        except Exception as e:
            logger.error(f"Falha na inicialização do sistema: {e}")
            self.recovery.record_failure(f"System init: {str(e)}")
    
    def _log_system_status(self):
        """Log do status do sistema"""
        device_info = self.device_manager.get_device_info()
        network_status = self.device_manager.get_network_status()
        
        logger.info("=== STATUS DO SISTEMA ===")
        logger.info(f"Dispositivo: {device_info['device_name']}")
        logger.info(f"ID: {device_info['device_id']}")
        logger.info(f"IP: {network_status.get('ip', 'N/A')}")
        
        if network_status.get('ap_mode', False):
            logger.warning("Modo: ACCESS POINT")
        elif network_status.get('connected', False):
            logger.success("Modo: CONECTADO AO WI-FI")
        else:
            logger.error("Modo: DESCONECTADO")
        
        logger.info("==========================")
    
    async def on_movement_detected(self):
        """Callback unificado para detecção de movimento"""
        current_time = time.time()
        
        # Cooldown
        if current_time - self.last_movement_time < self.movement_cooldown:
            return
        
        self.last_movement_time = current_time
        
        # Atualizar Flutter communicator
        self.communication_manager.flutter_communicator.update_movement_detected()
        
        # Notificar servidor se conectado
        if self.communication_manager.server_communicator.is_connected():
            await self.error_handler.safe_execute(
                self.communication_manager.server_communicator.send_movement_detected(),
                "Movement notification"
            )
            logger.info("Movimento detectado - notificação enviada ao servidor")
        else:
            logger.info("Movimento detectado - servidor desconectado")
    
    async def run_async(self):
        """Loop principal do sistema"""
        logger.info("Iniciando loop principal do sistema...")
        
        # Iniciar serviços
        await self.communication_manager.start_communication()
        
        # Criar tasks principais
        tasks = [
            asyncio.create_task(self._udp_message_handler()),
            asyncio.create_task(self._health_monitor_task()),
            asyncio.create_task(self._server_maintenance_task()),
            asyncio.create_task(self._system_maintenance_task()),
            asyncio.create_task(self._status_led_task())
        ]
        
        # Loop principal
        while self.running:
            try:
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.error(f"Erro no loop principal: {e}")
                await asyncio.sleep(5)
        
        # Cleanup
        for task in tasks:
            task.cancel()
        
        self.stop()
    
    async def _udp_message_handler(self):
        """Task para processar mensagens UDP"""
        logger.info("UDP message handler iniciado")
        while self.running:
            try:
                if self.communication_manager.udp_communicator:
                    msg, addr = await self.communication_manager.udp_communicator.msg_queue.get()
                    if msg and addr:
                        await self.communication_manager.handle_incoming_message(msg, addr)
            except Exception as e:
                logger.error(f"Erro no handler UDP: {e}")
                await asyncio.sleep(0.1)
    
    async def _health_monitor_task(self):
        """Task de monitoramento de saúde"""
        logger.info("Health monitor iniciado")
        while self.running:
            try:
                # Verificar saúde do sistema
                if not self.system_health.check_health():
                    self.recovery.record_failure("Health check failed")
                
                # Limpar sessões expiradas
                self.communication_manager.flutter_communicator.cleanup_expired_sessions()
                
                # Heartbeat para servidor
                if self.communication_manager.server_communicator.is_connected():
                    current_time = time.time()
                    heartbeat_interval = self.device_manager.get_system_config().get('HEARTBEAT_INTERVAL', 60)
                    
                    if hasattr(self, 'last_heartbeat'):
                        if current_time - self.last_heartbeat > heartbeat_interval:
                            await self.communication_manager.server_communicator.send_heartbeat()
                            self.last_heartbeat = current_time
                    else:
                        self.last_heartbeat = current_time
                
                await asyncio.sleep(10)
                
            except Exception as e:
                logger.error(f"Erro no monitor de saúde: {e}")
                await asyncio.sleep(10)
    
    async def _server_maintenance_task(self):
        """Task de manutenção do servidor"""
        logger.info("Server maintenance task iniciada")
        if self.communication_manager.server_communicator:
            await self.communication_manager.server_communicator.maintenance_task()
    
    async def _system_maintenance_task(self):
        """Task de manutenção do sistema"""
        logger.info("System maintenance task iniciada")
        while self.running:
            try:
                # Coleta de lixo se necessário
                if gc.mem_free() < 20000:
                    gc.collect()
                    logger.debug("Coleta de lixo realizada")
                
                await asyncio.sleep(30)
                
            except Exception as e:
                logger.error(f"Erro na manutenção do sistema: {e}")
                await asyncio.sleep(30)
    
    async def _status_led_task(self):
        """Task para controlar LED de status"""
        logger.info("Status LED task iniciada")
        while self.running:
            try:
                network_status = self.device_manager.get_network_status()
                
                if self.communication_manager.server_communicator.is_connected():
                    # LED fixo quando conectado ao servidor
                    self.hardware_manager.set_led_status(True)
                    await asyncio.sleep(1)
                elif network_status.get('ap_mode', False):
                    # Piscar em modo AP
                    blink_interval = self.hardware_manager.blink_led()
                    await asyncio.sleep(blink_interval)
                else:
                    # LED apagado quando desconectado
                    self.hardware_manager.set_led_status(False)
                    await asyncio.sleep(1)
                    
            except Exception as e:
                logger.error(f"Erro no controle do LED: {e}")
                await asyncio.sleep(1)
    
    def stop(self):
        """Parar sistema gracefulmente"""
        self.running = False
        self.hardware_manager.ir_sensor.stop()
        self.hardware_manager.servo.reset()
        self.communication_manager.stop_communication()
        self.hardware_manager.set_led_status(False)
        logger.info("Sistema parado gracefulmente")
    
    def get_system_status(self):
        """Obter status completo do sistema"""
        return {
            'device': self.device_manager.get_device_info(),
            'network': self.device_manager.get_network_status(),
            'system': self.device_manager.get_system_info(),
            'hardware': self.hardware_manager.get_hardware_info(),
            'communication': self.communication_manager.get_communication_status(),
            'health': self.system_health.get_system_status(),
            'running': self.running,
            'uptime': time.time() - self.startup_time,
            'movements_detected': self.hardware_manager.ir_sensor.detection_count
        }


# Ponto de entrada principal
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
            logger.info("Interrupção por teclado recebida")
        except Exception as e:
            logger.error(f"Erro fatal: {e}")
        finally:
            system.stop()
    else:
        logger.error("Sistema falhou na inicialização")
        logger.info("Entrando em modo de recuperação...")