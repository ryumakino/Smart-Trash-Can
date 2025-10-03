# src/core/service_factory.py - Factory centralizada (Simplificado)
from typing import Dict, Type

class ServiceFactory:
    """Factory para criação e gerenciamento de serviços"""
    
    _services: Dict[str, object] = {}  # Usar object em vez de BaseService para evitar import
    _service_registry: Dict[str, Type] = {}
    
    @classmethod
    def register_service(cls, name: str, service_class: Type):
        """Registrar uma classe de serviço"""
        cls._service_registry[name] = service_class
    
    @classmethod
    def create_service(cls, name: str, *args, **kwargs):
        """Criar instância de serviço"""
        if name not in cls._service_registry:
            raise ValueError(f"Serviço não registrado: {name}")
        
        if name not in cls._services:
            service_class = cls._service_registry[name]
            cls._services[name] = service_class(*args, **kwargs)
        
        return cls._services[name]
    
    @classmethod
    def get_service(cls, name: str):
        """Obter serviço existente"""
        if name not in cls._services:
            # Tentar criar se não existir
            return cls.create_service(name)
        return cls._services[name]
    
    @classmethod
    def initialize_all(cls):
        """Inicializar todos os serviços registrados"""
        for name, service in cls._services.items():
            if hasattr(service, '_initialized') and not service._initialized:
                if hasattr(service, 'initialize'):
                    service.initialize()
    
    @classmethod
    def cleanup_all(cls):
        """Limpar todos os serviços"""
        for name, service in cls._services.items():
            if hasattr(service, '_initialized') and service._initialized:
                if hasattr(service, 'cleanup'):
                    service.cleanup()
        cls._services.clear()