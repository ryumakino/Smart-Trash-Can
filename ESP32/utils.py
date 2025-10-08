# utils.py - CORREÇÕES ADICIONAIS
import time
import uasyncio as asyncio

_logger_cache = {}

class LoggerFactory:
    @staticmethod
    def get_logger(name):
        if name not in _logger_cache:
            _logger_cache[name] = _SimulatedLogger(name)
        return _logger_cache[name]

class _SimulatedLogger:
    def __init__(self, name):
        self.name = name
    
    def _log(self, level, msg):
        # CORREÇÃO: Formatação mais robusta
        try:
            print(f"[{level}][{self.name}] {msg}")
        except:
            print(f"[{level}][{self.name}] [MESSAGE TOO LONG]")
    
    def debug(self, msg): self._log("DEBUG", msg)
    def info(self, msg): self._log("INFO", msg)
    def warning(self, msg): self._log("WARN", msg)
    def error(self, msg): self._log("ERROR", msg)
    def success(self, msg): self._log("SUCCESS", msg)

class MicroPythonQueue:
    def __init__(self, maxsize=0):
        self._queue = []
        self._maxsize = maxsize
        self._event = asyncio.Event()
    
    def put(self, item):
        self._queue.append(item)
        self._event.set()
    
    async def get(self):
        while not self._queue:
            await self._event.wait()
            self._event.clear()
        return self._queue.pop(0)
    
    def empty(self):
        return len(self._queue) == 0
    
    def qsize(self):
        return len(self._queue)

# CORREÇÃO: Aliases para compatibilidade
FileNotFoundError = OSError
Queue = MicroPythonQueue

def get_logger(name):
    return LoggerFactory.get_logger(name)

def format_duration(seconds):
    """Formatação simples de duração"""
    try:
        if seconds < 60:
            return f"{seconds:.1f}s"
        elif seconds < 3600:
            return f"{seconds/60:.1f}m"
        else:
            return f"{seconds/3600:.1f}h"
    except:
        return "0s"