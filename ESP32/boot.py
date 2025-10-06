# boot.py - Inicialização segura do ESP32 com SOLID/DRY
import machine
import time
import gc
import os
from utils import get_logger

# Configurar logger mínimo antes do sistema completo
class BootLogger:
    """Logger mínimo para fase de boot"""
    @staticmethod
    def log(level, message):
        print(f"[{level}] {message}")
    
    @staticmethod
    def info(message):
        BootLogger.log("INFO", message)
    
    @staticmethod
    def error(message):
        BootLogger.log("ERROR", message)
    
    @staticmethod
    def success(message):
        BootLogger.log("SUCCESS", message)

class HardwareValidator:
    """SRP: Validar hardware durante o boot"""
    
    @staticmethod
    def validate_memory() -> bool:
        """Validar memória disponível"""
        free_memory = gc.mem_free()
        BootLogger.info(f"Free memory: {free_memory} bytes")
        
        if free_memory < 30000:  # Mínimo para operação
            BootLogger.error(f"Memory critically low: {free_memory} bytes")
            return False
        elif free_memory < 50000:
            BootLogger.info("Memory low but operational")
        return True
    
    @staticmethod
    def validate_filesystem() -> bool:
        """Validar sistema de arquivos"""
        try:
            files = os.listdir()
            required_files = ['config.json', 'main.py']
            
            missing_files = [f for f in required_files if f not in files]
            if missing_files:
                BootLogger.error(f"Missing required files: {missing_files}")
                return False
            
            BootLogger.info(f"Filesystem OK, {len(files)} files found")
            return True
            
        except Exception as e:
            BootLogger.error(f"Filesystem validation failed: {e}")
            return False
    
    @staticmethod
    def validate_cpu() -> bool:
        """Validar CPU e reset cause"""
        try:
            reset_cause = HardwareValidator.get_reset_cause()
            cpu_freq = machine.freq()
            
            BootLogger.info(f"CPU Frequency: {cpu_freq // 1000000}MHz")
            BootLogger.info(f"Reset cause: {reset_cause}")
            
            # Verificar se foi um reset por watchdog
            if reset_cause == "WATCHDOG":
                BootLogger.error("Watchdog reset detected - possible system hang")
                return False
                
            return True
            
        except Exception as e:
            BootLogger.error(f"CPU validation failed: {e}")
            return False
    
    @staticmethod
    def get_reset_cause() -> str:
        """Obter motivo do reset de forma segura"""
        try:
            reset_cause = machine.reset_cause()
            reasons = {
                machine.PWRON_RESET: "POWER_ON",
                machine.HARD_RESET: "HARD_RESET", 
                machine.WDT_RESET: "WATCHDOG",
                machine.DEEPSLEEP_RESET: "DEEP_SLEEP",
                machine.SOFT_RESET: "SOFT_RESET"
            }
            return reasons.get(reset_cause, "UNKNOWN")
        except:
            return "UNKNOWN"

class BootConfigurator:
    """SRP: Configurar sistema durante o boot"""
    
    @staticmethod
    def optimize_system():
        """Otimizar sistema para melhor performance"""
        try:
            # Coleta de lixo agressiva no boot
            gc.collect()
            initial_memory = gc.mem_free()
            
            # Configurar thresholds de GC (se suportado)
            if hasattr(gc, 'threshold'):
                gc.threshold(50000)  # Coletar quando alocar 50KB
            
            # Configurar frequência da CPU baseado na disponibilidade de energia
            BootConfigurator._configure_cpu_frequency()
            
            gc.collect()
            final_memory = gc.mem_free()
            BootLogger.info(f"Memory optimized: {initial_memory} -> {final_memory} bytes")
            
        except Exception as e:
            BootLogger.error(f"System optimization failed: {e}")
    
    @staticmethod
    def _configure_cpu_frequency():
        """Configurar frequência da CPU baseado nas condições"""
        try:
            # Tentar detectar condições de energia
            current_freq = machine.freq()
            
            # Se já está em alta frequência, manter
            if current_freq >= 240000000:
                BootLogger.info("CPU already at high frequency")
                return
            
            # Tentar aumentar para performance máxima
            try:
                machine.freq(240000000)  # 240MHz
                BootLogger.info("CPU frequency set to 240MHz")
            except:
                BootLogger.info("CPU frequency adjustment not supported")
                
        except Exception as e:
            BootLogger.info(f"CPU frequency configuration skipped: {e}")

class BootIndicator:
    """SRP: Indicadores visuais de boot"""
    
    def __init__(self, led_pin=2):
        self.led = machine.Pin(led_pin, machine.Pin.OUT)
        self.led.off()
    
    def sequence_ok(self):
        """Sequência de boot bem-sucedido"""
        self._blink_pattern([0.1, 0.1, 0.3, 0.1, 0.1])
        self.led.off()
    
    def sequence_error(self):
        """Sequência de boot com erro"""
        self._blink_pattern([0.3, 0.3, 0.3, 0.3, 0.3])
        self.led.off()
    
    def sequence_retry(self):
        """Sequência de tentativa de recuperação"""
        self._blink_pattern([0.05, 0.05, 0.05, 0.3])
        self.led.off()
    
    def _blink_pattern(self, pattern):
        """Executar padrão de piscada - DRY"""
        for delay in pattern:
            self.led.on()
            time.sleep(delay)
            self.led.off()
            time.sleep(0.1)

class BootManager:
    """Composite: Gerenciador principal do boot"""
    
    def __init__(self):
        self.validator = HardwareValidator()
        self.configurator = BootConfigurator()
        self.indicator = BootIndicator()
        self.boot_attempts = 0
        self.max_boot_attempts = 3
    
    def perform_safe_boot(self) -> bool:
        """Executar boot seguro com validações"""
        self.boot_attempts += 1
        
        BootLogger.info("=== ESP32 TRASH AI BOOT ===")
        BootLogger.info(f"Boot attempt: {self.boot_attempts}/{self.max_boot_attempts}")
        
        # Fase 1: Validações críticas
        if not self._perform_critical_validations():
            self.indicator.sequence_error()
            return False
        
        # Fase 2: Otimizações do sistema
        self.configurator.optimize_system()
        
        # Fase 3: Indicar boot bem-sucedido
        self.indicator.sequence_ok()
        
        BootLogger.success("Boot completed successfully")
        return True
    
    def _perform_critical_validations(self) -> bool:
        """Executar validações críticas do sistema"""
        validations = [
            ("Memory", self.validator.validate_memory),
            ("Filesystem", self.validator.validate_filesystem),
            ("CPU", self.validator.validate_cpu)
        ]
        
        for name, validation_func in validations:
            try:
                if not validation_func():
                    BootLogger.error(f"Critical validation failed: {name}")
                    return False
                BootLogger.info(f"Validation passed: {name}")
            except Exception as e:
                BootLogger.error(f"Validation error in {name}: {e}")
                return False
        
        return True
    
    def handle_boot_failure(self):
        """Tratamento de falha no boot"""
        BootLogger.error("=== BOOT FAILURE ===")
        
        if self.boot_attempts >= self.max_boot_attempts:
            BootLogger.error("Max boot attempts reached - initiating recovery")
            self._emergency_recovery()
        else:
            BootLogger.info("Will retry boot after delay")
            self.indicator.sequence_retry()
            time.sleep(5)  # Esperar antes de retry
    
    def _emergency_recovery(self):
        """Procedimentos de emergência"""
        try:
            BootLogger.info("Attempting emergency recovery...")
            
            # Tentar limpar memória
            gc.collect()
            
            # Tentar reset suave primeiro
            BootLogger.info("Performing soft reset...")
            time.sleep(2)
            machine.soft_reset()
            
        except Exception as e:
            BootLogger.error(f"Emergency recovery failed: {e}")
            # Último recurso - hard reset
            BootLogger.info("Performing hard reset...")
            time.sleep(2)
            machine.reset()

def main():
    """Ponto de entrada principal do boot"""
    boot_manager = BootManager()
    
    # Tentar boot seguro
    if boot_manager.perform_safe_boot():
        # Boot bem-sucedido - iniciar aplicação principal
        try:
            BootLogger.info("Starting main application...")
            
            # Importar e iniciar main application
            from main import main as app_main
            import uasyncio as asyncio
            
            # Executar aplicação principal
            asyncio.run(app_main())
            
        except ImportError as e:
            BootLogger.error(f"Failed to import main application: {e}")
            boot_manager.handle_boot_failure()
        except Exception as e:
            BootLogger.error(f"Main application error: {e}")
            boot_manager.handle_boot_failure()
    else:
        # Boot falhou
        boot_manager.handle_boot_failure()

if __name__ == '__main__':
    main()