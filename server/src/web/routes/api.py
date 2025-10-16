from flask import Blueprint, request, jsonify, current_app
from src.core.app_config import (
    get_device_registry,
    get_database,
    get_server_communicator,
    get_trash_net_server,
    get_classification_service
)
from src.config.config_manager import CONFIG_MANAGER
import logging
import os
from datetime import datetime, timedelta

logger = logging.getLogger("DashboardAPI")
api_bp = Blueprint("api", __name__)

def safe_get(func, default=None):
    """Executa função com tratamento de erro seguro"""
    try:
        return func()
    except Exception as e:
        logger.error(f"Erro ao executar função: {e}")
        return default

@api_bp.route("/devices")
def get_devices():
    """Obtém lista de todos os dispositivos"""
    try:
        device_manager = current_app.device_manager
        devices = device_manager.get_all_devices()
        
        return jsonify(devices)
        
    except Exception as e:
        logger.error(f"Erro ao buscar dispositivos: {e}")
        return jsonify({"error": "Erro interno do servidor"}), 500

@api_bp.route("/devices/<device_id>")
def get_device(device_id):
    """Obtém informações de um dispositivo específico"""
    try:
        device_manager = current_app.device_manager
        device = device_manager.get_device(device_id)
        
        if not device:
            return jsonify({"error": "Dispositivo não encontrado"}), 404
        
        return jsonify(device)
        
    except Exception as e:
        logger.error(f"Erro ao buscar dispositivo {device_id}: {e}")
        return jsonify({"error": "Erro interno do servidor"}), 500

@api_bp.route("/devices/<device_id>/request-info", methods=["POST"])
def request_device_info(device_id):
    """Solicita informações completas do dispositivo via MQTT"""
    try:
        mqtt_manager = current_app.mqtt_manager
        
        # Primeiro verifica se o dispositivo existe, se não, cria
        device_manager = current_app.device_manager
        if not device_manager.get_device(device_id):
            device_manager.add_device(device_id)
        
        # Solicita informações via MQTT
        success = mqtt_manager.request_device_info(device_id)
        
        if success:
            return jsonify({
                "success": True,
                "message": f"Solicitação de informações enviada para {device_id}",
                "device_id": device_id
            })
        else:
            return jsonify({"error": "Falha ao solicitar informações"}), 500
            
    except Exception as e:
        logger.error(f"Erro ao solicitar informações do dispositivo {device_id}: {e}")
        return jsonify({"error": "Erro interno do servidor"}), 500

@api_bp.route("/devices/<device_id>/send-command", methods=["POST"])
def send_device_command(device_id):
    """Envia comando para dispositivo via MQTT"""
    try:
        data = request.get_json()
        if not data or not data.get('command'):
            return jsonify({"error": "Comando é obrigatório"}), 400
        
        command = data['command']
        payload = data.get('payload')
        
        mqtt_manager = current_app.mqtt_manager
        
        # Verifica se dispositivo existe
        device_manager = current_app.device_manager
        if not device_manager.get_device(device_id):
            device_manager.add_device(device_id)
        
        success = mqtt_manager.publish_command(device_id, command, payload)
        
        if success:
            return jsonify({
                "success": True,
                "message": f"Comando {command} enviado para {device_id}",
                "device_id": device_id,
                "command": command
            })
        else:
            return jsonify({"error": "Falha ao enviar comando"}), 500
            
    except Exception as e:
        logger.error(f"Erro ao enviar comando para {device_id}: {e}")
        return jsonify({"error": "Erro interno do servidor"}), 500

@api_bp.route("/devices/<device_id>/servo/move", methods=["POST"])
def move_servo_angle(device_id):
    """Move servo do ESP32 para ângulo específico"""
    try:
        data = request.get_json()
        if not data or data.get('angle') is None:
            return jsonify({"error": "Ângulo é obrigatório"}), 400
        
        angle = int(data['angle'])
        
        mqtt_manager = current_app.mqtt_manager
        success = mqtt_manager.publish_command(device_id, 'MOVE_SERVO', {'angle': angle})
        
        if success:
            return jsonify({
                "success": True,
                "message": f"Servo movido para {angle}°",
                "device_id": device_id,
                "angle": angle
            })
        else:
            return jsonify({"error": "Falha ao mover servo"}), 500
            
    except Exception as e:
        logger.error(f"Erro ao mover servo: {e}")
        return jsonify({"error": "Erro interno do servidor"}), 500

@api_bp.route("/devices/<device_id>/servo/waste-type", methods=["POST"])
def set_waste_type(device_id):
    """Seleciona tipo de lixo no ESP32"""
    try:
        data = request.get_json()
        if not data or data.get('index') is None:
            return jsonify({"error": "Índice do tipo de lixo é obrigatório"}), 400
        
        waste_index = int(data['index'])
        
        mqtt_manager = current_app.mqtt_manager
        success = mqtt_manager.publish_command(device_id, 'WASTE_TYPE', {'index': waste_index})
        
        if success:
            return jsonify({
                "success": True,
                "message": f"Tipo de lixo definido para índice {waste_index}",
                "device_id": device_id,
                "waste_index": waste_index
            })
        else:
            return jsonify({"error": "Falha ao definir tipo de lixo"}), 500
            
    except Exception as e:
        logger.error(f"Erro ao definir tipo de lixo: {e}")
        return jsonify({"error": "Erro interno do servidor"}), 500

@api_bp.route("/devices/<device_id>/ping", methods=["POST"])
def ping_device(device_id):
    """Faz ping no dispositivo ESP32"""
    try:
        mqtt_manager = current_app.mqtt_manager
        success = mqtt_manager.publish_command(device_id, 'PING')
        
        if success:
            return jsonify({
                "success": True,
                "message": f"Ping enviado para {device_id}",
                "device_id": device_id,
                "timestamp": datetime.now().isoformat()
            })
        else:
            return jsonify({"error": "Falha ao enviar ping"}), 500
            
    except Exception as e:
        logger.error(f"Erro no ping: {e}")
        return jsonify({"error": "Erro interno do servidor"}), 500

@api_bp.route("/devices/<device_id>/restart", methods=["POST"])
def restart_device(device_id):
    """Reinicia dispositivo ESP32"""
    try:
        mqtt_manager = current_app.mqtt_manager
        success = mqtt_manager.publish_command(device_id, 'RESET')
        
        if success:
            return jsonify({
                "success": True,
                "message": f"Comando de reinício enviado para {device_id}",
                "device_id": device_id,
                "timestamp": datetime.now().isoformat()
            })
        else:
            return jsonify({"error": "Falha ao enviar comando de reinício"}), 500
            
    except Exception as e:
        logger.error(f"Erro ao reiniciar dispositivo: {e}")
        return jsonify({"error": "Erro interno do servidor"}), 500

@api_bp.route("/devices/broadcast", methods=["POST"])
def broadcast_command():
    """Envia comando para todos os dispositivos"""
    try:
        data = request.get_json()
        if not data or not data.get('command'):
            return jsonify({"error": "Comando é obrigatório"}), 400
        
        command = data['command']
        payload = data.get('payload')
        
        device_manager = current_app.device_manager
        mqtt_manager = current_app.mqtt_manager
        
        devices = device_manager.get_all_devices()
        results = []
        
        for device_id in devices.keys():
            success = mqtt_manager.publish_command(device_id, command, payload)
            results.append({
                'device_id': device_id,
                'success': success
            })
        
        successful_commands = sum(1 for r in results if r['success'])
        
        return jsonify({
            "success": True,
            "message": f"Comando {command} enviado para {successful_commands}/{len(results)} dispositivos",
            "results": results
        })
            
    except Exception as e:
        logger.error(f"Erro no broadcast de comando: {e}")
        return jsonify({"error": "Erro interno do servidor"}), 500

@api_bp.route("/mqtt/status")
def get_mqtt_status():
    """Retorna status da conexão MQTT"""
    try:
        mqtt_manager = current_app.mqtt_manager
        status = mqtt_manager.get_status()
        
        return jsonify(status)
        
    except Exception as e:
        logger.error(f"Erro ao obter status MQTT: {e}")
        return jsonify({"error": "Erro interno do servidor"}), 500


@api_bp.route("/config", methods=["GET", "POST"])
def handle_config():
    """Gerencia configurações do sistema"""
    try:
        if request.method == "GET":
            config_data = safe_get(
                lambda: CONFIG_MANAGER.get_all_configs(),
                {}
            )
            return jsonify(config_data)
            
        elif request.method == "POST":
            config_updates = request.get_json()
            
            if not config_updates:
                return jsonify({"error": "Dados de configuração inválidos"}), 400
            
            # Validar e aplicar atualizações
            for key, value in config_updates.items():
                if CONFIG_MANAGER.is_valid_config(key, value):
                    CONFIG_MANAGER.set_config(key, value)
                else:
                    return jsonify({"error": f"Configuração inválida: {key}"}), 400
            
            CONFIG_MANAGER.save_config()
            return jsonify({"message": "Configurações atualizadas com sucesso"})
            
    except Exception as e:
        logger.error(f"Erro ao gerenciar configurações: {e}")
        return jsonify({"error": "Erro interno do servidor"}), 500

@api_bp.route("/logs")
def get_logs():
    """Obtém logs do sistema"""
    try:
        lines = request.args.get("lines", 100, type=int)
        log_file = "logs/trashnet.log"
        
        if not os.path.exists(log_file):
            return jsonify({"error": "Arquivo de log não encontrado"}), 404
        
        with open(log_file, "r", encoding="utf-8") as f:
            log_lines = f.readlines()[-lines:]
        
        return jsonify({
            "logs": log_lines,
            "total_lines": len(log_lines)
        })
        
    except Exception as e:
        logger.error(f"Erro ao buscar logs: {e}")
        return jsonify({"error": "Erro interno do servidor"}), 500

@api_bp.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Endpoint não encontrado"}), 404

@api_bp.errorhandler(500)
def internal_error(error):
    return jsonify({"error": "Erro interno do servidor"}), 500

@api_bp.route("/system/metrics")
def get_system_metrics():
    """Obtém métricas completas do sistema em tempo real (CORRIGIDO)"""
    try:
        import psutil, datetime, platform, socket, os, sys
        from datetime import timedelta

        # Função para formatar bytes
        def format_bytes(bytes_size):
            if bytes_size == 0:
                return "0 B"
            for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
                if bytes_size < 1024.0:
                    return f"{bytes_size:.1f} {unit}"
                bytes_size /= 1024.0
            return f"{bytes_size:.1f} PB"

        # Função para obter informações de processos
        def get_top_processes():
            try:
                processes = []
                for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
                    try:
                        # Atualizar CPU percent para obter valores corretos
                        proc.cpu_percent()
                        processes.append(proc.info)
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue
                
                # Pequena pausa para cálculo preciso de CPU
                import time
                time.sleep(0.1)
                
                # Re-coletar dados com CPU atualizado
                updated_processes = []
                for proc_info in processes:
                    try:
                        p = psutil.Process(proc_info['pid'])
                        with p.oneshot():
                            updated_info = {
                                'pid': proc_info['pid'],
                                'name': proc_info['name'],
                                'cpu_percent': p.cpu_percent(),
                                'memory_percent': p.memory_percent(),
                                'memory_info': p.memory_info()._asdict()
                            }
                            updated_processes.append(updated_info)
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue
                
                # Ordenar por uso de CPU
                processes_sorted = sorted(updated_processes, 
                                        key=lambda x: x['cpu_percent'] or 0, 
                                        reverse=True)[:10]
                return processes_sorted
            except Exception as e:
                logger.error(f"Erro ao obter processos: {e}")
                return []

        # Função para obter informações de rede detalhadas
        def get_network_details():
            try:
                connections = psutil.net_connections()
                stats = {
                    'total_connections': len(connections),
                    'tcp_connections': len([c for c in connections if c.type == 1]),  # SOCK_STREAM
                    'udp_connections': len([c for c in connections if c.type == 2]),  # SOCK_DGRAM
                    'listening_ports': len([c for c in connections if c.status == 'LISTEN'])
                }
                return stats
            except Exception as e:
                logger.error(f"Erro ao obter detalhes de rede: {e}")
                return {}

        # Função para obter informações de discos múltiplos
        def get_all_disks():
            try:
                disks = []
                for partition in psutil.disk_partitions():
                    try:
                        # Ignorar partições de sistema e dispositivos especiais
                        if partition.fstype in ['squashfs', 'tmpfs', 'devtmpfs']:
                            continue
                        usage = psutil.disk_usage(partition.mountpoint)
                        disks.append({
                            'device': partition.device,
                            'mountpoint': partition.mountpoint,
                            'fstype': partition.fstype,
                            'total': usage.total,
                            'used': usage.used,
                            'free': usage.free,
                            'percent': usage.percent
                        })
                    except (PermissionError, OSError):
                        continue
                return disks
            except Exception as e:
                logger.error(f"Erro ao obter discos: {e}")
                return []

        # Função para obter informações de GPU (se disponível)
        def get_gpu_info():
            try:
                gpu_info = {'gpus': [], 'gpu_available': False}
                
                # Tentar importar GPUtil se disponível
                try:
                    import GPUtil
                    gpus = GPUtil.getGPUs()
                    if gpus:
                        gpu_info['gpus'] = [{
                            'id': gpu.id,
                            'name': gpu.name,
                            'load': gpu.load * 100,
                            'memory_total': gpu.memoryTotal,
                            'memory_used': gpu.memoryUsed,
                            'memory_free': gpu.memoryFree,
                            'temperature': getattr(gpu, 'temperature', 'N/A')
                        } for gpu in gpus]
                        gpu_info['gpu_available'] = True
                except ImportError:
                    # Tentar nvidia-smi como fallback
                    try:
                        import subprocess
                        result = subprocess.run(['nvidia-smi', '--query-gpu=name,memory.total,memory.used,utilization.gpu,temperature.gpu', '--format=csv,noheader,nounits'], 
                                              capture_output=True, text=True, timeout=5)
                        if result.returncode == 0:
                            lines = result.stdout.strip().split('\n')
                            for i, line in enumerate(lines):
                                parts = [p.strip() for p in line.split(',')]
                                if len(parts) >= 5:
                                    gpu_info['gpus'].append({
                                        'id': i,
                                        'name': parts[0],
                                        'load': float(parts[3]),
                                        'memory_total': float(parts[1]),
                                        'memory_used': float(parts[2]),
                                        'memory_free': float(parts[1]) - float(parts[2]),
                                        'temperature': float(parts[4])
                                    })
                                    gpu_info['gpu_available'] = True
                    except:
                        pass
                
                return gpu_info
            except Exception as e:
                logger.error(f"Erro ao obter info GPU: {e}")
                return {'gpus': [], 'gpu_available': False}

        # Função para obter informações de sensores (compatível)
        def get_sensors_info():
            try:
                sensors = {
                    'temperatures': {},
                    'fans': {},
                    'battery': {}
                }
                
                # Temperaturas - compatível com diferentes versões do psutil
                try:
                    if hasattr(psutil, 'sensors_temperatures'):
                        temps = psutil.sensors_temperatures()
                        if temps:
                            for sensor, values in temps.items():
                                sensors['temperatures'][sensor] = [
                                    {'label': getattr(temp, 'label', 'N/A'), 
                                     'current': getattr(temp, 'current', 0),
                                     'high': getattr(temp, 'high', 0),
                                     'critical': getattr(temp, 'critical', 0)}
                                    for temp in values
                                ]
                except Exception as e:
                    logger.warning(f"Erro ao obter temperaturas: {e}")
                
                # Fans - compatível
                try:
                    if hasattr(psutil, 'sensors_fans'):
                        fans = psutil.sensors_fans()
                        if fans:
                            for sensor, values in fans.items():
                                sensors['fans'][sensor] = [
                                    {'label': getattr(fan, 'label', 'N/A'),
                                     'current': getattr(fan, 'current', 0)}
                                    for fan in values
                                ]
                except Exception as e:
                    logger.warning(f"Erro ao obter fans: {e}")
                
                # Bateria - compatível
                try:
                    battery = psutil.sensors_battery()
                    if battery:
                        sensors['battery'] = {
                            'percent': getattr(battery, 'percent', 0),
                            'power_plugged': getattr(battery, 'power_plugged', False),
                            'secsleft': getattr(battery, 'secsleft', 0)
                        }
                except Exception as e:
                    logger.warning(f"Erro ao obter bateria: {e}")
                
                return sensors
            except Exception as e:
                logger.error(f"Erro ao obter sensores: {e}")
                return {'temperatures': {}, 'fans': {}, 'battery': {}}

        # Coletar métricas principais
        metrics = {
            # CPU - Informações avançadas
            "cpu": {
                "usage_percent": safe_get(lambda: psutil.cpu_percent(interval=1), 0),
                "usage_per_core": safe_get(lambda: [{"core": i, "usage": percent} for i, percent in enumerate(psutil.cpu_percent(interval=0.5, percpu=True))], []),
                "cores_physical": safe_get(lambda: psutil.cpu_count(logical=False), 0),
                "cores_logical": safe_get(lambda: psutil.cpu_count(logical=True), 0),
                "frequency": safe_get(lambda: psutil.cpu_freq()._asdict() if psutil.cpu_freq() else {}, {}),
                "load_avg": safe_get(lambda: [x / psutil.cpu_count() * 100 for x in psutil.getloadavg()], [0, 0, 0]) if hasattr(psutil, 'getloadavg') else [0, 0, 0],
                "stats": safe_get(lambda: psutil.cpu_stats()._asdict(), {}),
                "times": safe_get(lambda: psutil.cpu_times()._asdict(), {})
            },

            # Memória - Informações compatíveis
            "memory": {
                "total": safe_get(lambda: psutil.virtual_memory().total, 0),
                "available": safe_get(lambda: psutil.virtual_memory().available, 0),
                "used": safe_get(lambda: psutil.virtual_memory().used, 0),
                "percent": safe_get(lambda: psutil.virtual_memory().percent, 0),
                "free": safe_get(lambda: psutil.virtual_memory().free, 0),
                # Atributos que podem não estar disponíveis em todos os sistemas
                "active": safe_get(lambda: getattr(psutil.virtual_memory(), 'active', 0), 0),
                "inactive": safe_get(lambda: getattr(psutil.virtual_memory(), 'inactive', 0), 0),
                "buffers": safe_get(lambda: getattr(psutil.virtual_memory(), 'buffers', 0), 0),
                "cached": safe_get(lambda: getattr(psutil.virtual_memory(), 'cached', 0), 0),
                "shared": safe_get(lambda: getattr(psutil.virtual_memory(), 'shared', 0), 0),
                "swap_total": safe_get(lambda: psutil.swap_memory().total, 0),
                "swap_used": safe_get(lambda: psutil.swap_memory().used, 0),
                "swap_free": safe_get(lambda: psutil.swap_memory().free, 0),
                "swap_percent": safe_get(lambda: psutil.swap_memory().percent, 0),
                "swap_sin": safe_get(lambda: getattr(psutil.swap_memory(), 'sin', 0), 0),
                "swap_sout": safe_get(lambda: getattr(psutil.swap_memory(), 'sout', 0), 0)
            },

            # Discos - Todos os discos e partições
            "disks": {
                "root": {
                    "usage_percent": safe_get(lambda: psutil.disk_usage("/").percent, 0),
                    "total": safe_get(lambda: psutil.disk_usage("/").total, 0),
                    "used": safe_get(lambda: psutil.disk_usage("/").used, 0),
                    "free": safe_get(lambda: psutil.disk_usage("/").free, 0)
                },
                "all_disks": safe_get(get_all_disks, []),
                "io_counters": safe_get(lambda: psutil.disk_io_counters()._asdict() if psutil.disk_io_counters() else {}, {}),
            },

            # Rede - Estatísticas avançadas
            "network": {
                "io_counters": safe_get(lambda: psutil.net_io_counters()._asdict() if psutil.net_io_counters() else {}, {}),
                "connections": safe_get(get_network_details, {}),
                "interfaces": safe_get(lambda: len(psutil.net_if_addrs()), 0),
            },

            # Sistema - Informações completas
            "system": {
                "boot_time": safe_get(lambda: datetime.datetime.fromtimestamp(psutil.boot_time()).isoformat(), ""),
                "uptime_seconds": safe_get(lambda: (datetime.datetime.now() - datetime.datetime.fromtimestamp(psutil.boot_time())).total_seconds(), 0),
                "process_count": safe_get(lambda: len(psutil.pids()), 0),
                "thread_count": safe_get(lambda: sum(p.num_threads() for p in psutil.process_iter(['num_threads']) if p.info['num_threads']), 0),
                "users_connected": safe_get(lambda: len(psutil.users()), 0),
                "hostname": safe_get(lambda: socket.gethostname(), ""),
                "platform": safe_get(lambda: platform.platform(), ""),
                "python_version": safe_get(lambda: platform.python_version(), ""),
                "architecture": safe_get(lambda: platform.architecture()[0], ""),
                "processor": safe_get(lambda: platform.processor(), ""),
                "system": safe_get(lambda: platform.system(), ""),
                "release": safe_get(lambda: platform.release(), ""),
                "version": safe_get(lambda: platform.version(), ""),
                "machine": safe_get(lambda: platform.machine(), "")
            },

            # Sensores - Monitoramento de hardware (compatível)
            "sensors": safe_get(get_sensors_info, {'temperatures': {}, 'fans': {}, 'battery': {}}),

            # Processos - Top processos
            "processes": {
                "top_by_cpu": safe_get(get_top_processes, []),
            },

            # GPU - Informações de placa de vídeo
            "gpu": safe_get(get_gpu_info, {'gpus': [], 'gpu_available': False}),
        }

        # Adicionar informações formatadas para fácil consumo
        metrics["formatted"] = {
            # Memória
            "memory_total": format_bytes(metrics["memory"]["total"]),
            "memory_used": format_bytes(metrics["memory"]["used"]),
            "memory_available": format_bytes(metrics["memory"]["available"]),
            "memory_free": format_bytes(metrics["memory"]["free"]),
            "memory_active": format_bytes(metrics["memory"]["active"]),
            "memory_inactive": format_bytes(metrics["memory"]["inactive"]),
            "memory_buffers": format_bytes(metrics["memory"]["buffers"]),
            "memory_cached": format_bytes(metrics["memory"]["cached"]),
            "memory_shared": format_bytes(metrics["memory"]["shared"]),
            
            # Swap
            "swap_used": format_bytes(metrics["memory"]["swap_used"]),
            "swap_total": format_bytes(metrics["memory"]["swap_total"]),
            "swap_free": format_bytes(metrics["memory"]["swap_free"]),
            
            # Disco
            "disk_total": format_bytes(metrics["disks"]["root"]["total"]),
            "disk_used": format_bytes(metrics["disks"]["root"]["used"]),
            "disk_free": format_bytes(metrics["disks"]["root"]["free"]),
            
            # Rede
            "network_sent": format_bytes(metrics["network"]["io_counters"].get("bytes_sent", 0)),
            "network_recv": format_bytes(metrics["network"]["io_counters"].get("bytes_recv", 0)),
            "network_packets_sent": metrics["network"]["io_counters"].get("packets_sent", 0),
            "network_packets_recv": metrics["network"]["io_counters"].get("packets_recv", 0),
            
            # Uptime
            "uptime_human": str(timedelta(seconds=int(metrics["system"]["uptime_seconds"]))),
            "boot_time_human": safe_get(lambda: datetime.datetime.fromtimestamp(psutil.boot_time()).strftime("%d/%m/%Y %H:%M:%S"), ""),
        }

        # Adicionar estatísticas de performance
        metrics["performance"] = {
            "memory_efficiency": safe_get(lambda: (metrics["memory"]["cached"] + metrics["memory"]["buffers"]) / metrics["memory"]["total"] * 100 if metrics["memory"]["total"] > 0 else 0, 0),
            "swap_activity": safe_get(lambda: metrics["memory"]["swap_sin"] + metrics["memory"]["swap_sout"], 0),
            "context_switches": safe_get(lambda: metrics["cpu"]["stats"].get("ctx_switches", 0), 0),
            "interrupts": safe_get(lambda: metrics["cpu"]["stats"].get("interrupts", 0), 0)
        }

        return jsonify(metrics)

    except Exception as e:
        logger.error(f"Erro ao buscar métricas do sistema: {e}")
        return jsonify({"error": "Erro interno do servidor"}), 500