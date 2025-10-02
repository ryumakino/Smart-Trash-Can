# utils.py - Utilitários comuns para todo o sistema
import time

# Cache de loggers para reutilização
_logger_cache = {}

def get_logger(name):
    """Obter logger reutilizável (simulação para MicroPython)"""
    if name not in _logger_cache:
        _logger_cache[name] = _SimulatedLogger(name)
    return _logger_cache[name]

class _SimulatedLogger:
    """Logger simulado para MicroPython"""
    
    def __init__(self, name):
        self.name = name
    
    def debug(self, msg):
        print(f"[DEBUG][{self.name}] {msg}")
    
    def info(self, msg):
        print(f"[INFO][{self.name}] {msg}")
    
    def warning(self, msg):
        print(f"[WARN][{self.name}] {msg}")
    
    def error(self, msg):
        print(f"[ERROR][{self.name}] {msg}")
    
    def success(self, msg):
        print(f"[SUCCESS][{self.name}] {msg}")

def format_duration(seconds):
    """Formatar duração em segundos para string legível"""
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        return f"{seconds/60:.1f}m"
    else:
        return f"{seconds/3600:.1f}h"

def retry_on_exception(func, max_retries=3, delay=1, exceptions=(Exception,)):
    """Decorator para retry em caso de exceção"""
    def wrapper(*args, **kwargs):
        for attempt in range(max_retries):
            try:
                return func(*args, **kwargs)
            except exceptions as e:
                if attempt == max_retries - 1:
                    raise e
                time.sleep(delay)
    return wrapper

class Timer:
    """Utilitário para medição de tempo"""
    
    def __init__(self):
        self.start_time = None
        self.end_time = None
    
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