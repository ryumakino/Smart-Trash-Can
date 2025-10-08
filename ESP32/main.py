# main.py - CORREÇÕES PARA MICROPYTHON
import uasyncio as asyncio
import time
import gc
from utils import get_logger

logger = get_logger("ESP32System")

class TaskManager:
    def __init__(self):
        self.tasks = []
    
    def create_task(self, coroutine, name=None):
        task = asyncio.create_task(coroutine)
        self.tasks.append((task, name))
        logger.debug(f"Task criada: {name}")
        return task
    
    async def cancel_all(self):
        logger.info("Cancelando todas as tasks...")
        for task, name in self.tasks:
            try:
                if not task.done():
                    task.cancel()
                    logger.debug(f"Task cancelada: {name}")
            except Exception as e:
                logger.debug(f"Erro ao cancelar {name}: {e}")
        
        await asyncio.sleep(0.2)
        self.tasks.clear()

class SystemInitializer:
    def __init__(self, device_manager):
        self.device_manager = device_manager
    
    async def initialize(self):
        logger.info("Inicializando sistema...")
        gc.collect()
        
        initialization_steps = [
            self._initialize_wlan,
            self._initialize_hardware, 
            self._initialize_communication
        ]
        
        for step in initialization_steps:
            try:
                success = await step()
                if not success:
                    logger.error(f"Falha no passo: {step.__name__}")
                    return False
                gc.collect()
            except Exception as e:
                logger.error(f"Erro em {step.__name__}: {e}")
                return False
        
        logger.success("✅ Sistema inicializado com sucesso")
        return True
    
    async def _initialize_wlan(self):
        try:
            from wlan_manager import WlanManager
            
            logger.info("🔌 Inicializando WLAN...")
            wlan = WlanManager(self.device_manager)
            connection_result = wlan.connect()
            
            self.device_manager.modules['wlan'] = wlan
            logger.success("✅ WLAN inicializado")
            return True
            
        except Exception as e:
            logger.error(f"❌ Falha no WLAN: {e}")
            return False
    
    async def _initialize_hardware(self):
        try:
            from hardware_manager import HardwareManager
            
            logger.info("🔧 Inicializando hardware...")
            system_config = self.device_manager.get_config('SystemConfig')
            ir_config = self.device_manager.get_config('IRSensorConfig')
            servo_config = self.device_manager.get_config('ServoConfig')
            
            hardware = HardwareManager(system_config, ir_config, servo_config)
            self.device_manager.modules['hardware'] = hardware
            
            logger.success("✅ Hardware inicializado")
            return True
            
        except Exception as e:
            logger.error(f"❌ Falha no hardware: {e}")
            return False
    
    async def _initialize_communication(self):
        try:
            from communication_manager import MultiProtocolManager
            
            logger.info("📡 Inicializando comunicação...")
            hardware = self.device_manager.modules.get('hardware')
            if not hardware:
                logger.error("Hardware não inicializado")
                return False
            
            network_config = self.device_manager.get_network_config()
            communication = MultiProtocolManager(
                self.device_manager, 
                hardware, 
                network_config
            )
            self.device_manager.modules['communication'] = communication
            logger.success("✅ Comunicação inicializada")
            return True
            
        except Exception as e:
            logger.error(f"❌ Falha na comunicação: {e}")
            return False

class MovementHandler:
    def __init__(self, device_manager, cooldown=3):
        self.device_manager = device_manager
        self.cooldown = cooldown
        self.last_movement_time = 0
        self.movement_count = 0
    
    async def handle_movement(self):
        current_time = time.time()
        
        if current_time - self.last_movement_time < self.cooldown:
            logger.debug("Movimento ignorado (cooldown)")
            return
        
        self.last_movement_time = current_time
        self.movement_count += 1
        
        logger.info(f"🚨 Movimento detectado (#{self.movement_count})")
        
        communication = self.device_manager.modules.get('communication')
        if communication and hasattr(communication, 'send_movement_detected'):
            try:
                success = await communication.send_movement_detected()
                if success:
                    logger.info("📤 Movimento reportado para servidor")
                else:
                    logger.warning("⚠️ Falha ao reportar movimento")
            except Exception as e:
                logger.error(f"❌ Erro ao reportar movimento: {e}")
        else:
            logger.info("📡 Movimento detectado (servidor desconectado)")

class HealthMonitor:
    def __init__(self, device_manager):
        self.device_manager = device_manager
        self.last_health_check = 0
        self.health_check_interval = 30
    
    async def check_health(self):
        current_time = time.time()
        
        if current_time - self.last_health_check < self.health_check_interval:
            return
        
        self.last_health_check = current_time
        
        try:
            free_mem = gc.mem_free()
            if free_mem < 10000:
                logger.warning(f"🔄 Memória baixa: {free_mem} bytes")
                gc.collect()
                logger.info(f"✅ Memória após coleta: {gc.mem_free()} bytes")
            
            comm_status = self.device_manager.get_communication_status()
            if not comm_status.get('running', False):
                logger.warning("📡 Comunicação não está rodando")
            
            network_status = self.device_manager.get_network_status()
            if not network_status.get('connected', False):
                logger.warning("🌐 Rede desconectada")
                
            logger.debug("💚 Saúde do sistema OK")
            
        except Exception as e:
            logger.error(f"❌ Erro no health check: {e}")

class NetworkMonitor:
    def __init__(self, device_manager):
        self.device_manager = device_manager
        self.last_network_check = 0
        self.network_check_interval = 60
    
    async def check_network(self):
        current_time = time.time()
        
        if current_time - self.last_network_check < self.network_check_interval:
            return
        
        self.last_network_check = current_time
        
        try:
            wlan = self.device_manager.modules.get('wlan')
            if not wlan:
                return
            
            network_status = self.device_manager.get_network_status()
            
            if not network_status.get('connected', False):
                logger.warning("🌐 Rede desconectada - tentando reconectar...")
                connection_result = wlan.connect()
                
                if connection_result.get('connected', False):
                    logger.success("✅ Rede reconectada")
                else:
                    logger.error("❌ Falha ao reconectar rede")
            else:
                logger.debug("🌐 Rede conectada")
                
        except Exception as e:
            logger.error(f"❌ Erro no network monitor: {e}")

class ESP32System:
    def __init__(self):
        self.device_manager = None
        self.task_manager = TaskManager()
        self.movement_handler = None
        self.health_monitor = None
        self.network_monitor = None
        self.running = False
    
    async def start(self):
        try:
            logger.info("🚀 Iniciando ESP32 TRASH AI System...")
            gc.collect()
            logger.info(f"💾 Memória inicial: {gc.mem_free()} bytes")
            
            from device_manager import DeviceManager
            self.device_manager = DeviceManager()
            
            initializer = SystemInitializer(self.device_manager)
            success = await initializer.initialize()
            
            if not success:
                logger.error("❌ Falha crítica na inicialização - parando")
            
            await self._setup_ir_sensor()
            
            self.movement_handler = MovementHandler(self.device_manager)
            self.health_monitor = HealthMonitor(self.device_manager)
            self.network_monitor = NetworkMonitor(self.device_manager)
            
            self.running = True
            await self._run_system_loops()
            
        except Exception as e:
            logger.error(f"💥 Erro fatal no start: {e}")
            await self.stop()
    
    async def _setup_ir_sensor(self):
        try:
            hardware = self.device_manager.modules.get('hardware')
            if hardware:
                # CORREÇÃO: Nome correto do componente
                ir_sensor = hardware.get_component('ir')
                if ir_sensor and hasattr(ir_sensor, 'start'):
                    # CORREÇÃO: Passar callback corretamente
                    ir_sensor.start(self.on_movement_detected)
                    logger.info("✅ Sensor IR configurado com callback")
        except Exception as e:
            logger.error(f"❌ Erro ao configurar sensor IR: {e}")
    
    async def _run_system_loops(self):
        logger.info("🔄 Iniciando loops do sistema...")
        
        communication = self.device_manager.modules.get('communication')
        if communication and hasattr(communication, 'start_communication'):
            try:
                self.task_manager.create_task(
                    communication.start_communication(),
                    "communication_main"
                )
                logger.info("✅ Task de comunicação iniciada")
            except Exception as e:
                logger.warning(f"⚠️ Não foi possível iniciar comunicação: {e}")
        
        self.task_manager.create_task(self._health_monitor_loop(), "health_monitor")
        self.task_manager.create_task(self._network_monitor_loop(), "network_monitor")
        self.task_manager.create_task(self._status_logger_loop(), "status_logger")
        
        logger.success("✅ Sistema inicializado (modo: {})".format(
            "COMUNICAÇÃO" if communication else "STANDALONE"
        ))
        await self._main_loop()
    
    async def _health_monitor_loop(self):
        while self.running:
            try:
                await self.health_monitor.check_health()
                await asyncio.sleep(10)
            except Exception as e:
                logger.error(f"❌ Erro no health loop: {e}")
                await asyncio.sleep(30)
    
    async def _network_monitor_loop(self):
        while self.running:
            try:
                await self.network_monitor.check_network()
                await asyncio.sleep(30)
            except Exception as e:
                logger.error(f"❌ Erro no network loop: {e}")
                await asyncio.sleep(60)
    
    async def _status_logger_loop(self):
        while self.running:
            try:
                await self._log_system_status()
                await asyncio.sleep(30)
            except Exception as e:
                logger.error(f"❌ Erro no status logger: {e}")
                await asyncio.sleep(60)
    
    async def _main_loop(self):
        logger.info("🎯 Entrando no loop principal...")
        
        cycle_count = 0
        last_memory_log = time.time()
        
        while self.running:
            try:
                cycle_count += 1
                
                current_time = time.time()
                if current_time - last_memory_log > 60:
                    logger.debug(f"🔁 Ciclo #{cycle_count} - Memória: {gc.mem_free()} bytes")
                    last_memory_log = current_time
                    cycle_count = 0
                
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.error(f"❌ Erro no loop principal: {e}")
                await asyncio.sleep(5)
    
    async def _log_system_status(self):
        try:
            comm_status = self.device_manager.get_communication_status()
            server_connected = comm_status.get('server_connected', False)
            active_protocol = comm_status.get('active_protocol', 'NONE')
            
            network_status = self.device_manager.get_network_status()
            network_connected = network_status.get('connected', False)
            network_mode = network_status.get('mode', 'UNKNOWN')
            
            server_info = self.device_manager.get_server_info()
            server_name = server_info.get('name', 'Unknown')
            
            if server_connected:
                status_msg = f"🎯 Conectado via {active_protocol.upper()} → {server_name}"
            elif active_protocol:
                status_msg = f"🔍 Procurando servidor via {active_protocol.upper()}..."
            else:
                status_msg = "🔌 Sem comunicação ativa"
            
            if network_connected:
                status_msg += f" | 🌐 {network_mode}"
            else:
                status_msg += " | 🌐❌ SEM REDE"
            
            status_msg += f" | 💾 {gc.mem_free()} bytes"
            
            logger.info(status_msg)
            
        except Exception as e:
            logger.debug(f"Erro no log de status: {e}")
    
    async def on_movement_detected(self):
        if self.movement_handler:
            await self.movement_handler.handle_movement()
        else:
            logger.warning("Movement handler não disponível")
    
    async def stop(self):
        logger.info("🛑 Parando sistema...")
        self.running = False
        
        await self.task_manager.cancel_all()
        
        if self.device_manager and hasattr(self.device_manager, 'modules'):
            for name, module in self.device_manager.modules.items():
                try:
                    if hasattr(module, 'cleanup'):
                        module.cleanup()
                        logger.debug(f"Módulo {name} limpo")
                    elif hasattr(module, 'stop'):
                        module.stop()
                        logger.debug(f"Módulo {name} parado")
                except Exception as e:
                    logger.error(f"Erro ao limpar {name}: {e}")
        
        gc.collect()
        logger.info(f"💾 Memória final: {gc.mem_free()} bytes")
        logger.info("✅ Sistema parado com sucesso")

async def main():
    system = None
    
    try:
        logger.info("=" * 50)
        logger.info("🚀 ESP32 TRASH AI - INICIANDO")
        logger.info("=" * 50)
        
        gc.collect()
        initial_memory = gc.mem_free()
        logger.info(f"💾 Memória inicial: {initial_memory} bytes")
        
        system = ESP32System()
        await system.start()
        
    except Exception as e:
        logger.error(f"💥 ERRO FATAL: {e}")
        
        if system:
            try:
                await system.stop()
            except Exception as stop_error:
                logger.error(f"Erro durante parada: {stop_error}")
        
        await asyncio.sleep(3)
        
        try:
            import machine
            logger.error("🔄 Reinício de emergência...")
            machine.reset()
        except Exception as reset_error:
            logger.error(f"❌ Não foi possível reiniciar: {reset_error}")
    
    finally:
        logger.info("=" * 50)
        logger.info("🏁 ESP32 TRASH AI - FINALIZADO")
        logger.info("=" * 50)

try:
    asyncio.run(main())
except Exception as e:
    try:
        print(f"💥 CRITICAL: {e}")
        import machine
        machine.reset()
    except:
        pass