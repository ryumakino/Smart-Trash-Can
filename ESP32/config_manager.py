# config_manager.py
import ujson as json
import os
from utils import get_logger

logger = get_logger("ConfigManager")

class ConfigValidator:
    """SRP: Responsável apenas por validação"""
    
    @staticmethod
    def validate_section(section_name, section_data, schema):
        """Validar seção específica"""
        required_fields = schema.get('required', [])
        missing_fields = [field for field in required_fields if field not in section_data]
        
        if missing_fields:
            logger.warning(f"Seção {section_name} faltando campos: {missing_fields}")
            return False
        return True
    
    @staticmethod
    def validate_updates(section_name, updates):
        """Validar updates básicos"""
        for key, value in updates.items():
            if isinstance(value, str) and len(value.strip()) == 0:
                raise ValueError(f"Valor vazio para {key}")
            if value is None:
                raise ValueError(f"Valor None para {key}")
        return True

class ConfigCache:
    """SRP: Gerenciamento de cache"""
    
    def __init__(self):
        self._cache = {}
    
    def get(self, key):
        return self._cache.get(key)
    
    def set(self, key, value):
        self._cache[key] = value
    
    def invalidate(self, key=None):
        if key:
            self._cache.pop(key, None)
        else:
            self._cache.clear()
    
    def get_stats(self):
        return {
            'size': len(self._cache),
            'keys': list(self._cache.keys())
        }

class ConfigManager:
    """Classe principal - OCP: Aberta para extensão, fechada para modificação"""
    
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
        self.cache = ConfigCache()
        self._load_count = 0
        self.config = {}
        self.load_config()
    
    def load_config(self):
        """Carregar configuração - SRP"""
        try:
            if self.filename in os.listdir():
                with open(self.filename, 'r') as f:
                    loaded_config = json.load(f)
                
                self.config = self._apply_defaults_and_validate(loaded_config)
                self._load_count += 1
                self.cache.invalidate()
                
                logger.info(f"Config carregada (vez #{self._load_count})")
                return self.config
            else:
                raise FileNotFoundError(f"{self.filename} não encontrado")
                
        except Exception as e:
            logger.error(f"Erro ao carregar: {e}")
            self.config = self._create_default_config()
            raise
    
    def _apply_defaults_and_validate(self, config_dict):
        """Aplicar defaults e validar - DRY"""
        validated_config = {}
        
        for section_name, section_schema in self.CONFIG_SCHEMA.items():
            section_data = config_dict.get(section_name, {})
            defaults = section_schema.get('defaults', {})
            
            # DRY: Aplicar defaults uma única vez
            validated_section = {**defaults, **section_data}
            validated_config[section_name] = validated_section
            
            # Validar
            self.validator.validate_section(section_name, validated_section, section_schema)
        
        return validated_config
    
    def get_section(self, section_name):
        """Obter seção com cache - DRY"""
        cache_key = f"section_{section_name}"
        cached = self.cache.get(cache_key)
        
        if cached is not None:
            return cached
        
        section_data = self.config.get(section_name, {})
        
        # Aplicar defaults se necessário
        if section_name in self.CONFIG_SCHEMA:
            defaults = self.CONFIG_SCHEMA[section_name].get('defaults', {})
            section_data = {**defaults, **section_data}
        
        self.cache.set(cache_key, section_data)
        return section_data
    
    def get_value(self, section_name, key, default=None):
        """Obter valor específico - DRY"""
        cache_key = f"value_{section_name}_{key}"
        cached = self.cache.get(cache_key)
        
        if cached is not None:
            return cached
        
        section = self.get_section(section_name)
        value = section.get(key, default)
        
        self.cache.set(cache_key, value)
        return value
    
    def update_section(self, section_name, updates):
        """Atualizar seção - SRP"""
        try:
            self.validator.validate_updates(section_name, updates)
            
            current_section = self.get_section(section_name)
            updated_section = {**current_section, **updates}
            self.config[section_name] = updated_section
            
            # Invalidar cache relacionado
            self._invalidate_section_cache(section_name)
            
            return self._save_config()
            
        except Exception as e:
            logger.error(f"Erro ao atualizar {section_name}: {e}")
            return False
    
    def _invalidate_section_cache(self, section_name):
        """Invalidar cache da seção - DRY"""
        keys_to_remove = [
            k for k in self.cache._cache.keys()
            if k.startswith(f"section_{section_name}") or k.startswith(f"value_{section_name}")
        ]
        for key in keys_to_remove:
            self.cache.invalidate(key)
    
    def _save_config(self):
        """Salvar configuração - SRP"""
        try:
            # Criar backup se arquivo existir
            if self.filename in os.listdir():
                backup_name = f"{self.filename}.backup"
                with open(self.filename, 'r') as original:
                    with open(backup_name, 'w') as backup:
                        backup.write(original.read())
            
            # Salvar nova configuração
            with open(self.filename, 'w') as f:
                json.dump(self.config, f, indent=2)
            
            logger.info("Configuração salva")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao salvar: {e}")
            return False
    
    def _create_default_config(self):
        """Criar configuração padrão - SRP"""
        logger.warning("Criando configuração padrão")
        return {
            section: schema.get('defaults', {}).copy()
            for section, schema in self.CONFIG_SCHEMA.items()
        }
    
    # ISP: Interfaces específicas em vez de uma geral
    def get_device_config(self):
        return self.get_section('DeviceConfig')
    
    def get_wifi_config(self):
        return self.get_section('WiFiConfig')
    
    def get_network_config(self):
        return self.get_section('NetworkConfig')
    
    def get_system_config(self):
        return self.get_section('SystemConfig')
    
    def get_servo_config(self):
        return self.get_section('ServoConfig')
    
    def get_ir_config(self):
        return self.get_section('IRSensorConfig')
    
    def get_stats(self):
        """Estatísticas do gerenciador"""
        return {
            'load_count': self._load_count,
            'cache_stats': self.cache.get_stats(),
            'sections_loaded': list(self.config.keys())
        }