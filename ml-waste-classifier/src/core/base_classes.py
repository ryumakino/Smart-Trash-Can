from abc import ABC, abstractmethod
import logging
from typing import Any, Dict

class Observable:
    """Implementa o padrão Observer para notificações"""
    
    def __init__(self):
        self._observers = []
    
    def add_observer(self, observer):
        if observer not in self._observers:
            self._observers.append(observer)
    
    def remove_observer(self, observer):
        if observer in self._observers:
            self._observers.remove(observer)
    
    def notify_observers(self, event: str, data: Any = None):
        for observer in self._observers:
            observer.on_event(event, data)

class BaseService(ABC, Observable):
    """Classe base para todos os serviços usando Template Method pattern"""
    
    def __init__(self, name: str):
        super().__init__()
        self.name = name
        self._initialized = False
        self._setup_logger()
    
    def _setup_logger(self):
        self.logger = logging.getLogger(self.name)
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s | %(name)s | %(levelname)s | %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)
    
    def initialize(self) -> bool:
        """Template method para inicialização"""
        if self._initialized:
            return True
        
        try:
            if self._initialize_impl():
                self._initialized = True
                self.logger.info(f"✅ {self.name} inicializado com sucesso")
                self.notify_observers("service_initialized", self.name)
                return True
        except Exception as e:
            self.logger.error(f"❌ Erro na inicialização de {self.name}: {e}")
        
        return False
    
    @abstractmethod
    def _initialize_impl(self) -> bool:
        """Implementação específica da inicialização"""
        pass
    
    def cleanup(self):
        """Template method para limpeza"""
        if self._initialized:
            self._cleanup_impl()
            self._initialized = False
            self.logger.info(f"🛑 {self.name} finalizado")
    
    @abstractmethod
    def _cleanup_impl(self):
        """Implementação específica da limpeza"""
        pass
    
    @property
    def is_initialized(self) -> bool:
        return self._initialized
    
    def get_status(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "initialized": self._initialized,
            "status": "operational" if self._initialized else "stopped"
        }