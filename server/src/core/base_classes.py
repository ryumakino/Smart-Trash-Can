# base_classes_refactored.py – DRY + SOLID
import json, logging
from abc import ABC, abstractmethod

class BaseService(ABC):
    def __init__(self, config_section: str | None = None):
        self._config_manager = None
        self._config: dict = {}
        self._logger: logging.Logger | None = None
        self._initialized = False
        self._config_section = config_section
        self._setup_basic_logger()

    # ---------- lifecycle ---------- #
    def initialize(self) -> bool:
        if not self._initialized:
            self._initialized = True
            self.logger.info(f"✅ {self.__class__.__name__} inicializado")
        return True

    def cleanup(self):
        self._initialized = False
        if self._logger:
            self._logger.info(f"{self.__class__.__name__} cleanup completed")

    # ---------- configuration ---------- #
    def set_config_manager(self, manager):
        self._config_manager = manager
        if self._config_section:
            method = getattr(self._config_manager, f"get_{self._config_section.lower()}_config", None)
            if method:
                self._config = method()
                self.logger.debug(f"✅ Configuração '{self._config_section}' carregada")

    def set_config_section(self, section: str):
        self._config_section = section
        if self._config_manager:
            self.set_config_manager(self._config_manager)

    # ---------- logging ---------- #
    def _setup_basic_logger(self):
        self._logger = logging.getLogger(self.__class__.__name__)
        if not self._logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter(
                '%(asctime)s | %(name)s | %(levelname)s | %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            ))
            self._logger.addHandler(handler)
            self._logger.setLevel(logging.INFO)
            self._logger.propagate = False

    def setup_logger(self):
        try:
            from src.utils.utils import get_logger
            self._logger = get_logger(self.__class__.__name__)
        except ImportError:
            pass

    @property
    def logger(self) -> logging.Logger:
        return self._logger

    @property
    def config(self) -> dict:
        return self._config

    @property
    def is_initialized(self) -> bool:
        return self._initialized

    # ---------- status ---------- #
    def get_status(self) -> dict:
        return {
            'initialized': self._initialized,
            'service_name': self.__class__.__name__,
            'config_section': self._config_section,
            'timestamp': __import__('datetime').datetime.now().isoformat()
        }

class ConfigurableMixin:
    def get_config_value(self, key: str, default=None, config_section: str | None = None):
        section = config_section or getattr(self, '_config_section', None)
        cfg = self._config
        if section and hasattr(self, '_config_manager') and self._config_manager:
            method = getattr(self._config_manager, f"get_{section.lower()}_config", None)
            if method:
                cfg = method()
        return cfg.get(key, default)

class MessageHandlerMixin:
    def handle_message_pattern(self, msg: str, addr: tuple[str, int], patterns: dict) -> any:
        for pattern, handler in patterns.items():
            if msg.startswith(pattern):
                return handler(msg, pattern, addr)
        return None

    def extract_json_payload(self, msg: str, prefix: str) -> dict | None:
        try:
            return json.loads(msg.split(prefix, 1)[1])
        except (json.JSONDecodeError, IndexError, ValueError) as e:
            if hasattr(self, 'logger'):
                self.logger.error(f"Erro ao extrair JSON de '{prefix}': {e}")
            return None