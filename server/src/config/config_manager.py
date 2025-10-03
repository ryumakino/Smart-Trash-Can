# src/config/config_manager.py - Gerenciador de configuração independente
import json
import os
import logging

class ConfigManager:
    """Gerenciador de configuração sem dependências circulares"""
    
    def __init__(self, config_path="config.json"):
        self.config_path = config_path
        self._setup_basic_logging()  # PRIMEIRO configurar o logger
        self.config = self._load_config()  # DEPOIS carregar configuração
    
    def _setup_basic_logging(self):
        """Configurar logging básico para o config manager"""
        # Criar logger específico para ConfigManager
        self.logger = logging.getLogger("ConfigManager")
        
        # Só adicionar handler se não existir
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s | %(name)s | %(levelname)s | %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)
            self.logger.propagate = False
    
    def _load_config(self):
        """Carregar configuração do arquivo JSON"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            self.logger.info("Configuração carregada com sucesso")
            return config
        except Exception as e:
            self.logger.error(f"Erro ao carregar configuração: {e}")
            return self._get_default_config()
    
    def _get_default_config(self):
        """Configuração padrão de fallback"""
        self.logger.warning("Usando configuração padrão")
        return {
            "ServerConfig": {
                "HOST": "0.0.0.0",
                "PORT": 5000,
                "DEBUG": False,
                "SECRET_KEY": "trashnet_server_secret_2024"
            },
            "NetworkConfig": {
                "UDP_PORT": 8888,
                "UDP_BUFFER_SIZE": 1024,
                "UDP_SOCKET_TIMEOUT": 1.0,
                "AUTH_KEY": "TR4SH_4I_S3CUR3_K3Y_2024_M4K3DC_D3C0747387",
                "TOKEN_TIMEOUT": 30,
                "BROADCAST_PORT": 8889,
                "HEARTBEAT_INTERVAL": 60,
                "DEVICE_DISCOVERY_INTERVAL": 30
            },
            "DeviceConfig": {
                "MAX_DEVICES": 50,
                "DEVICE_TIMEOUT": 300,
                "AUTO_DISCOVERY": True
            },
            "CameraConfig": {
                "CAMERA_INDEX": 0,
                "CAPTURE_WIDTH": 640,
                "CAPTURE_HEIGHT": 480,
                "CAMERA_WARMUP_ATTEMPTS": 5,
                "CAMERA_WARMUP_DELAY": 0.5,
                "MAX_CAMERA_INDEX": 3
            },
            "TrashNetConfig": {
                "ORIGINAL_CLASSES": ["cardboard", "glass", "metal", "paper", "plastic", "trash"],
                "CLASS_MAPPING": {
                    "cardboard": "PAPELAO",
                    "glass": "VIDRO",
                    "metal": "METAL",
                    "paper": "PAPEL",
                    "plastic": "PLASTICO",
                    "trash": "LIXO"
                },
                "SYSTEM_CLASSES": ["PLASTICO", "PAPEL", "VIDRO", "METAL", "LIXO", "PAPELAO"],
                "MODEL_WEIGHTS_PATH": "models/trashnet_model.h5",
                "MODEL_INPUT_SIZE": [224, 224],
                "CONFIDENCE_THRESHOLD": 0.6,
                "USE_FALLBACK": True
            },
            "SystemConfig": {
                "DATA_DIR": "data",
                "MODELS_DIR": "models",
                "LOGS_DIR": "logs",
                "TEST_IMAGES_DIR": "test_images",
                "TEMPLATES_DIR": "templates",
                "HEARTBEAT_INTERVAL": 30,
                "MAX_RETRY_ATTEMPTS": 3,
                "LOG_LEVEL": "INFO"
            }
        }
    
    def get_server_config(self):
        return self.config.get("ServerConfig", {})
    
    def get_network_config(self):
        return self.config.get("NetworkConfig", {})
    
    def get_device_config(self):
        return self.config.get("DeviceConfig", {})
    
    def get_camera_config(self):
        return self.config.get("CameraConfig", {})
    
    def get_trashnet_config(self):
        return self.config.get("TrashNetConfig", {})
    
    def get_system_config(self):
        return self.config.get("SystemConfig", {})
    
    def get_all_config(self):
        return self.config
    
    def update_config(self, new_config):
        """Atualizar configuração e salvar no arquivo"""
        try:
            self.config = new_config
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(new_config, f, indent=2, ensure_ascii=False)
            self.logger.info("Configuração atualizada e salva")
            return True
        except Exception as e:
            self.logger.error(f"Erro ao salvar configuração: {e}")
            return False

# Instância global - AGORA SEM DEPENDÊNCIAS CIRCULARES
CONFIG_MANAGER = ConfigManager()