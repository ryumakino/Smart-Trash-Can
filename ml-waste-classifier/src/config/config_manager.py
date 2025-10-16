import json
import os
import logging
from typing import Dict, Any

class ConfigManager:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self, config_path: str = "config.json"):
        if not hasattr(self, '_initialized'):
            self.config_path = config_path
            self._setup_logging()
            self.config = self._load_config()
            self._initialized = True
    
    def _setup_logging(self):
        self.logger = logging.getLogger("ConfigManager")
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s | %(name)s | %(levelname)s | %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)
    
    def _load_config(self) -> Dict[str, Any]:
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            self.logger.error(f"Erro ao carregar configuração: {e}")
            return self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        return {
            "MQTTConfig": {
                "BROKER_HOST": "localhost", 
                "BROKER_PORT": 1883,
                "TOPIC_PREFIX": "trashnet"
            },
            "CameraConfig": {
                "CAMERA_INDEX": 0,
                "CAPTURE_WIDTH": 640,
                "CAPTURE_HEIGHT": 480
            },
            "TrashNetConfig": {
                "MODEL_WEIGHTS_PATH": "models/trashnet_model.h5",
                "CONFIDENCE_THRESHOLD": 0.6
            },
            "SystemConfig": {
                "LOG_LEVEL": "INFO"
            }
        }
    
    def get_mqtt_config(self) -> Dict[str, Any]:
        return self.config.get("MQTTConfig", {})
    
    def get_camera_config(self) -> Dict[str, Any]:
        return self.config.get("CameraConfig", {})
    
    def get_trashnet_config(self) -> Dict[str, Any]:
        return self.config.get("TrashNetConfig", {})
    
    def get_system_config(self) -> Dict[str, Any]:
        return self.config.get("SystemConfig", {})

CONFIG_MANAGER = ConfigManager()