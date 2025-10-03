# src/utils/utils.py - Utilitários atualizados
import logging
import sys
import os
from datetime import datetime

# Importação correta dentro da nova estrutura
try:
    from src.config import CONFIG_MANAGER
except ImportError:
    # Fallback para desenvolvimento
    try:
        from config_manager import CONFIG_MANAGER
    except ImportError:
        CONFIG_MANAGER = None

# Cache de loggers
_loggers = {}

def get_logger(name="System"):
    """Retorna uma instância de Logger configurada"""
    if name in _loggers:
        return _loggers[name]
    
    # Se CONFIG_MANAGER não estiver disponível, usar configuração básica
    if CONFIG_MANAGER is None:
        return _create_basic_logger(name)
    
    try:
        # Obter configurações do sistema
        system_config = CONFIG_MANAGER.get_system_config()
        log_level = system_config.get("LOG_LEVEL", "INFO").upper()
        logs_dir = system_config.get("LOGS_DIR", "logs")
        
        # Criar diretório de logs se não existir
        os.makedirs(logs_dir, exist_ok=True)
        
        # Criar logger
        logger = logging.getLogger(name)
        
        # Evitar duplicação de handlers
        if logger.handlers:
            _loggers[name] = logger
            return logger
        
        # Configurar nível do logger
        logger.setLevel(getattr(logging, log_level, logging.INFO))
        logger.propagate = False
        
        # Formatter com cores para console
        class ColorFormatter(logging.Formatter):
            """Formatter com cores para console"""
            COLORS = {
                'DEBUG': '\033[90m',     # Cinza
                'INFO': '\033[94m',      # Azul
                'WARNING': '\033[93m',   # Amarelo
                'ERROR': '\033[91m',     # Vermelho
                'CRITICAL': '\033[91m',  # Vermelho
                'SUCCESS': '\033[92m',   # Verde
                'RESET': '\033[0m'       # Reset
            }
            
            def format(self, record):
                # Formatar mensagem base
                formatted = super().format(record)
                
                # Adicionar cores se for terminal
                if sys.stdout.isatty() and record.levelname in self.COLORS:
                    formatted = f"{self.COLORS[record.levelname]}{formatted}{self.COLORS['RESET']}"
                
                return formatted
        
        # Formatter para arquivo (sem cores)
        file_formatter = logging.Formatter(
            '[%(asctime)s] [%(name)s] [%(levelname)s] [%(message)s]',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # Handler para console
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(ColorFormatter(
            '[%(asctime)s] [%(name)s] [%(levelname)s] [%(message)s]',
            datefmt='%Y-%m-%d %H:%M:%S'
        ))
        logger.addHandler(console_handler)
        
        # Handler para arquivo
        log_filename = f"{logs_dir}/server_{datetime.now().strftime('%Y%m%d')}.log"
        file_handler = logging.FileHandler(log_filename, encoding='utf-8')
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
        
        # Adicionar método success
        def success(self, message, *args, **kwargs):
            if self.isEnabledFor(25):  # Nível personalizado entre INFO e WARNING
                self._log(25, message, args, **kwargs)
        
        logging.addLevelName(25, "SUCCESS")
        logging.Logger.success = success
        
        _loggers[name] = logger
        return logger
        
    except Exception as e:
        print(f"❌ Erro ao criar logger configurado: {e}")
        return _create_basic_logger(name)

def _create_basic_logger(name="System"):
    """Criar logger básico como fallback"""
    logger = logging.getLogger(name)
    
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            '[%(asctime)s] [%(name)s] [%(levelname)s] [%(message)s]',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        
        # Adicionar método success
        def success(self, message, *args, **kwargs):
            if self.isEnabledFor(25):
                self._log(25, message, args, **kwargs)
        
        logging.addLevelName(25, "SUCCESS")
        logging.Logger.success = success
    
    return logger

def validate_config():
    """Validar configuração carregada"""
    if CONFIG_MANAGER is None:
        raise ValueError("ConfigManager não disponível")
    
    config = CONFIG_MANAGER.get_all_config()
    required_sections = ["ServerConfig", "NetworkConfig", "DeviceConfig", "TrashNetConfig"]
    
    for section in required_sections:
        if section not in config:
            raise ValueError(f"Seção de configuração obrigatória ausente: {section}")
    
    # Validar configurações específicas
    network_config = config.get("NetworkConfig", {})
    if not network_config.get("AUTH_KEY"):
        raise ValueError("AUTH_KEY não configurada em NetworkConfig")
    
    trashnet_config = config.get("TrashNetConfig", {})
    if not trashnet_config.get("SYSTEM_CLASSES"):
        raise ValueError("SYSTEM_CLASSES não configurada em TrashNetConfig")
    
    return True

def setup_environment():
    """Configurar ambiente da aplicação"""
    try:
        if CONFIG_MANAGER is None:
            print("ConfigManager não disponível, usando configurações padrão")
            return True
        
        # Validar configuração
        validate_config()
        
        # Configurar diretórios
        system_config = CONFIG_MANAGER.get_system_config()
        directories = [
            system_config.get("DATA_DIR", "data"),
            system_config.get("MODELS_DIR", "models"),
            system_config.get("LOGS_DIR", "logs"),
            system_config.get("TEST_IMAGES_DIR", "test_images"),
            system_config.get("TEMPLATES_DIR", "templates")
        ]
        
        for directory in directories:
            os.makedirs(directory, exist_ok=True)

        return True
        
    except Exception as e:
        print(f"Erro na configuração do ambiente: {e}")
        return False

def get_system_info():
    """Obter informações do sistema"""
    if CONFIG_MANAGER is None:
        return {
            'error': 'ConfigManager não disponível',
            'directories': {
                'data': 'data',
                'models': 'models',
                'logs': 'logs',
                'test_images': 'test_images',
                'templates': 'templates'
            }
        }
    
    system_config = CONFIG_MANAGER.get_system_config()
    trashnet_config = CONFIG_MANAGER.get_trashnet_config()
    
    return {
        'directories': {
            'data': system_config.get("DATA_DIR", "data"),
            'models': system_config.get("MODELS_DIR", "models"),
            'logs': system_config.get("LOGS_DIR", "logs"),
            'test_images': system_config.get("TEST_IMAGES_DIR", "test_images"),
            'templates': system_config.get("TEMPLATES_DIR", "templates")
        },
        'trashnet': {
            'system_classes': trashnet_config.get("SYSTEM_CLASSES", []),
            'model_path': trashnet_config.get("MODEL_WEIGHTS_PATH", ""),
            'confidence_threshold': trashnet_config.get("CONFIDENCE_THRESHOLD", 0.6),
            'use_fallback': trashnet_config.get("USE_FALLBACK", True)
        },
        'logging': {
            'level': system_config.get("LOG_LEVEL", "INFO"),
            'log_file': f"logs/server_{datetime.now().strftime('%Y%m%d')}.log"
        }
    }

# Inicialização automática do ambiente quando o módulo é importado
if __name__ != "__main__":
    setup_environment()