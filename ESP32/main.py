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
from error_handler import ErrorHandler
from recovery import RecoverySystem

logger = get_logger("ESP32System")

class SystemMonitor:
    """SRP: Monitorar saúde do sistema"""
    
    def __init__(self, device_manager):
        self.device_manager = device_manager
        self.last_memory_check = 0
        self.memory_check_interval = 30
    
    async def check_system_health(self):
        """Verificar saúde do sistema periodicamente"""
        try:
            # Verificar memória
            if time.time() - self.last_memory_check > self.memory_check_interval:
                free_mem = gc.mem_free()
                if free_mem < 10000:
                    logger.warning(f"Memória baixa: {free_mem} bytes")
                
                if gc.mem_free() < 20000:
                    gc.collect()
                    logger.debug("Coleta de lixo realizada")
                
                self.last_memory_check = time.time()
            
            return True
        except Exception as e:
            logger.error(f"Erro na verificação: {e}")
            return False

class StatusLEDController:
    """SRP: Controlar LED de status"""
    
    def __init__(self, hardware_manager, device_manager):
        self.hardware_manager = hardware_manager
        self.device_manager = device_manager
    
    async def run_status_sequence(self):
        """Executar sequência de status"""
        while True:
            try:
                network_status = self.device_manager.get_network_status()
                comm_status = self.device_manager.get_communication_status()
                
                if comm_status.get('connected'):
                    # LED fixo quando conectado
                    self.hardware_manager.set_led_status(True)
                    await asyncio.sleep(1)
                elif network_status.get('ap_mode'):
                    # Piscar rápido em AP
                    await self._blink_led(0.2, 0.2)
                elif network_status.get('connected'):
                    # Piscar lento em WiFi
                    await self._blink_led(0.5, 0.5)
                else:
                    # LED apagado
                    self.hardware_manager.set_led_status(False)
                    await asyncio.sleep(1)
                    
            except Exception as e:
                logger.error(f"Erro no LED: {e}")
                await asyncio.sleep(1)
    
    async def _blink_led(self, on_time, off_time):
        """Piscar LED - DRY"""
        self.hardware_manager.set_led_status(True)
        await asyncio.sleep(on_time)
        self.hardware_manager.set_led_status(False)
        await asyncio.sleep(off_time)

class ESP32System:
    """Orquestrador principal - SRP"""
    
    def __init__(self):
        # Injeção de dependências
        self.device_manager = DeviceManager()
        self.recovery = RecoverySystem()
        self.error_handler = ErrorHandler(self.recovery)
        
        # Configurações
        system_config = self.device_manager.get_system_config()
        ir_config = self.device_manager.get_ir_config()
        servo_config = self.device_manager.get_servo_config()
        network_config = self.device_manager.get_network_config()
        
        # Componentes especializados
        self.hardware_manager = HardwareManager(system_config, ir_config, servo_config)
        self.wifi_manager = WlanManager(self.device_manager)
        self.communication = CommunicationManager(
            self.device_manager, self.hardware_manager, network_config
        )
        self.system_monitor = SystemMonitor(self.device_manager)
        self.led_controller = StatusLEDController(self.hardware_manager, self.device_manager)
        
        # Estado
        self.running = False
        self.startup_time = time.time()
        self.movement_cooldown = 2
        self.last_movement_time = 0
        
        self._initialize_system()
    
    def _initialize_system(self):
        """Inicialização centralizada - SRP"""
        try:
            # 1. Conectar rede
            connection_result = self.wifi_manager.connect()
            self.device_manager.update_network_info(connection_result)
            
            # 2. Configurar sensor IR
            ir_sensor = self.hardware_manager.get_component('ir_sensor')
            if ir_sensor:
                ir_sensor.start(callback=self.on_movement_detected)
            
            # 3. Log inicial
            self._log_initial_status()
            
            self.running = True
            logger.success("Sistema inicializado")
            
        except Exception as e:
            logger.error(f"Falha na inicialização: {e}")
            self.recovery.record_failure(f"System init: {str(e)}")
    
    def _log_initial_status(self):
        """Log do status inicial - SRP"""
        device_info = self.device_manager.get_device_info()
        network_status = self.device_manager.get_network_status()
        
        logger.info("=== STATUS INICIAL ===")
        logger.info(f"Dispositivo: {device_info['device_name']}")
        logger.info(f"ID: {device_info['device_id']}")
        logger.info(f"IP: {network_status.get('ip', 'N/A')}")
        logger.info(f"Modo: {'AP' if network_status.get('ap_mode') else 'STA'}")
        logger.info("======================")
    
    async def on_movement_detected(self):
        """Callback para detecção de movimento - SRP"""
        current_time = time.time()
        
        # Cooldown
        if current_time - self.last_movement_time < self.movement_cooldown:
            return
        
        self.last_movement_time = current_time
        
        # Notificar servidor se conectado
        comm_status = self.device_manager.get_communication_status()
        if comm_status.get('connected'):
            await self.error_handler.safe_execute(
                self.communication.send_movement_detected(),
                "Movement notification"
            )
            logger.info("Movimento detectado - notificação enviada")
        else:
            logger.info("Movimento detectado - servidor desconectado")
    
    async def run_async(self):
        """Loop principal - SRP"""
        logger.info("Iniciando loop principal...")
        
        # Iniciar serviços
        await self.communication.start_communication()
        
        # Criar tasks especializadas
        tasks = [
            asyncio.create_task(self.system_monitor.check_system_health()),
            asyncio.create_task(self.led_controller.run_status_sequence()),
            asyncio.create_task(self._network_maintenance_task())
        ]
        
        # Loop principal simplificado
        while self.running:
            try:
                await asyncio.sleep(1)
            except Exception as e:
                logger.error(f"Erro no loop: {e}")
                await asyncio.sleep(5)
        
        # Cleanup
        for task in tasks:
            task.cancel()
        
        self.stop()
    
    async def _network_maintenance_task(self):
        """Manutenção de rede - SRP"""
        while self.running:
            try:
                network_status = self.device_manager.get_network_status()
                if not network_status.get('connected') and not network_status.get('ap_mode'):
                    logger.warning("Rede desconectada - tentando reconectar...")
                    connection_result = self.wifi_manager.connect()
                    self.device_manager.update_network_info(connection_result)
                
                await asyncio.sleep(30)
            except Exception as e:
                logger.error(f"Erro na manutenção: {e}")
                await asyncio.sleep(30)
    
    def stop(self):
        """Parada graceful - SRP"""
        self.running = False
        self.hardware_manager.cleanup_all()
        self.communication.stop_communication()
        logger.info("Sistema parado")
    
    def get_system_status(self):
        """Status completo - Facade pattern"""
        return self.device_manager.get_complete_status()

# Ponto de entrada - SRP
async def main():
    system = ESP32System()
    
    if system.running:
        try:
            status = system.get_system_status()
            logger.info(f"Sistema: {status['device']['device_name']}")
            logger.info(f"IP: {status['network'].get('ip', 'N/A')}")
            logger.info(f"Memória: {status['system']['memory_free']} bytes")
            
            await system.run_async()
            
        except KeyboardInterrupt:
            logger.info("Interrupção recebida")
        except Exception as e:
            logger.error(f"Erro fatal: {e}")
        finally:
            system.stop()
    else:
        logger.error("Sistema falhou na inicialização")
        machine.reset()

if __name__ == "__main__":
    asyncio.run(main())