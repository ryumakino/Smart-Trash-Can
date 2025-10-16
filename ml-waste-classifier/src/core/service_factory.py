from typing import Dict, Type
from src.core.base_classes import BaseService

class ServiceFactory:
    """Implementa Singleton e Factory patterns"""
    
    _instance = None
    _services: Dict[str, BaseService] = {}
    _registry: Dict[str, Type[BaseService]] = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    @classmethod
    def register_service(cls, name: str, service_class: Type[BaseService]):
        cls._registry[name] = service_class
    
    @classmethod
    def create_service(cls, name: str) -> BaseService:
        if name not in cls._registry:
            raise ValueError(f"Serviço não registrado: {name}")
        
        if name not in cls._services:
            cls._services[name] = cls._registry[name]()
        
        return cls._services[name]
    
    @classmethod
    def get_service(cls, name: str) -> BaseService:
        return cls._services.get(name)
    
    @classmethod
    def initialize_all(cls):
        for service in cls._services.values():
            if not service.is_initialized:
                service.initialize()
    
    @classmethod
    def cleanup_all(cls):
        for service in cls._services.values():
            if service.is_initialized:
                service.cleanup()
        cls._services.clear()