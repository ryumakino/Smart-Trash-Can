from flask import Blueprint, render_template, jsonify
from src.core.app_config import (
    get_device_registry,
    get_database,
    get_classification_service,
    get_trash_net_server
)
import psutil, os, datetime, logging

views_bp = Blueprint("views", __name__)
logger = logging.getLogger("WebViews")

def safe_stats():
    """Retorna estatísticas sempre válidas."""
    try:
        return get_database().get_statistics()
    except Exception as e:
        logger.warning("Falha ao ler estatísticas: %s", e)
        return {
            "total_classifications": 0,
            "average_confidence": 0,
            "classifications_by_type": {},
            "last_classification": None,
        }

def safe_system():
    """Dados do sistema com valores padrão."""
    try:
        return {
            "cpu": psutil.cpu_percent(interval=None),
            "memory": psutil.virtual_memory().percent,
            "uptime": str(datetime.datetime.now() - datetime.datetime.fromtimestamp(psutil.boot_time())).split(".")[0],
        }
    except Exception as e:
        logger.warning("Falha ao ler dados do sistema: %s", e)
        return {"cpu": 0, "memory": 0, "uptime": "—"}
    
@views_bp.route("/")
def index():
    """Página inicial"""
    from flask import current_app
    
    device_manager = current_app.device_manager
    devices = device_manager.get_all_devices()
    
    # Calcular estatísticas
    online_devices = sum(1 for d in devices.values() if d.get('status') == 'online')
    total_classifications = sum(d.get('classifications_count', 0) for d in devices.values())
    
    stats = {
        "total_devices": len(devices),
        "online_devices": online_devices,
        "total_classifications": total_classifications,
        "last_classification": max([d.get('last_movement') for d in devices.values() if d.get('last_movement')], default=None)
    }
    
    return render_template("index.html", 
                         stats=stats, 
                         system_stats=safe_system(),
                         devices=devices)

@views_bp.route("/mqtt-control")
def mqtt_control():
    """Página de controle MQTT"""
    from flask import current_app
    
    device_manager = current_app.device_manager
    devices = device_manager.get_all_devices()
    
    return render_template("mqtt_control.html", devices=devices)

@views_bp.route("/devices")
def devices():
    """Página de dispositivos"""
    from flask import current_app
    
    device_manager = current_app.device_manager
    devices = device_manager.get_all_devices()
    
    return render_template("devices.html", devices=devices)

@views_bp.route("/esp32-control")
def esp32_control():
    """Página de controle específica para ESP32"""
    from flask import current_app
    
    device_manager = current_app.device_manager
    devices = device_manager.get_all_devices()
    
    # Filtrar apenas dispositivos ESP32 (baseado no protocolo ou nome)
    esp32_devices = {
        dev_id: dev_data for dev_id, dev_data in devices.items() 
        if dev_data.get('protocol') == 'mqtt' or 'ESP32' in dev_data.get('device_name', '')
    }
    
    # Tipos de lixo padrão para ESP32
    waste_types = ['Repouso', 'Plástico', 'Papel', 'Metal', 'Vidro']
    
    return render_template("esp32_control.html", 
                         devices=esp32_devices,
                         waste_types=waste_types)

@views_bp.route("/settings")
def settings():
    from src.config.config_manager import CONFIG_MANAGER
    import os, glob

    cfg = CONFIG_MANAGER.get_all_config()

    # Lista de arquivos do sistema
    base = os.getcwd()
    arquivos = {}
    pastas = {
        "logs": "logs",
        "models": "models",
        "data": "data",
        "test_images": "test_images",
        "templates": "templates",
    }
    for nome, pasta in pastas.items():
        caminho = os.path.join(base, pasta)
        arquivos[nome] = []
        if os.path.isdir(caminho):
            for f in glob.glob(os.path.join(caminho, "**"), recursive=True):
                if os.path.isfile(f):
                    rel = os.path.relpath(f, base)
                    arquivos[nome].append({
                        "path": rel,
                        "size": os.path.getsize(f),
                        "mtime": datetime.datetime.fromtimestamp(os.path.getmtime(f)).strftime("%d/%m %H:%M")
                    })
            arquivos[nome].sort(key=lambda x: x["mtime"], reverse=True)

    return render_template("settings.html", config=cfg, arquivos=arquivos)

@views_bp.route("/classes")
def classes():
    from src.config.config_manager import CONFIG_MANAGER
    try:
        cfg = CONFIG_MANAGER.get_trashnet_config()
        original = cfg.get("ORIGINAL_CLASSES", [])
        mapping = cfg.get("CLASS_MAPPING", {})
        unique_system_classes = len(set(mapping.values()))
    except Exception as e:
        logger.warning("Falha ao obter classes: %s", e)
        original, mapping, unique_system_classes = [], {}, 0
    return render_template("classes.html", original=original, mapping=mapping, unique_system_classes=unique_system_classes)

@views_bp.route("/logs")
def logs():
    log_file = os.path.join("logs", f"server_{datetime.datetime.now():%Y%m%d}.log")
    lines = ""
    try:
        if os.path.isfile(log_file):
            with open(log_file, encoding="utf-8") as f:
                lines = "".join(f.readlines()[-500:])
    except Exception as e:
        logger.warning("Falha ao ler logs: %s", e)
        lines = "Erro ao carregar logs."
    return render_template("logs.html", logs=lines)