# src/core/app_config.py - Configuração centralizada (Atualizado)
from src.config.config_manager import CONFIG_MANAGER
from src.core.service_factory import ServiceFactory

# Configurações globais
SERVER_CONFIG = CONFIG_MANAGER.get_server_config()
NETWORK_CONFIG = CONFIG_MANAGER.get_network_config()
DEVICE_CONFIG = CONFIG_MANAGER.get_device_config()
CAMERA_CONFIG = CONFIG_MANAGER.get_camera_config()
TRASHNET_CONFIG = CONFIG_MANAGER.get_trashnet_config()
SYSTEM_CONFIG = CONFIG_MANAGER.get_system_config()

def initialize_system():
    """Inicializar todo o sistema"""
    # Usar logger básico inicialmente
    import logging
    logger = logging.getLogger("AppConfig")
    logger.info("Inicializando sistema TrashNet...")
    
    try:
        # Configurar ambiente
        from src.utils.utils import setup_environment
        if not setup_environment():
            return False
        
        # Garantir que todos os serviços estão registrados
        _ensure_services_registered()
        
        # Configurar ConfigManager em todos os serviços
        _configure_services()
        
        # Inicializar serviços via factory
        ServiceFactory.initialize_all()
        
        # Agora usar logger avançado se disponível
        try:
            from src.utils.utils import get_logger
            advanced_logger = get_logger("AppConfig")
            advanced_logger.success("Sistema inicializado com sucesso")
        except:
            logger.info("Sistema inicializado com sucesso")
        
        return True
        
    except Exception as e:
        logger.error(f"Erro na inicialização do sistema: {e}")
        return False

def _ensure_services_registered():
    """Garantir que todos os serviços estão registrados"""
    # Importar módulos para garantir registro
    try:
        import src.services
        import src.ai
        import src.web
    except ImportError as e:
        import logging
        logging.getLogger("AppConfig").error(f"Erro ao registrar serviços: {e}")

def _configure_services():
    """Configurar ConfigManager em todos os serviços BaseService"""
    import logging
    logger = logging.getLogger("AppConfig")
    
    for service_name, service in ServiceFactory._services.items():
        if hasattr(service, 'set_config_manager'):
            service.set_config_manager(CONFIG_MANAGER)
            logger.debug(f"ConfigManager configurado em {service_name}")

# Funções de acesso rápido
def get_device_registry():
    return ServiceFactory.get_service('device_registry')

def get_camera_manager():
    return ServiceFactory.get_service('camera_manager')

def get_server_communicator():
    return ServiceFactory.get_service('server_communicator')

def get_classification_service():
    return ServiceFactory.get_service('classification_service')

def get_security_manager():
    return ServiceFactory.get_service('security_manager')

def get_database():
    return ServiceFactory.get_service('database')

def get_web_dashboard():
    return ServiceFactory.get_service('web_dashboard')

def get_trash_net_server():
    """Obter instância do servidor principal"""
    from src.services.main_server import TrashNetServer
    return TrashNetServer()