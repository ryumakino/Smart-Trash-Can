# utils.py
import time
import uasyncio as asyncio

# Cache de loggers para reutilização - DRY
_logger_cache = {}

class LoggerFactory:
    """SRP: Factory para criação de loggers"""
    
    @staticmethod
    def get_logger(name):
        """Obter logger reutilizável"""
        if name not in _logger_cache:
            _logger_cache[name] = _SimulatedLogger(name)
        return _logger_cache[name]
    
    @staticmethod
    def clear_cache():
        """Limpar cache de loggers"""
        _logger_cache.clear()

class _SimulatedLogger:
    """SRP: Logger simulado para MicroPython"""
    
    def __init__(self, name):
        self.name = name
    
    def _log(self, level, msg):
        """Método base para logging - DRY"""
        print(f"[{level}][{self.name}] {msg}")
    
    def debug(self, msg):
        self._log("DEBUG", msg)
    
    def info(self, msg):
        self._log("INFO", msg)
    
    def warning(self, msg):
        self._log("WARN", msg)
    
    def error(self, msg):
        self._log("ERROR", msg)
    
    def success(self, msg):
        self._log("SUCCESS", msg)

class TimeFormatter:
    """SRP: Formatação de tempo"""
    
    @staticmethod
    def format_duration(seconds):
        """Formatar duração em segundos para string legível"""
        if seconds < 60:
            return f"{seconds:.1f}s"
        elif seconds < 3600:
            return f"{seconds/60:.1f}m"
        else:
            return f"{seconds/3600:.1f}h"
    
    @staticmethod
    def format_timestamp(timestamp):
        """Formatar timestamp para string legível"""
        # Em MicroPython não temos datetime completo,
        # então usamos uma versão simplificada
        hours = int((timestamp % 86400) / 3600)
        minutes = int((timestamp % 3600) / 60)
        seconds = int(timestamp % 60)
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

class RetryDecorator:
    """SRP: Decorator para retry em caso de exceção"""
    
    def __init__(self, max_retries=3, delay=1, exceptions=(Exception,)):
        self.max_retries = max_retries
        self.delay = delay
        self.exceptions = exceptions
    
    def __call__(self, func):
        def sync_wrapper(*args, **kwargs):
            for attempt in range(self.max_retries):
                try:
                    return func(*args, **kwargs)
                except self.exceptions as e:
                    if attempt == self.max_retries - 1:
                        raise e
                    time.sleep(self.delay)
            return None
        
        async def async_wrapper(*args, **kwargs):
            for attempt in range(self.max_retries):
                try:
                    return await func(*args, **kwargs)
                except self.exceptions as e:
                    if attempt == self.max_retries - 1:
                        raise e
                    await asyncio.sleep(self.delay)
            return None
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper

class Timer:
    """SRP: Utilitário para medição de tempo"""
    
    def __init__(self, auto_start=True):
        self.start_time = None
        self.end_time = None
        if auto_start:
            self.start()
    
    def start(self):
        self.start_time = time.time()
        return self
    
    def stop(self):
        self.end_time = time.time()
        return self.elapsed()
    
    def elapsed(self):
        if self.start_time is None:
            return 0
        end = self.end_time or time.time()
        return end - self.start_time
    
    def reset(self):
        self.start_time = time.time()
        self.end_time = None

class DataValidator:
    """SRP: Validação de dados"""
    
    @staticmethod
    def validate_ip_address(ip):
        """Validar endereço IP"""
        if not ip or not isinstance(ip, str):
            return False
        
        parts = ip.split('.')
        if len(parts) != 4:
            return False
        
        for part in parts:
            if not part.isdigit():
                return False
            num = int(part)
            if num < 0 or num > 255:
                return False
        
        return True
    
    @staticmethod
    def validate_port(port):
        """Validar número de porta"""
        return isinstance(port, int) and 1 <= port <= 65535
    
    @staticmethod
    def validate_mac_address(mac):
        """Validar endereço MAC"""
        if not mac or not isinstance(mac, str):
            return False
        
        # Formato: XX:XX:XX:XX:XX:XX ou XXXXXXXXXXXX
        clean_mac = mac.replace(':', '').replace('-', '').upper()
        if len(clean_mac) != 12:
            return False
        
        try:
            int(clean_mac, 16)
            return True
        except ValueError:
            return False

# Funções de conveniência para manter compatibilidade
def get_logger(name):
    return LoggerFactory.get_logger(name)

def format_duration(seconds):
    return TimeFormatter.format_duration(seconds)

def retry_on_exception(func, max_retries=3, delay=1, exceptions=(Exception,)):
    decorator = RetryDecorator(max_retries, delay, exceptions)
    return decorator(func)