# recovery.py
import machine
import time
from utils import get_logger

logger = get_logger("Recovery")

class FailureTracker:
    """SRP: Rastrear falhas do sistema"""
    
    def __init__(self, max_failures=5, failure_timeout=300):
        self.max_failures = max_failures
        self.failure_timeout = failure_timeout
        self.failure_count = 0
        self.last_failure_time = 0
        self.failure_history = []
    
    def record_failure(self, error_type="Unknown"):
        """Registrar uma falha"""
        current_time = time.time()
        
        # Limpar falhas antigas
        if current_time - self.last_failure_time > self.failure_timeout:
            self.failure_count = 0
            self.failure_history.clear()
            
        self.failure_count += 1
        self.last_failure_time = current_time
        
        # Manter histórico
        self.failure_history.append({
            'timestamp': current_time,
            'type': error_type,
            'count': self.failure_count
        })
        
        # Manter histórico limitado
        if len(self.failure_history) > 10:
            self.failure_history = self.failure_history[-10:]
        
        logger.warning(f"Falha #{self.failure_count}: {error_type}")
        return self.failure_count
    
    def should_recover(self) -> bool:
        """Verificar se deve iniciar recuperação"""
        return self.failure_count >= self.max_failures
    
    def reset_counter(self):
        """Resetar contador de falhas"""
        self.failure_count = 0
        logger.info("Contador de falhas resetado")
    
    def get_failure_stats(self):
        """Obter estatísticas de falhas"""
        return {
            'current_count': self.failure_count,
            'last_failure_time': self.last_failure_time,
            'history_length': len(self.failure_history),
            'time_since_last_failure': time.time() - self.last_failure_time
        }

class RecoveryStrategy:
    """SRP: Estratégias de recuperação"""
    
    @staticmethod
    def soft_reset():
        """Reset suave do sistema"""
        logger.info("Executando soft reset...")
        time.sleep(2)
        machine.soft_reset()
    
    @staticmethod
    def hard_reset():
        """Reset completo do sistema"""
        logger.info("Executando hard reset...")
        time.sleep(2)
        machine.reset()
    
    @staticmethod
    def partial_reset(components=None):
        """Reset parcial de componentes específicos"""
        logger.info("Executando reset parcial...")
        # Aqui poderia reinicializar componentes específicos
        # como WiFi, serviços, etc.
        if components:
            logger.info(f"Reinicializando componentes: {components}")
        return True

class RecoveryExecutor:
    """SRP: Executor de procedimentos de recuperação"""
    
    def __init__(self, failure_tracker):
        self.failure_tracker = failure_tracker
        self.recovery_strategy = RecoveryStrategy()
        self.recovery_attempts = 0
        self.max_recovery_attempts = 3
    
    def initiate_recovery(self):
        """Iniciar procedimento de recuperação"""
        try:
            self.recovery_attempts += 1
            logger.error("=== INICIANDO RECUPERAÇÃO DO SISTEMA ===")
            
            # Tentar reset suave primeiro
            if self.recovery_attempts <= self.max_recovery_attempts:
                logger.info(f"Tentativa de recuperação #{self.recovery_attempts}")
                self.recovery_strategy.soft_reset()
            else:
                # Forçar reset completo após muitas tentativas
                logger.error("Muitas tentativas de recuperação - reset completo")
                self.recovery_strategy.hard_reset()
                
        except Exception as e:
            logger.error(f"Falha na recuperação: {e}")
            # Último recurso
            self.recovery_strategy.hard_reset()

class RecoverySystem:
    """Composite: Sistema de recuperação principal"""
    
    def __init__(self, max_failures=5):
        self.failure_tracker = FailureTracker(max_failures)
        self.recovery_executor = RecoveryExecutor(self.failure_tracker)
    
    def record_failure(self, error_type="Unknown"):
        """Registrar falha e verificar recuperação"""
        count = self.failure_tracker.record_failure(error_type)
        
        if self.failure_tracker.should_recover():
            self.recovery_executor.initiate_recovery()
        
        return count
    
    def reset_counter(self):
        """Resetar contador de falhas"""
        self.failure_tracker.reset_counter()
    
    def soft_reset(self):
        """Reset suave manual"""
        self.recovery_executor.recovery_strategy.soft_reset()
    
    def hard_reset(self):
        """Reset completo manual"""
        self.recovery_executor.recovery_strategy.hard_reset()
    
    def get_recovery_status(self):
        """Obter status do sistema de recuperação"""
        failure_stats = self.failure_tracker.get_failure_stats()
        return {
            **failure_stats,
            'recovery_attempts': self.recovery_executor.recovery_attempts,
            'max_recovery_attempts': self.recovery_executor.max_recovery_attempts,
            'needs_recovery': self.failure_tracker.should_recover()
        }