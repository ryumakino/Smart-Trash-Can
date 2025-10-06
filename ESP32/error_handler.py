# error_handler.py
import uasyncio as asyncio
from utils import get_logger

logger = get_logger("ErrorHandler")

class ErrorClassifier:
    """SRP: Classificar tipos de erro"""
    
    @staticmethod
    def classify_error(error: Exception) -> str:
        """Classificar erro por tipo"""
        error_type = type(error).__name__
        
        if isinstance(error, asyncio.CancelledError):
            return "CANCELLED"
        elif isinstance(error, MemoryError):
            return "MEMORY_ERROR"
        elif isinstance(error, OSError):
            return "NETWORK_ERROR"
        elif isinstance(error, ValueError):
            return "VALUE_ERROR"
        else:
            return "UNKNOWN_ERROR"
    
    @staticmethod
    def should_retry(error_type: str) -> bool:
        """Determinar se o erro é recuperável"""
        non_retryable = ['CANCELLED', 'MEMORY_ERROR']
        return error_type not in non_retryable

class RetryStrategy:
    """SRP: Estratégia de retry com backoff"""
    
    def __init__(self, max_retries=3, base_delay=1, max_delay=30):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
    
    def calculate_delay(self, attempt: int) -> float:
        """Calcular delay com exponential backoff"""
        delay = self.base_delay * (2 ** (attempt - 1))
        return min(delay, self.max_delay)

class OperationResult:
    """SRP: Representar resultado de operação"""
    
    def __init__(self, success: bool, data=None, error=None, attempts=0):
        self.success = success
        self.data = data
        self.error = error
        self.attempts = attempts
    
    def __bool__(self):
        return self.success

class ErrorHandler:
    """Composite: Manipulador de erros principal"""
    
    def __init__(self, recovery_system):
        self.recovery = recovery_system
        self.error_classifier = ErrorClassifier()
        self.retry_strategy = RetryStrategy()
    
    async def execute_with_retry(self, coroutine, operation_name="Unknown", 
                               max_retries=None, allowed_exceptions=(Exception,)):
        """Executar coroutine com retry automático"""
        max_retries = max_retries or self.retry_strategy.max_retries
        
        for attempt in range(1, max_retries + 1):
            try:
                result = await coroutine
                self.recovery.reset_counter()
                return OperationResult(True, result, attempts=attempt)
                
            except asyncio.CancelledError:
                logger.info(f"Operação cancelada: {operation_name}")
                return OperationResult(False, error="CANCELLED", attempts=attempt)
                
            except allowed_exceptions as e:
                error_type = self.error_classifier.classify_error(e)
                logger.error(f"Tentativa {attempt} falhou para {operation_name}: {e}")
                
                if attempt == max_retries or not self.error_classifier.should_retry(error_type):
                    self.recovery.record_failure(f"{operation_name}: {error_type} - {str(e)}")
                    return OperationResult(False, error=str(e), attempts=attempt)
                
                # Esperar antes da próxima tentativa
                delay = self.retry_strategy.calculate_delay(attempt)
                await asyncio.sleep(delay)
        
        return OperationResult(False, error="Max retries exceeded", attempts=max_retries)
    
    def execute_sync_with_retry(self, func, operation_name="Unknown", 
                              max_retries=None, args=None, kwargs=None):
        """Executar função síncrona com retry"""
        args = args or []
        kwargs = kwargs or {}
        max_retries = max_retries or self.retry_strategy.max_retries
        
        for attempt in range(1, max_retries + 1):
            try:
                result = func(*args, **kwargs)
                self.recovery.reset_counter()
                return OperationResult(True, result, attempts=attempt)
                
            except Exception as e:
                error_type = self.error_classifier.classify_error(e)
                logger.error(f"Tentativa {attempt} falhou para {operation_name}: {e}")
                
                if attempt == max_retries or not self.error_classifier.should_retry(error_type):
                    self.recovery.record_failure(f"{operation_name}: {error_type} - {str(e)}")
                    return OperationResult(False, error=str(e), attempts=attempt)
                
                # Esperar antes da próxima tentativa
                import time
                delay = self.retry_strategy.calculate_delay(attempt)
                time.sleep(delay)
        
        return OperationResult(False, error="Max retries exceeded", attempts=max_retries)
    
    def create_async_wrapper(self, operation_name="Unknown", max_retries=None):
        """Criar wrapper para função assíncrona - DRY"""
        def decorator(coroutine_func):
            async def wrapper(*args, **kwargs):
                coroutine = coroutine_func(*args, **kwargs)
                return await self.execute_with_retry(coroutine, operation_name, max_retries)
            return wrapper
        return decorator
    
    def create_sync_wrapper(self, operation_name="Unknown", max_retries=None):
        """Criar wrapper para função síncrona - DRY"""
        def decorator(func):
            def wrapper(*args, **kwargs):
                return self.execute_sync_with_retry(func, operation_name, max_retries, args, kwargs)
            return wrapper
        return decorator

# Aliases para compatibilidade
class SafeExecutor:
    """Facade para compatibilidade com código existente"""
    
    def __init__(self, error_handler):
        self.error_handler = error_handler
    
    async def safe_execute(self, coroutine, operation_name="Unknown", max_retries=3):
        result = await self.error_handler.execute_with_retry(
            coroutine, operation_name, max_retries
        )
        return result.data if result.success else None
    
    def wrap_sync_function(self, func, operation_name="Unknown"):
        @self.error_handler.create_sync_wrapper(operation_name)
        def wrapped(*args, **kwargs):
            return func(*args, **kwargs)
        return wrapped