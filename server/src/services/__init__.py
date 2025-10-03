"""
Módulo Services - Serviços do sistema TrashNet
"""

from src.services.database import ClassificationDB
from src.services.security import SecurityManager
from src.services.device_registry import DeviceRegistry
from src.services.camera_manager import CameraManager
from src.services.classification_service import ClassificationService
from src.services.server_communicator import ServerCommunicator

# Registrar serviços na factory
from src.core.service_factory import ServiceFactory

ServiceFactory.register_service('database', ClassificationDB)
ServiceFactory.register_service('security_manager', SecurityManager)
ServiceFactory.register_service('device_registry', DeviceRegistry)
ServiceFactory.register_service('camera_manager', CameraManager)
ServiceFactory.register_service('classification_service', ClassificationService)
ServiceFactory.register_service('server_communicator', ServerCommunicator)

__all__ = [
    'ClassificationDB',
    'SecurityManager', 
    'DeviceRegistry',
    'CameraManager',
    'ClassificationService',
    'ServerCommunicator',
]