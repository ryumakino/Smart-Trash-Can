# utils_refactored.py – DRY + SOLID
import logging, sys, os
from datetime import datetime

try:
    from src.config import CONFIG_MANAGER
except ImportError:
    try:
        from config_manager import CONFIG_MANAGER
    except ImportError:
        CONFIG_MANAGER = None

_logger_cache: dict[str, logging.Logger] = {}

def get_logger(name: str = "System") -> logging.Logger:
    if name in _logger_cache:
        return _logger_cache[name]
    if CONFIG_MANAGER is None:
        return _create_basic_logger(name)
    try:
        sys_cfg = CONFIG_MANAGER.get_system_config()
        log_level = sys_cfg.get("LOG_LEVEL", "INFO").upper()
        logs_dir = sys_cfg.get("LOGS_DIR", "logs")
        os.makedirs(logs_dir, exist_ok=True)

        logger = logging.getLogger(name)
        if logger.handlers:
            _logger_cache[name] = logger
            return logger

        logger.setLevel(getattr(logging, log_level, logging.INFO))
        logger.propagate = False

        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(_ColoredFormatter(
            '[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        ))
        logger.addHandler(console_handler)

        file_handler = logging.FileHandler(
            f"{logs_dir}/server_{datetime.now().strftime('%Y%m%d')}.log",
            encoding='utf-8'
        )
        file_handler.setFormatter(logging.Formatter(
            '[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        ))
        logger.addHandler(file_handler)

        logging.addLevelName(25, "SUCCESS")
        logging.Logger.success = lambda self, message, *args, **kwargs: self._log(25, message, args, **kwargs)

        _logger_cache[name] = logger
        return logger
    except Exception as e:
        print(f"❌ Erro ao criar logger configurado: {e}")
        return _create_basic_logger(name)

def _create_basic_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter(
            '[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        ))
        logger.addHandler(handler)
        logging.addLevelName(25, "SUCCESS")
        logging.Logger.success = lambda self, message, *args, **kwargs: self._log(25, message, args, **kwargs)
    return logger

class _ColoredFormatter(logging.Formatter):
    COLORS = {
        'DEBUG': '\033[90m', 'INFO': '\033[94m', 'WARNING': '\033[93m',
        'ERROR': '\033[91m', 'CRITICAL': '\033[91m', 'SUCCESS': '\033[92m', 'RESET': '\033[0m'
    }

    def format(self, record):
        formatted = super().format(record)
        if sys.stdout.isatty() and record.levelname in self.COLORS:
            return f"{self.COLORS[record.levelname]}{formatted}{self.COLORS['RESET']}"
        return formatted

def validate_config() -> bool:
    if CONFIG_MANAGER is None:
        raise ValueError("ConfigManager não disponível")
    cfg = CONFIG_MANAGER.get_all_config()
    for section in ("ServerConfig", "NetworkConfig", "DeviceConfig", "TrashNetConfig"):
        if section not in cfg:
            raise ValueError(f"Seção obrigatória ausente: {section}")
    if not cfg.get("NetworkConfig", {}).get("AUTH_KEY"):
        raise ValueError("AUTH_KEY não configurada")
    if not cfg.get("TrashNetConfig", {}).get("SYSTEM_CLASSES"):
        raise ValueError("SYSTEM_CLASSES não configurada")
    return True

def setup_environment() -> bool:
    try:
        if CONFIG_MANAGER is None:
            print("ConfigManager não disponível, usando configurações padrão")
            return True
        validate_config()
        sys_cfg = CONFIG_MANAGER.get_system_config()
        for directory in (
            sys_cfg.get("DATA_DIR", "data"),
            sys_cfg.get("MODELS_DIR", "models"),
            sys_cfg.get("LOGS_DIR", "logs"),
            sys_cfg.get("TEST_IMAGES_DIR", "test_images"),
            sys_cfg.get("TEMPLATES_DIR", "templates"),
        ):
            os.makedirs(directory, exist_ok=True)
        return True
    except Exception as e:
        print(f"Erro na configuração do ambiente: {e}")
        return False

def get_system_info() -> dict:
    if CONFIG_MANAGER is None:
        return {
            'error': 'ConfigManager não disponível',
            'directories': {
                'data': 'data', 'models': 'models', 'logs': 'logs',
                'test_images': 'test_images', 'templates': 'templates'
            }
        }
    sys_cfg = CONFIG_MANAGER.get_system_config()
    trash_cfg = CONFIG_MANAGER.get_trashnet_config()
    return {
        'directories': {
            'data': sys_cfg.get("DATA_DIR", "data"),
            'models': sys_cfg.get("MODELS_DIR", "models"),
            'logs': sys_cfg.get("LOGS_DIR", "logs"),
            'test_images': sys_cfg.get("TEST_IMAGES_DIR", "test_images"),
            'templates': sys_cfg.get("TEMPLATES_DIR", "templates"),
        },
        'trashnet': {
            'system_classes': trash_cfg.get("SYSTEM_CLASSES", []),
            'model_path': trash_cfg.get("MODEL_WEIGHTS_PATH", ""),
            'confidence_threshold': trash_cfg.get("CONFIDENCE_THRESHOLD", 0.6),
            'use_fallback': trash_cfg.get("USE_FALLBACK", True),
        },
        'logging': {
            'level': sys_cfg.get("LOG_LEVEL", "INFO"),
            'log_file': f"logs/server_{datetime.now().strftime('%Y%m%d')}.log"
        }
    }

if __name__ != "__main__":
    setup_environment()