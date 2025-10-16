# service_factory_refactored.py – DRY + SOLID
from typing import Dict, Type

class ServiceFactory:
    _services: Dict[str, object] = {}
    _registry: Dict[str, Type] = {}

    @classmethod
    def register_service(cls, name: str, service_class: Type):
        cls._registry[name] = service_class

    @classmethod
    def create_service(cls, name: str, *args, **kwargs):
        if name not in cls._registry:
            raise ValueError(f"Serviço não registrado: {name}")
        if name not in cls._services:
            cls._services[name] = cls._registry[name](*args, **kwargs)
        return cls._services[name]

    @classmethod
    def get_service(cls, name: str):
        return cls.create_service(name) if name not in cls._services else cls._services[name]

    @classmethod
    def initialize_all(cls):
        for service in cls._services.values():
            if hasattr(service, '_initialized') and not service._initialized and hasattr(service, 'initialize'):
                service.initialize()

    @classmethod
    def cleanup_all(cls):
        for service in cls._services.values():
            if hasattr(service, '_initialized') and service._initialized and hasattr(service, 'cleanup'):
                service.cleanup()
        cls._services.clear()