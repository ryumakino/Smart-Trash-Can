# error_handler.py - Tratamento robusto de erros
import uasyncio as asyncio
from utils import get_logger

logger = get_logger("ErrorHandler")

class ErrorHandler:
    def __init__(self, recovery_system):
        self.recovery = recovery_system
        
    async def safe_execute(self, coroutine, operation_name="Unknown", max_retries=3):
        """Executar coroutine com tratamento de erro seguro"""
        for attempt in range(max_retries):
            try:
                result = await coroutine
                self.recovery.reset_counter()  # Reset em caso de sucesso
                return result
                
            except asyncio.CancelledError:
                logger.info(f"Operation cancelled: {operation_name}")
                raise  # Re-raise cancelled errors
                
            except Exception as e:
                logger.error(f"Attempt {attempt + 1} failed for {operation_name}: {e}")
                
                if attempt == max_retries - 1:  # Última tentativa
                    self.recovery.record_failure(f"{operation_name}: {str(e)}")
                    return None
                    
                await asyncio.sleep(1 * (attempt + 1))  # Backoff exponencial
        
        return None
    
    def wrap_sync_function(self, func, operation_name="Unknown"):
        """Wrapper para funções síncronas"""
        def wrapper(*args, **kwargs):
            try:
                result = func(*args, **kwargs)
                self.recovery.reset_counter()
                return result
            except Exception as e:
                logger.error(f"Sync function failed {operation_name}: {e}")
                self.recovery.record_failure(f"{operation_name}: {str(e)}")
                return None
        return wrapper