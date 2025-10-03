"""
Módulo Web - Interface web do TrashNet
"""

from src.web.web_dashboard import WebDashboard

# Registrar dashboard na factory  
from src.core.service_factory import ServiceFactory

ServiceFactory.register_service('web_dashboard', WebDashboard)

__all__ = [
    'WebDashboard',
]