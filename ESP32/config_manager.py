# config_manager.py
import ujson as json
import os
from utils import get_logger

logger = get_logger("ConfigManager")

class ConfigManager:
    """Gerenciador de configurações com validação e cache - Responsabilidade Única"""
    
    # Esquema de validação centralizado
    CONFIG_SCHEMA = {
        'DeviceConfig': {
            'required': ['DEVICE_ID', 'DEVICE_NAME'],
            'defaults': {
                'DEVICE_TYPE': 'TRASH_CAN',
                'DEVICE_VERSION': '1.0.0',
                'AUTO_GENERATE_ID': True,
                'DEVICE_MANUFACTURER': 'MAKEDC',
                'DEVICE_LOCATION': 'Sala de Reuniões'
            }
        },
        'WiFiConfig': {
            'required': [],
            'defaults': {
                'MAX_RETRIES': 3,
                'RETRY_DELAY': 5,
                'AP_CHANNEL': 6,
                'AP_SSID_PREFIX': 'TRASH_AI_',
                'AP_PASSWORD': 'trashai2024'
            }
        },
        'NetworkConfig': {
            'required': [],
            'defaults': {
                'UDP_PORT': 8888,
                'BROADCAST_PORT': 8889,
                'DISCOVERY_INTERVAL': 30,
                'TOKEN_TIMEOUT': 30,
                'SERVER_PORT': 8888,
                'AUTO_DISCOVER_SERVER': True
            }
        },
        'SystemConfig': {
            'required': [],
            'defaults': {
                'STATUS_LED_PIN': 2,
                'HEARTBEAT_INTERVAL': 60,
                'AP_MODE_BLINK_INTERVAL': 2,
                'LOG_LEVEL': 'INFO'
            }
        },
        'ServoConfig': {
            'required': [],
            'defaults': {
                'SERVO_PIN': 18,
                'SERVO_FREQ': 50,
                'SERVO_MIN_DUTY': 40,
                'SERVO_MAX_DUTY': 115,
                'SERVO_RESET_DELAY': 3,
                'SERVO_ANGLES': [0, 45, 90, 135, 180],
                'WASTE_TYPES': ["Repouso", "Plástico", "Papel", "Metal", "Vidro"]
            }
        },
        'IRSensorConfig': {
            'required': [],
            'defaults': {
                'IR_SENSOR_PIN': 34,
                'ACTIVE_HIGH': True,
                'CHECK_INTERVAL': 0.1,
                'DETECTION_THRESHOLD': 2
            }
        }
    }
    
    def __init__(self, filename='config.json'):
        self.filename = filename
        self.config = {}
        self._cache = {}
        self._load_count = 0
        self.load_config()
    
    def load_config(self):
        """Carregar configuração com validação"""
        try:
            if self.filename in os.listdir():
                with open(self.filename, 'r') as f:
                    loaded_config = json.load(f)
                
                self.config = self._validate_and_apply_defaults(loaded_config)
                self._load_count += 1
                self._cache.clear()
                
                logger.info(f"Configuração carregada (vez #{self._load_count})")
                return self.config
            else:
                logger.error("Arquivo de configuração não encontrado")
                raise FileNotFoundError(f"{self.filename} not found")
                
        except Exception as e:
            logger.error(f"Erro ao carregar configuração: {e}")
            self.config = self._create_default_config()
            raise
    
    def save_config(self, config_dict=None):
        """Salvar configuração com backup"""
        try:
            config_to_save = config_dict or self.config
            
            # Criar backup
            if self.filename in os.listdir():
                backup_name = f"{self.filename}.backup"
                with open(self.filename, 'r') as original:
                    with open(backup_name, 'w') as backup:
                        backup.write(original.read())
            
            # Salvar nova configuração
            with open(self.filename, 'w') as f:
                json.dump(config_to_save, f, indent=2)
            
            self.config = config_to_save
            self._cache.clear()
            
            logger.info("Configuração salva com sucesso")
            return True
            
        except Exception as e:
            logger.error(f"Erro ao salvar configuração: {e}")
            return False
    
    def get_section(self, section_name, use_cache=True):
        """Obter seção de configuração com cache"""
        cache_key = f"section_{section_name}"
        
        if use_cache and cache_key in self._cache:
            return self._cache[cache_key]
        
        section_data = self.config.get(section_name, {})
        
        # Aplicar defaults
        if section_name in self.CONFIG_SCHEMA:
            defaults = self.CONFIG_SCHEMA[section_name].get('defaults', {})
            section_data = {**defaults, **section_data}
        
        if use_cache:
            self._cache[cache_key] = section_data
            
        return section_data
    
    def get_value(self, section_name, key, default=None, use_cache=True):
        """Obter valor específico"""
        cache_key = f"value_{section_name}_{key}"
        
        if use_cache and cache_key in self._cache:
            return self._cache[cache_key]
        
        section = self.get_section(section_name, use_cache=False)
        value = section.get(key, default)
        
        if use_cache:
            self._cache[cache_key] = value
            
        return value
    
    def update_section(self, section_name, updates, validate=True):
        """Atualizar seção com validação"""
        try:
            # Validar updates se necessário
            if validate:
                self._validate_updates(section_name, updates)
            
            # Obter seção atual
            current_section = self.get_section(section_name, use_cache=False)
            
            # Aplicar updates
            updated_section = {**current_section, **updates}
            self.config[section_name] = updated_section
            
            # Invalidar cache
            cache_keys_to_remove = [
                k for k in self._cache.keys() 
                if k.startswith(f"section_{section_name}") or k.startswith(f"value_{section_name}")
            ]
            for key in cache_keys_to_remove:
                self._cache.pop(key, None)
            
            return self.save_config()
            
        except Exception as e:
            logger.error(f"Erro ao atualizar seção {section_name}: {e}")
            return False
    
    def update_value(self, section_name, key, value, validate=True):
        """Atualizar valor específico"""
        return self.update_section(section_name, {key: value}, validate)
    
    def _validate_and_apply_defaults(self, config_dict):
        """Validar e aplicar defaults"""
        validated_config = {}
        
        for section_name, section_schema in self.CONFIG_SCHEMA.items():
            section_data = config_dict.get(section_name, {})
            defaults = section_schema.get('defaults', {})
            
            # Aplicar defaults para valores faltantes
            validated_section = {**defaults, **section_data}
            validated_config[section_name] = validated_section
            
            # Verificar campos obrigatórios
            required_fields = section_schema.get('required', [])
            missing_fields = [field for field in required_fields if field not in validated_section]
            
            if missing_fields:
                logger.warning(f"Seção {section_name} faltando campos obrigatórios: {missing_fields}")
        
        return validated_config
    
    def _validate_updates(self, section_name, updates):
        """Validar updates para uma seção"""
        if section_name not in self.CONFIG_SCHEMA:
            return  # Sem schema, sem validação
        
        # Validações básicas
        for key, value in updates.items():
            if isinstance(value, str) and len(value.strip()) == 0:
                raise ValueError(f"Valor vazio para {key}")
            if value is None:
                raise ValueError(f"Valor None para {key}")
    
    def _create_default_config(self):
        """Criar configuração padrão de emergência"""
        logger.warning("Criando configuração padrão de emergência")
        
        default_config = {}
        for section_name, section_schema in self.CONFIG_SCHEMA.items():
            default_config[section_name] = section_schema.get('defaults', {}).copy()
        
        return default_config
    
    # Métodos de conveniência para seções específicas
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
    
    def get_all_configs(self):
        """Obter todas as configurações formatadas"""
        return {
            'device': self.get_device_config(),
            'wifi': self.get_wifi_config(),
            'network': self.get_network_config(),
            'system': self.get_system_config(),
            'servo': self.get_servo_config(),
            'ir_sensor': self.get_ir_config()
        }
    
    def get_stats(self):
        """Obter estatísticas do gerenciador"""
        return {
            'load_count': self._load_count,
            'cache_size': len(self._cache),
            'cache_keys': list(self._cache.keys()),
            'sections_loaded': list(self.config.keys())
        }