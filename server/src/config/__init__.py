"""
Módulo Config - Configuração do sistema
"""

from src.config.config_manager import ConfigManager, CONFIG_MANAGER

# Registrar config manager na factory
from src.core.service_factory import ServiceFactory

ServiceFactory.register_service('config_manager', ConfigManager)

__all__ = [
    'ConfigManager',
    'CONFIG_MANAGER',
]