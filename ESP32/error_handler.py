# error_handler.py - CORREÇÕES COMPLETAS
import uasyncio as asyncio
from utils import get_logger

logger = get_logger("ErrorHandler")

class ErrorClassifier:
    @staticmethod
    def classify(error):
        error_type = type(error).__name__
        error_str = str(error).lower()
        
        if "memory" in error_str or "Memory" in error_type:
            return "MEMORY_ERROR"
        elif "network" in error_str or "OSError" in error_type or "socket" in error_str:
            return "NETWORK_ERROR"
        elif "ValueError" in error_type:
            return "VALUE_ERROR"
        elif "TypeError" in error_type:
            return "TYPE_ERROR"
        elif "Timeout" in error_str:
            return "TIMEOUT_ERROR"
        return "UNKNOWN_ERROR"
    
    @staticmethod
    def should_retry(error_type):
        return error_type not in ['MEMORY_ERROR', 'TYPE_ERROR']

class RetryCalculator:
    def __init__(self, max_retries=3, base_delay=1, max_delay=30):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
    
    def get_delay(self, attempt):
        try:
            delay = self.base_delay * (2 ** (attempt - 1))
            return min(delay, self.max_delay)
        except:
            return self.base_delay

class OperationExecutor:
    def __init__(self, classifier, retry_calc, recovery_system):
        self.classifier = classifier
        self.retry_calc = retry_calc
        self.recovery = recovery_system
    
    async def execute_async(self, coroutine, operation_name):
        last_error = None
        
        for attempt in range(1, self.retry_calc.max_retries + 1):
            try:
                result = await coroutine
                if self.recovery and hasattr(self.recovery, 'reset_counter'):
                    self.recovery.reset_counter()
                return result
                
            except Exception as e:
                last_error = e
                error_type = self.classifier.classify(e)
                logger.warning(f"Tentativa {attempt}/{self.retry_calc.max_retries} falhou: {operation_name} - {error_type}")
                
                if attempt == self.retry_calc.max_retries or not self.classifier.should_retry(error_type):
                    if self.recovery and hasattr(self.recovery, 'record_failure'):
                        self.recovery.record_failure(f"{operation_name}: {error_type}")
                    raise e
                
                delay = self.retry_calc.get_delay(attempt)
                logger.debug(f"Aguardando {delay}s antes da próxima tentativa...")
                await asyncio.sleep(delay)
        
        raise last_error or Exception("Max retries exceeded")

class ErrorHandler:
    def __init__(self, recovery_system=None, max_retries=3):
        classifier = ErrorClassifier()
        retry_calc = RetryCalculator(max_retries)
        self.executor = OperationExecutor(classifier, retry_calc, recovery_system)
    
    async def execute_with_retry(self, coroutine, operation_name="Operation"):
        return await self.executor.execute_async(coroutine, operation_name)