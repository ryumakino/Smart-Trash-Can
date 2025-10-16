# utils/utils.py - UTILITÁRIOS ESSENCIAIS
import uasyncio as asyncio
import time

class Logger:
    """Logger otimizado para o sistema"""
    
    def __init__(self, name):
        self.name = name
    
    def _log(self, level, message):
        """Método de log centralizado"""
        timestamp = time.time()
        print(f"[{level}][{self.name}][{timestamp:.0f}] {message}")
    
    def debug(self, message): self._log("DEBUG", message)
    def info(self, message): self._log("INFO", message)
    def warning(self, message): self._log("WARN", message)
    def error(self, message): self._log("ERROR", message)
    def success(self, message): self._log("SUCCESS", message)

# Cache de loggers
_loggers = {}

def get_logger(name):
    """Factory para loggers com cache"""
    if name not in _loggers:
        _loggers[name] = Logger(name)
    return _loggers[name]

async def safe_async(coro):
    """Decorator para operações assíncronas seguras"""
    async def wrapper(*args, **kwargs):
        try:
            return await coro(*args, **kwargs)
        except Exception as e:
            get_logger("SafeAsync").error(f"Erro em {coro.__name__}: {e}")
            return None
    return wrapper

async def async_timer(interval, callback, name="Timer"):
    """Timer assíncrono para agendamento"""
    logger = get_logger(f"Timer.{name}")
    logger.info(f"Iniciando timer (intervalo: {interval}s)")
    
    while True:
        try:
            await callback()
        except Exception as e:
            logger.error(f"Erro no callback: {e}")
        await asyncio.sleep(interval)

def format_duration(seconds):
    """Formata duração em segundos para string legível"""
    if seconds < 60:
        return f"{seconds:.0f}s"
    elif seconds < 3600:
        return f"{seconds/60:.1f}m"
    else:
        return f"{seconds/3600:.1f}h"
    