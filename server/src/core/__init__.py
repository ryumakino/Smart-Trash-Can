"""
Módulo Core - Núcleo do sistema TrashNet
"""

from src.core.base_classes import BaseService, ConfigurableMixin, MessageHandlerMixin
from src.core.service_factory import ServiceFactory
from src.core.app_config import (
    initialize_system,
    get_device_registry,
    get_camera_manager, 
    get_server_communicator,
    get_classification_service,
    get_web_dashboard,
    get_trash_net_server,
    SERVER_CONFIG,
    NETWORK_CONFIG,
    DEVICE_CONFIG,
    CAMERA_CONFIG,
    TRASHNET_CONFIG, 
    SYSTEM_CONFIG
)

# Exportar main_server também
from src.services.main_server import TrashNetServer

__all__ = [
    # Classes Base
    'BaseService',
    'ConfigurableMixin', 
    'MessageHandlerMixin',
    
    # Servidor Principal
    'TrashNetServer',
    
    # Factory
    'ServiceFactory',
    
    # Funções de Acesso
    'initialize_system',
    'get_device_registry',
    'get_camera_manager',
    'get_server_communicator', 
    'get_classification_service',
    'get_web_dashboard',
    'get_trash_net_server',
    
    # Configurações
    'SERVER_CONFIG',
    'NETWORK_CONFIG',
    'DEVICE_CONFIG',
    'CAMERA_CONFIG',
    'TRASHNET_CONFIG',
    'SYSTEM_CONFIG',
]