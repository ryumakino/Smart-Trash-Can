# config_manager.py - Gerenciador de configurações do servidor
import json
import os
from utils import get_logger

logger = get_logger("ConfigManager")

class ConfigManager:
    def __init__(self, filename='config.json'):
        self.filename = filename
        self.config = {}
        
    def load_config(self):
        """Carregar configurações do arquivo JSON"""
        try:
            if os.path.exists(self.filename):
                with open(self.filename, 'r') as f:
                    self.config = json.load(f)
                    logger.info("Configurações do servidor carregadas")
                    return self.config
            else:
                logger.error("Arquivo de configuração não encontrado")
                return {}
        except Exception as e:
            logger.error(f"Erro ao carregar configurações: {e}")
            return {}
    
    def get_server_config(self):
        return self.config.get('ServerConfig', {})
    
    def get_network_config(self):
        return self.config.get('NetworkConfig', {})
    
    def get_device_config(self):
        return self.config.get('DeviceConfig', {})
    
    def get_camera_config(self):
        return self.config.get('CameraConfig', {})
    
    def get_trashnet_config(self):
        return self.config.get('TrashNetConfig', {})
    
    def get_system_config(self):
        return self.config.get('SystemConfig', {})
    
    def save_config(self, config_dict):
        """Salvar configurações no arquivo"""
        try:
            with open(self.filename, 'w') as f:
                json.dump(config_dict, f, indent=2)
            logger.info("Configurações salvas com sucesso")
            return True
        except Exception as e:
            logger.error(f"Erro ao salvar configurações: {e}")
            return False

# Instância global
CONFIG_MANAGER = ConfigManager()