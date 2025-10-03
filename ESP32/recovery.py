# recovery.py
import machine
import time
from utils import get_logger

logger = get_logger("Recovery")

class RecoverySystem:
    def __init__(self, max_failures=5):
        self.max_failures = max_failures
        self.failure_count = 0
        self.last_failure_time = 0
        self.failure_timeout = 300
        
    def record_failure(self, error_type="Unknown"):
        """Registrar uma falha no sistema"""
        current_time = time.time()
        
        if current_time - self.last_failure_time > self.failure_timeout:
            self.failure_count = 0
            
        self.failure_count += 1
        self.last_failure_time = current_time
        
        logger.warning(f"Failure #{self.failure_count}: {error_type}")
        
        if self.failure_count >= self.max_failures:
            logger.error("Max failures reached - initiating recovery")
            self.initiate_recovery()
    
    def initiate_recovery(self):
        """Iniciar procedimento de recuperação"""
        try:
            logger.error("=== SYSTEM RECOVERY INITIATED ===")
            self.soft_reset()
        except Exception as e:
            logger.error(f"Soft reset failed: {e}")
            self.hard_reset()
    
    def soft_reset(self):
        """Reset suave"""
        logger.info("Performing soft reset...")
        time.sleep(2)
        machine.soft_reset()
    
    def hard_reset(self):
        """Reset hard"""
        logger.info("Performing hard reset...")
        time.sleep(2)
        machine.reset()
    
    def reset_counter(self):
        """Resetar contador de falhas"""
        self.failure_count = 0
        logger.info("Failure counter reset")