# app_config_refactored.py – DRY + SOLID
from src.config.config_manager import CONFIG_MANAGER
from src.core.service_factory import ServiceFactory

# ---------- config shortcuts ---------- #
SERVER_CONFIG = CONFIG_MANAGER.get_server_config()
NETWORK_CONFIG = CONFIG_MANAGER.get_network_config()
DEVICE_CONFIG = CONFIG_MANAGER.get_device_config()
CAMERA_CONFIG = CONFIG_MANAGER.get_camera_config()
TRASHNET_CONFIG = CONFIG_MANAGER.get_trashnet_config()
SYSTEM_CONFIG = CONFIG_MANAGER.get_system_config()

# ---------- initialization ---------- #
def initialize_system() -> bool:
    import logging
    logger = logging.getLogger("AppConfig")
    logger.info("Inicializando sistema TrashNet...")
    try:
        from src.utils.utils import setup_environment
        if not setup_environment():
            return False
        _ensure_services_registered()
        _configure_services()
        ServiceFactory.initialize_all()
        try:
            from src.utils.utils import get_logger
            get_logger("AppConfig").success("Sistema inicializado com sucesso")
        except:
            logger.info("Sistema inicializado com sucesso")
        return True
    except Exception as e:
        logger.error(f"Erro na inicialização do sistema: {e}")
        return False

def _ensure_services_registered():
    try:
        import src.services, src.ai, src.web
    except ImportError as e:
        import logging
        logging.getLogger("AppConfig").error(f"Erro ao registrar serviços: {e}")

def _configure_services():
    import logging
    logger = logging.getLogger("AppConfig")
    for name, service in ServiceFactory._services.items():
        if hasattr(service, 'set_config_manager'):
            service.set_config_manager(CONFIG_MANAGER)
            logger.debug(f"ConfigManager configurado em {name}")

# ---------- service accessors ---------- #
def get_device_registry(): return ServiceFactory.get_service('device_registry')
def get_camera_manager(): return ServiceFactory.get_service('camera_manager')
def get_server_communicator(): return ServiceFactory.get_service('server_communicator')
def get_classification_service(): return ServiceFactory.get_service('classification_service')
def get_security_manager(): return ServiceFactory.get_service('security_manager')
def get_database(): return ServiceFactory.get_service('database')
def get_web_dashboard(): return ServiceFactory.get_service('web_dashboard') 
def get_web_dashboard(): return ServiceFactory.get_service('web_dashboard')
def get_trashnet_model(): return ServiceFactory.get_service('trashnet_model')

def get_trash_net_server():
    from src.services.main_server import TrashNetServer
    return TrashNetServer()