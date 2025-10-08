# recovery.py
import machine
import time
from utils import get_logger

logger = get_logger("Recovery")

class FailureTracker:
    """SRP: Rastreamento de falhas"""
    
    def __init__(self, max_failures=5):
        self.max_failures = max_failures
        self.failure_count = 0
        self.last_failure_time = 0
    
    def record_failure(self, error_type="Unknown"):
        current_time = time.time()
        
        # Reset se última falha foi há muito tempo
        if current_time - self.last_failure_time > 300:  # 5 minutos
            self.failure_count = 0
        
        self.failure_count += 1
        self.last_failure_time = current_time
        
        logger.warning(f"Falha #{self.failure_count}: {error_type}")
        return self.failure_count
    
    def should_recover(self):
        return self.failure_count >= self.max_failures
    
    def reset(self):
        self.failure_count = 0
        logger.info("Contador de falhas resetado")

class ResetExecutor:
    """SRP: Execução de reset"""
    
    @staticmethod
    def soft_reset():
        logger.info("Soft reset...")
        time.sleep(2)
        try:
            machine.soft_reset()
        except:
            machine.reset()
    
    @staticmethod
    def hard_reset():
        logger.info("Hard reset...")
        time.sleep(2)
        machine.reset()

class RecoveryManager:
    """Facade: Gerenciador de recuperação"""
    
    def __init__(self, max_failures=5):
        self.tracker = FailureTracker(max_failures)
        self.reset_executor = ResetExecutor()
        self.recovery_attempts = 0
    
    def record_failure(self, error_type="Unknown"):
        count = self.tracker.record_failure(error_type)
        
        if self.tracker.should_recover():
            logger.critical("Limite de falhas - iniciando recuperação")
            self._execute_recovery()
        
        return count
    
    def _execute_recovery(self):
        """Execução de recuperação - SRP"""
        self.recovery_attempts += 1
        
        if self.recovery_attempts == 1:
            logger.info("Tentando reset parcial...")
            # Reset parcial poderia ser implementado aqui
            self.tracker.reset()
            return
        
        logger.info(f"Recuperação #{self.recovery_attempts}")
        self.reset_executor.soft_reset()
    
    def get_status(self):
        return {
            'failure_count': self.tracker.failure_count,
            'recovery_attempts': self.recovery_attempts,
            'needs_recovery': self.tracker.should_recover(),
            'timestamp': time.time()
        }