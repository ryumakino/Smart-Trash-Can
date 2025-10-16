# core/config_manager.py - CONFIGURAÇÃO SIMPLIFICADA SEM CLASSES
import ujson as json
import os

# Estado global
_config_data = None
_config_cache = {}

def _get_chip_id():
    """Obtém ID único do chip"""
    try:
        import machine
        return machine.unique_id().hex()[-6:]
    except:
        return "001"

def _get_default_config():
    """Configuração padrão de fallback"""
    return {
        "device": {
            "id": f"TRASH_AI_{_get_chip_id()}",
            "name": "Lixeira Inteligente - ESP32",
            "type": "TRASH_CAN",
            "location": ""
        },
        "wifi": {
            "ssid": "",
            "password": "",
            "max_retries": 3
        },
        "mqtt": {
            "broker": "broker.hivemq.com",
            "port": 1883,
            "topic_base": "trash_ai",
            "qos": 0,
            "keepalive": 60
        },
        "servo": {
            "pin": 18,
            "freq": 50,
            "min_duty": 40,
            "max_duty": 115,
            "angles": [0, 45, 90, 135, 180],
            "waste_types": ["Repouso", "Plástico", "Papel", "Metal", "Vidro"]
        },
        "sensors": {
            "ir_pin": 34,
            "check_interval": 0.1
        },
        "system": {
            "led_pin": 2,
            "health_check_interval": 30
        }
    }

def config_init(filename='config.json'):
    """Inicializa o gerenciador de configuração"""
    global _config_data
    try:
        # MicroPython: usar 'rb' para ler bytes
        with open(filename, 'rb') as f:
            _config_data = json.load(f)
    except Exception as e:
        print(f"Erro carregando config: {e}")
        _config_data = _get_default_config()
        # Salvar config padrão se não existir
        config_save(filename)
    _config_cache.clear()
    return _config_data

def config_get(*keys, default=None):
    """Obtém valor usando chaves aninhadas"""
    global _config_data
    
    if _config_data is None:
        config_init()
    
    cache_key = '.'.join(keys)
    if cache_key in _config_cache:
        return _config_cache[cache_key]
    
    value = _config_data
    try:
        for key in keys:
            value = value[key]
        _config_cache[cache_key] = value
        return value
    except (KeyError, TypeError):
        return default

def config_set(*keys, value):
    """Define valor usando chaves aninhadas"""
    global _config_data, _config_cache
    
    if len(keys) == 0:
        return False
    
    if _config_data is None:
        config_init()
    
    # Navega até o nível anterior
    config_level = _config_data
    for key in keys[:-1]:
        if key not in config_level:
            config_level[key] = {}
        config_level = config_level[key]
    
    # Define o valor
    config_level[keys[-1]] = value
    
    # Limpa cache e salva
    _config_cache.clear()
    return config_save()  # ← Esta linha já está correta

def config_save(filename='config.json'):
    """Salva configuração no arquivo"""
    global _config_data
    try:
        with open(filename, 'w') as f:
            json.dump(_config_data, f)
        return True
    except:
        return False

def config_get_all():
    """Retorna toda a configuração"""
    global _config_data
    if _config_data is None:
        config_init()
    return _config_data.copy()