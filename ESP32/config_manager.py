# config_manager.py - Gerenciamento de configurações persistentes
import ujson as json
import os
from utils import get_logger

logger = get_logger("ConfigManager")

class ConfigManager:
    def __init__(self, filename='config.json'):
        self.filename = filename
        self.config = {}
        self.sections = ['DeviceConfig', 'WiFiConfig', 'NetworkConfig', 'SystemConfig']
        self.load_config()
    
    def load_config(self):
        """Carregar configurações do arquivo JSON"""
        try:
            if self.filename in os.listdir():
                with open(self.filename, 'r') as f:
                    self.config = json.load(f)
                    logger.info("Configuration loaded from JSON file")
                    return self.config
            else:
                logger.error("No config file found - system cannot start without config.json")
                raise FileNotFoundError("config.json not found")
                
        except Exception as e:
            logger.error(f"Error loading config: {e}")
            raise
    
    def _get_section(self, section_name):
        """Método interno reutilizável para obter seções"""
        return self.config.get(section_name, {})
    
    def get_device_config(self):
        return self._get_section('DeviceConfig')
    
    def get_wifi_config(self):
        return self._get_section('WiFiConfig')
    
    def get_network_config(self):
        return self._get_section('NetworkConfig')
    
    def get_system_config(self):
        return self._get_section('SystemConfig')
    
    def save_config(self, config_dict=None):
        """Salvar configurações no arquivo"""
        try:
            config_to_save = config_dict or self.config
            with open(self.filename, 'w') as f:
                json.dump(config_to_save, f, indent=2)
            self.config = config_to_save
            logger.info("Configuration saved successfully")
            return True
        except Exception as e:
            logger.error(f"Error saving config: {e}")
            return False
    
    def update_config_section(self, section, updates):
        """Atualizar uma seção específica da configuração"""
        try:
            if section not in self.config:
                self.config[section] = {}
            
            self.config[section].update(updates)
            return self.save_config()
        except Exception as e:
            logger.error(f"Error updating {section} config: {e}")
            return False
    
    def update_device_config(self, device_config):
        return self.update_config_section('DeviceConfig', device_config)
    
    def update_wifi_config(self, wifi_config):
        return self.update_config_section('WiFiConfig', wifi_config)
    
    def update_network_config(self, network_config):
        return self.update_config_section('NetworkConfig', network_config)
    
    def update_system_config(self, system_config):
        return self.update_config_section('SystemConfig', system_config)
    
    def get_config_value(self, section, key, default=None):
        """Obter valor específico da configuração"""
        section_config = self.config.get(section, {})
        return section_config.get(key, default)
    
    def get_all_configs(self):
        """Obter todas as configurações de uma vez"""
        return {
            'device': self.get_device_config(),
            'wifi': self.get_wifi_config(),
            'network': self.get_network_config(),
            'system': self.get_system_config()
        }