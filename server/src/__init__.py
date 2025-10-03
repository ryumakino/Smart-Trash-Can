"""
TrashNet Server - Sistema de Classificação Inteligente de Resíduos
"""

__version__ = "1.0.0"
__author__ = "TrashNet Team"
__description__ = "Sistema de classificação de resíduos com ESP32 e IA"

# Importações principais para facilitar o acesso
from src.core.app_config import (
    initialize_system,
    get_device_registry,
    get_camera_manager,
    get_server_communicator,
    get_classification_service,
    get_web_dashboard,
    get_trash_net_server
)

# Configurações globais
from src.core.app_config import (
    SERVER_CONFIG,
    NETWORK_CONFIG, 
    DEVICE_CONFIG,
    CAMERA_CONFIG,
    TRASHNET_CONFIG,
    SYSTEM_CONFIG
)

# Servidor principal
from src.services.main_server import TrashNetServer

__all__ = [
    # Classes
    'TrashNetServer',
    
    # Funções
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