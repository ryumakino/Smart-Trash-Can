# boot.py - CORREÇÕES PARA MICROPYTHON
import machine
import time
import gc
import os
import sys

# CORREÇÃO: Importação segura para MicroPython
try:
    from utils import get_logger
except ImportError:
    class MockLogger:
        def info(self, msg): print(f"[INFO] {msg}")
        def warning(self, msg): print(f"[WARN] {msg}")
        def error(self, msg): print(f"[ERROR] {msg}")
        def success(self, msg): print(f"[SUCCESS] {msg}")
    
    def get_logger(name): return MockLogger()

logger = get_logger("Boot")

class HardwareValidator:
    @staticmethod
    def validate_memory() -> bool:
        gc.collect()
        free_memory = gc.mem_free()
        logger.info(f"Free memory: {free_memory} bytes")
        
        if free_memory < 10000:
            logger.error(f"Memory critically low: {free_memory} bytes")
            return False
        elif free_memory < 20000:
            logger.warning("Memory low but operational")
        return True
    
    @staticmethod
    def validate_filesystem() -> bool:
        try:
            files = os.listdir()
            required_files = ['config.json', 'main.py']
            
            missing_files = [f for f in required_files if f not in files]
            if missing_files:
                logger.error(f"Missing required files: {missing_files}")
                return False
            
            logger.info(f"Filesystem OK, {len(files)} files found")
            return True
            
        except Exception as e:
            logger.error(f"Filesystem validation failed: {e}")
            return False
    
    @staticmethod
    def validate_cpu() -> bool:
        try:
            reset_cause_str = HardwareValidator.get_reset_cause()
            # CORREÇÃO: machine.freq() pode não estar disponível
            try:
                cpu_freq = machine.freq()
                logger.info(f"CPU Frequency: {cpu_freq // 1000000}MHz")
            except:
                logger.info("CPU Frequency: Unknown")
            
            logger.info(f"Reset cause: {reset_cause_str}")
            
            if reset_cause_str == "WATCHDOG":
                logger.error("Watchdog reset detected - possible system hang")
            
            return True
            
        except Exception as e:
            logger.error(f"CPU validation failed: {e}")
            return False
    
    @staticmethod
    def get_reset_cause() -> str:
        try:
            reset_cause = machine.reset_cause()
            # CORREÇÃO: Constantes do MicroPython
            reasons = {
                0: "POWER_ON",      # machine.PWRON_RESET
                1: "HARD_RESET",    # machine.HARD_RESET  
                2: "WATCHDOG",      # machine.WDT_RESET
                3: "DEEP_SLEEP",    # machine.DEEPSLEEP_RESET
                4: "SOFT_RESET",    # machine.SOFT_RESET
            }
            return reasons.get(reset_cause, f"UNKNOWN({reset_cause})")
        except:
            return "UNKNOWN_ERROR"

class BootConfigurator:
    @staticmethod
    def optimize_system():
        try:
            gc.collect()
            
            # CORREÇÃO: Verificar se threshold existe
            if hasattr(gc, 'threshold'):
                gc.threshold(30000)
            
            gc.collect()
            logger.info(f"Memory after optimization: {gc.mem_free()} bytes")
            
        except Exception as e:
            logger.error(f"System optimization failed: {e}")

class BootIndicator:
    def __init__(self, led_pin=2):
        try:
            self.led = machine.Pin(led_pin, machine.Pin.OUT)
            self.led.value(0)
            self.working = True
        except:
            self.working = False
            logger.warning("LED Pin not configured/available for BootIndicator")
    
    def _set_led(self, state):
        if self.working:
            self.led.value(state)
    
    def sequence_ok(self):
        self._blink_pattern([0.1, 0.1, 0.1, 0.1])
        self._set_led(0)
    
    def sequence_error(self):
        self._blink_pattern([0.3, 0.3, 0.3, 0.3, 0.3, 0.3])
        self._set_led(0)
    
    def sequence_retry(self):
        self._blink_pattern([0.05, 0.05, 0.05, 0.05, 0.05, 0.05, 0.05])
        self._set_led(0)
    
    def _blink_pattern(self, pattern):
        if not self.working:
            return
            
        for delay in pattern:
            self._set_led(1)
            time.sleep(delay)
            self._set_led(0)
            time.sleep(0.05)

class BootManager:
    def __init__(self):
        self.validator = HardwareValidator()
        self.configurator = BootConfigurator()
        self.indicator = BootIndicator(led_pin=2)
        self.boot_attempts = 0
        self.max_boot_attempts = 3
    
    def perform_safe_boot(self) -> bool:
        self.boot_attempts += 1
        
        logger.info("=== ESP32 TRASH AI BOOT ===")
        logger.info(f"Boot attempt: {self.boot_attempts}/{self.max_boot_attempts}")
        
        if not self._perform_critical_validations():
            self.indicator.sequence_error()
            return False
        
        self.configurator.optimize_system()
        self.indicator.sequence_ok()
        
        logger.success("Boot completed successfully")
        return True
    
    def _perform_critical_validations(self) -> bool:
        validations = [
            ("Memory", self.validator.validate_memory),
            ("Filesystem", self.validator.validate_filesystem),
            ("CPU", self.validator.validate_cpu)
        ]
        
        for name, validation_func in validations:
            try:
                if not validation_func():
                    logger.error(f"Critical validation failed: {name}")
                    return False
                logger.info(f"Validation passed: {name}")
            except Exception as e:
                logger.error(f"Validation error in {name}: {e}")
                return False
        
        return True
    
    def handle_boot_failure(self):
        logger.error("=== BOOT FAILURE ===")
        
        if self.boot_attempts >= self.max_boot_attempts:
            logger.error("Max boot attempts reached - initiating recovery")
            self._emergency_recovery()
        else:
            logger.info("Will retry boot after delay")
            self.indicator.sequence_retry()
            time.sleep(5)
    
    def _emergency_recovery(self):
        logger.info("Attempting emergency recovery...")
        gc.collect()
        
        logger.info("Performing soft reset...")
        time.sleep(2)
        try:
            # CORREÇÃO: MicroPython usa machine.reset() para soft reset
            machine.reset()
        except:
            machine.reset()

def main():
    boot_manager = BootManager()
    
    if boot_manager.perform_safe_boot():
        try:
            logger.info("Starting main application...")
            
            # CORREÇÃO: Importação segura para MicroPython
            import main
            import uasyncio as asyncio
            
            # CORREÇÃO: Verificar se main tem função main, senão executar diretamente
            if hasattr(main, 'main') and callable(main.main):
                # Executar aplicação principal se existir main()
                asyncio.run(main.main())
            else:
                # Se não tiver main(), importar e executar a aplicação principal
                logger.info("Starting application directly...")
                from main import app
                asyncio.run(app.run_application())
            
        except ImportError as e:
            logger.error(f"Failed to import main application: {e}")
            boot_manager.handle_boot_failure()
        except Exception as e:
            logger.error(f"Main application error: {e}")
            boot_manager.handle_boot_failure()
    else:
        boot_manager.handle_boot_failure()

try:
    main()
except Exception as e:
    print(f"CRITICAL BOOT ERROR: {e}")
    machine.reset()