# config_manager.py - CORREÇÕES COMPLETAS
import ujson as json
import os
from utils import get_logger

logger = get_logger("ConfigManager")

class ConfigValidator:
    @staticmethod
    def validate_section(section_data, schema):
        return bool(section_data and schema)
    
    @staticmethod
    def validate_updates(updates):
        for key, value in updates.items():
            # CORREÇÃO: MicroPython não tem strip() para não-strings
            if value is None or (isinstance(value, str) and not value.strip()):
                raise ValueError(f"Valor inválido para {key}")
        return True

class ConfigLoader:
    @staticmethod
    def load_from_file(filename):
        # CORREÇÃO: Verificação de arquivo mais robusta
        try:
            with open(filename, 'r') as f:
                return json.load(f)
        except OSError:
            raise OSError(f"{filename} não encontrado")
        except Exception as e:
            raise OSError(f"Erro ao ler {filename}: {e}")
    
    @staticmethod
    def create_default(schema):
        return {section: schema.copy() for section, schema in schema.items()}

class ConfigManager:
    CONFIG_SCHEMA = {
        "DeviceConfig": {
            "DEVICE_ID": "TRASH_AI_A1B2C3",
            "DEVICE_NAME": "Lixeira Inteligente",
            "DEVICE_TYPE": "TRASH_CAN",
            "DEVICE_LOCATION": "Sala de Reuniões",
            "DEVICE_VERSION": "1.0.0",
            "DEVICE_MANUFACTURER": "MAKEDC",
            "AUTO_GENERATE_ID": True
        },
        "WiFiConfig": {
            "SSID": "MinhaRedeWiFi",
            "PASSWORD": "minhasenha",
            "MAX_RETRIES": 3,
            "RETRY_DELAY": 5,
            "AP_SSID_PREFIX": "TRASH_AI_",
            "AP_PASSWORD": "trashai2024",
            "AP_CHANNEL": 6
        },
        "NetworkConfig": {
            "UDP_PORT": 8888,
            "BROADCAST_PORT": 8888,
            "SERVER_IP": "192.168.1.100",
            "SERVER_PORT": 8888,
            "AUTO_DISCOVER_SERVER": True,
            "DISCOVERY_INTERVAL": 30,
            "AUTH_KEY": "TR4SH_4I_S3CUR3_K3Y_2024_M4K3DC_D3C0747387",
            "TOKEN_TIMEOUT": 30
        },
        "SystemConfig": {
            "STATUS_LED_PIN": 2,
            "HEARTBEAT_INTERVAL": 60,
            "AP_MODE_BLINK_INTERVAL": 2,
            "LOG_LEVEL": "INFO",
            "MEMORY_CRITICAL": 4000,
            "MEMORY_WARNING": 8000,
            "GC_THRESHOLD": 20000
        },
        "ServoConfig": {
            "SERVO_PIN": 18,
            "SERVO_FREQ": 50,
            "SERVO_MIN_DUTY": 40,
            "SERVO_MAX_DUTY": 115,
            "SERVO_RESET_DELAY": 3,
            "SERVO_ANGLES": [0, 45, 90, 135, 180],
            "WASTE_TYPES": ["Repouso", "Plástico", "Papel", "Metal", "Vidro"]
        },
        "IRSensorConfig": {
            "IR_SENSOR_PIN": 34,
            "ACTIVE_HIGH": True,
            "CHECK_INTERVAL": 0.1,
            "DETECTION_THRESHOLD": 2
        },
        "ErrorHandlingConfig": {
            "MAX_RETRIES": 3,
            "BASE_RETRY_DELAY": 1,
            "MAX_RETRY_DELAY": 30,
            "MAX_FAILURES_BEFORE_RECOVERY": 5,
            "FAILURE_TIMEOUT": 300
        },
        "PowerConfig": {
            "SLEEP_ENABLED": True,
            "LIGHT_SLEEP_INTERVAL": 5,
            "DEEP_SLEEP_INTERVAL": 60,
            "NETWORK_SCAN_INTERVAL": 10
        },
        "HealthCheckConfig": {
            "HEALTH_CHECK_INTERVAL": 60,
            "MEMORY_WARNING_PERCENT": 70,
            "MEMORY_CRITICAL_PERCENT": 85,
            "UPTIME_WARNING_SECONDS": 86400,
            "UPTIME_CRITICAL_SECONDS": 604800
        }
    }
    
    def __init__(self, filename='config.json'):
        self.filename = filename
        self.validator = ConfigValidator()
        self.loader = ConfigLoader()
        self.config = {}
        self._initialize_config()
    
    def _initialize_config(self):
        try:
            loaded_config = self.loader.load_from_file(self.filename)
            self.config = self._apply_defaults(loaded_config)
            logger.info("Configuração carregada do arquivo")
        except OSError as e:
            logger.warning(f"Criando config padrão: {e}")
            self.config = self.loader.create_default(self.CONFIG_SCHEMA)
            self._save_config()
        except Exception as e:
            logger.error(f"Erro ao carregar configuração: {e}")
            self.config = self.loader.create_default(self.CONFIG_SCHEMA)
    
    def _apply_defaults(self, loaded_config):
        config_with_defaults = {}
        
        for section_name, section_schema in self.CONFIG_SCHEMA.items():
            section_data = loaded_config.get(section_name, {})
            merged_section = section_schema.copy()
            
            # CORREÇÃO: Atualizar apenas chaves existentes no schema
            for key, value in section_data.items():
                if key in merged_section:
                    merged_section[key] = value
            
            config_with_defaults[section_name] = merged_section
        
        return config_with_defaults
    
    def get_section(self, section_name):
        return self.config.get(section_name, {}).copy()
    
    def get_value(self, section_name, key, default=None):
        section = self.get_section(section_name)
        return section.get(key, default)
    
    def update_section(self, section_name, updates):
        try:
            self.validator.validate_updates(updates)
            current_section = self.get_section(section_name)
            current_section.update(updates)
            self.config[section_name] = current_section
            return self._save_config()
        except Exception as e:
            logger.error(f"Erro ao atualizar {section_name}: {e}")
            return False
    
    def _save_config(self):
        try:
            with open(self.filename, 'w') as f:
                json.dump(self.config, f)
            logger.info("Configuração salva com sucesso")
            return True
        except Exception as e:
            logger.error(f"Erro ao salvar configuração: {e}")
            return False