"""
Módulo AI - Inteligência Artificial do TrashNet
"""

from src.ai.trashnet_model import TrashNetModel, load_trashnet_model

# Registrar modelo na factory
from src.core.service_factory import ServiceFactory

ServiceFactory.register_service('trashnet_model', TrashNetModel)

__all__ = [
    'TrashNetModel',
    'load_trashnet_model',
]