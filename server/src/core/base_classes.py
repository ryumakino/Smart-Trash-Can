# src/core/base_classes.py - Classes base corrigidas
import json
from abc import ABC, abstractmethod

class BaseService(ABC):
    """Classe base para todos os serviços com funcionalidades comuns"""
    
    def __init__(self, config_section=None):
        self._config_manager = None
        self._config = {}
        self._logger = None
        self._initialized = False
        self._config_section = config_section  # Armazenar a seção de configuração
        
        # Configurar logger básico inicialmente
        self._setup_basic_logger()
    
    def _setup_basic_logger(self):
        """Configurar logger básico inicial"""
        import logging
        logger_name = self.__class__.__name__
        self._logger = logging.getLogger(logger_name)
        
        # Só configurar se não tiver handlers
        if not self._logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s | %(name)s | %(levelname)s | %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            handler.setFormatter(formatter)
            self._logger.addHandler(handler)
            self._logger.setLevel(logging.INFO)
            self._logger.propagate = False
    
    def initialize(self):
        """Método de inicialização padrão - pode ser sobrescrito"""
        if not self._initialized:
            self._initialized = True
            self.logger.info(f"✅ {self.__class__.__name__} inicializado")
        return True
    
    def set_config_manager(self, config_manager):
        """Injetar ConfigManager após a criação"""
        self._config_manager = config_manager
        # Aplicar configuração se houver uma seção definida
        if self._config_section and self._config_manager:
            config_method = getattr(self._config_manager, f"get_{self._config_section.lower()}_config", None)
            if config_method:
                self._config = config_method()
                self.logger.debug(f"✅ Configuração '{self._config_section}' carregada")
    
    def set_config_section(self, config_section):
        """Configurar seção de configuração (para uso posterior)"""
        self._config_section = config_section
        # Se já tiver config_manager, aplicar imediatamente
        if self._config_manager and config_section:
            config_method = getattr(self._config_manager, f"get_{config_section.lower()}_config", None)
            if config_method:
                self._config = config_method()
    
    def setup_logger(self):
        """Configurar logger apropriado após inicialização"""
        # Esta função pode ser sobrescrita por serviços específicos
        # para usar um logger mais avançado
        try:
            from src.utils.utils import get_logger
            self._logger = get_logger(self.__class__.__name__)
        except ImportError:
            # Manter o logger básico se não conseguir importar
            pass
    
    @property
    def logger(self):
        return self._logger
    
    @property
    def config(self):
        return self._config
    
    @property
    def is_initialized(self):
        return self._initialized
    
    def cleanup(self):
        """Método de limpeza opcional"""
        self._initialized = False
        if self._logger:
            self._logger.info(f"{self.__class__.__name__} cleanup completed")
    
    def get_status(self):
        """Status padrão do serviço"""
        return {
            'initialized': self._initialized,
            'service_name': self.__class__.__name__,
            'config_section': self._config_section,
            'timestamp': __import__('datetime').datetime.now().isoformat()
        }

class ConfigurableMixin:
    """Mixin para acesso padronizado à configuração"""
    
    def get_config_value(self, key, default=None, config_section=None):
        """Obter valor de configuração de forma segura"""
        config = self._config
        
        # Usar seção específica se fornecida, senão usar a seção padrão do serviço
        target_section = config_section or getattr(self, '_config_section', None)
        
        if target_section and hasattr(self, '_config_manager') and self._config_manager:
            config_method = getattr(self._config_manager, f"get_{target_section.lower()}_config", None)
            if config_method:
                config = config_method()
        
        return config.get(key, default)

class MessageHandlerMixin:
    """Mixin para processamento padronizado de mensagens"""
    
    def handle_message_pattern(self, msg, addr, patterns):
        """Processar mensagem baseado em padrões"""
        for pattern, handler in patterns.items():
            if msg.startswith(pattern):
                return handler(msg, pattern, addr)
        return None
    
    def extract_json_payload(self, msg, prefix):
        """Extrair payload JSON de mensagem prefixada"""
        try:
            return json.loads(msg.split(prefix, 1)[1])
        except (json.JSONDecodeError, IndexError, ValueError) as e:
            if hasattr(self, 'logger'):
                self.logger.error(f"Erro ao extrair JSON de '{prefix}': {e}")
            return None