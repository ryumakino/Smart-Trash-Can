# utils.py - Utilitários
from datetime import datetime
import sys

class Logger:
    def __init__(self, name="System"):
        self.name = name
        self.colors = {
            'INFO': '\033[94m',      # Azul
            'SUCCESS': '\033[92m',   # Verde  
            'WARNING': '\033[93m',   # Amarelo
            'ERROR': '\033[91m',     # Vermelho
            'DEBUG': '\033[90m',     # Cinza
            'CAMERA': '\033[95m',    # Magenta
            'RESET': '\033[0m'       # Reset
        }
        self.use_colors = sys.stdout.isatty()
    
    def _format_message(self, level, message):
        """Formata a mensagem com timestamp e cores"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        if self.use_colors and level in self.colors:
            level_display = f"{self.colors[level]}[{level}]{self.colors['RESET']}"
            name_display = f"{self.colors['DEBUG']}[{self.name}]{self.colors['RESET']}"
        else:
            level_display = f"[{level}]"
            name_display = f"[{self.name}]"
        
        return f"[{timestamp}] {name_display} {level_display} {message}"
    
    def info(self, message):
        """Log nível INFO"""
        print(self._format_message("INFO", message))
        sys.stdout.flush()
    
    def error(self, message):
        """Log nível ERROR"""
        print(self._format_message("ERROR", message))
        sys.stdout.flush()
    
    def warning(self, message):
        """Log nível WARNING"""
        print(self._format_message("WARNING", message))
        sys.stdout.flush()
    
    def success(self, message):
        """Log nível SUCCESS"""
        print(self._format_message("SUCCESS", message))
        sys.stdout.flush()
    
    def debug(self, message):
        """Log nível DEBUG"""
        print(self._format_message("DEBUG", message))
        sys.stdout.flush()

# Cache de loggers
_loggers = {}

def get_logger(name="System"):
    """Retorna uma instância de Logger para o nome especificado"""
    if name not in _loggers:
        _loggers[name] = Logger(name)
    return _loggers[name]