from flask import Flask, render_template, jsonify, request
from datetime import datetime
import psutil, os, logging, json, threading
import paho.mqtt.client as mqtt
from collections import defaultdict
import requests

logger = logging.getLogger("Dashboard")

class DeviceManager:
    """Gerenciador de dispositivos em memória"""
    
    def __init__(self):
        self.devices = {}  # {device_id: device_data}
        self.device_callbacks = defaultdict(list)
    
    def add_device(self, device_id, initial_data=None):
        """Adiciona/atualiza dispositivo"""
        if device_id not in self.devices:
            self.devices[device_id] = {
                'device_id': device_id,
                'device_name': initial_data.get('device_name', f'ESP32_{device_id[-6:]}'),
                'device_type': 'TRASH_CAN',
                'status': 'offline',
                'last_seen': None,
                'first_seen': datetime.now().isoformat(),
                'protocol': 'mqtt',
                'firmware_version': '1.0.0',
                'hardware_info': {},
                'system_info': {},
                'config': {},
                'classifications_count': 0,
                'last_classification': None,
                'last_prediction': None
            }
        
        if initial_data:
            self.devices[device_id].update(initial_data)
        
        logger.info(f"Dispositivo registrado: {device_id}")
        return self.devices[device_id]
    
    def update_device(self, device_id, updates):
        """Atualiza dados do dispositivo"""
        if device_id in self.devices:
            self.devices[device_id].update(updates)
            self.devices[device_id]['last_seen'] = datetime.now().isoformat()
            
            # Notificar callbacks
            for callback in self.device_callbacks[device_id]:
                try:
                    callback(device_id, self.devices[device_id])
                except Exception as e:
                    logger.error(f"Erro em callback: {e}")
            
            return True
        return False
    
    def get_device(self, device_id):
        """Obtém dispositivo por ID"""
        return self.devices.get(device_id)
    
    def get_all_devices(self):
        """Retorna todos os dispositivos"""
        return self.devices
    
    def remove_device(self, device_id):
        """Remove dispositivo"""
        if device_id in self.devices:
            del self.devices[device_id]
            if device_id in self.device_callbacks:
                del self.device_callbacks[device_id]
            return True
        return False
    
    def register_callback(self, device_id, callback):
        """Registra callback para atualizações do dispositivo"""
        self.device_callbacks[device_id].append(callback)

class MLServerClient:
    """Cliente para comunicação com o servidor ML"""
    
    def __init__(self, base_url):
        self.base_url = base_url
        self.session = requests.Session()
        self.timeout = 30
    
    def get_health(self):
        """Verifica saúde do servidor ML"""
        try:
            response = self.session.get(f"{self.base_url}/health", timeout=10)
            return response.json() if response.status_code == 200 else None
        except Exception as e:
            logger.error(f"Erro ao verificar saúde do ML server: {e}")
            return None
    
    def get_models(self):
        """Obtém modelos disponíveis"""
        try:
            response = self.session.get(f"{self.base_url}/api/v1/models", timeout=10)
            return response.json() if response.status_code == 200 else None
        except Exception as e:
            logger.error(f"Erro ao obter modelos: {e}")
            return None
    
    def predict(self, model_name, features):
        """Faz predição com features"""
        try:
            data = {
                "features": features,
                "model_name": model_name
            }
            response = self.session.post(
                f"{self.base_url}/api/v1/predict", 
                json=data,
                timeout=self.timeout
            )
            return response.json() if response.status_code == 200 else None
        except Exception as e:
            logger.error(f"Erro na predição: {e}")
            return None
    
    def predict_image(self, model_name, image_file):
        """Faz predição com imagem"""
        try:
            files = {'file': (image_file.filename, image_file, 'image/jpeg')}
            data = {'model_name': model_name}
            
            response = self.session.post(
                f"{self.base_url}/api/v1/predict-image/{model_name}",
                files=files,
                data=data,
                timeout=self.timeout
            )
            return response.json() if response.status_code == 200 else None
        except Exception as e:
            logger.error(f"Erro na predição de imagem: {e}")
            return None
    
    def get_prediction(self, prediction_id):
        """Obtém predição pelo ID"""
        try:
            response = self.session.get(f"{self.base_url}/api/v1/prediction/{prediction_id}", timeout=10)
            return response.json() if response.status_code == 200 else None
        except Exception as e:
            logger.error(f"Erro ao buscar predição: {e}")
            return None
    
    def get_recent_predictions(self, limit=10):
        """Obtém predições recentes"""
        try:
            response = self.session.get(f"{self.base_url}/api/v1/predictions/recent?limit={limit}", timeout=10)
            return response.json() if response.status_code == 200 else None
        except Exception as e:
            logger.error(f"Erro ao buscar predições recentes: {e}")
            return None

class MQTTManager:
    """Gerenciador MQTT simplificado"""
    
    def __init__(self, device_manager, ml_server_url):
        self.device_manager = device_manager
        self.ml_client = MLServerClient(ml_server_url)
        self.client = None
        self.connected = False
        self.message_count = 0
        
        # Configuração MQTT
        self.broker = "broker.hivemq.com"
        self.port = 1883
        self.topic_base = "trash_ai"

        # Mapeamento de comandos ESP32
        self.esp32_commands = {
            'STATUS': 'STATUS',
            'MOVE_SERVO': 'MOVE_SERVO', 
            'WASTE_TYPE': 'WASTE_TYPE',
            'RESET': 'RESET',
            'PING': 'PING',
            'GET_INFO': 'STATUS'  # Comando para solicitar info completa
        }
        
        self._connect()
    
    def _connect(self):
        """Conecta ao broker MQTT"""
        try:
            self.client = mqtt.Client()
            self.client.on_connect = self._on_connect
            self.client.on_message = self._on_message
            self.client.on_disconnect = self._on_disconnect
            
            # Conectar em thread separada
            thread = threading.Thread(target=self._connect_thread)
            thread.daemon = True
            thread.start()
            
        except Exception as e:
            logger.error(f"Erro ao inicializar MQTT: {e}")
    
    def _connect_thread(self):
        """Thread de conexão MQTT"""
        try:
            self.client.connect(self.broker, self.port, 60)
            self.client.loop_start()
            logger.info(f"MQTT conectando a {self.broker}:{self.port}")
        except Exception as e:
            logger.error(f"Erro na conexão MQTT: {e}")
    
    def _on_connect(self, client, userdata, flags, rc):
        """Callback de conexão MQTT"""
        if rc == 0:
            self.connected = True
            logger.info("✅ MQTT conectado com sucesso")
            
            # Inscrever nos tópicos
            self.client.subscribe(f"{self.topic_base}/+/status")
            self.client.subscribe(f"{self.topic_base}/+/info")
            self.client.subscribe(f"{self.topic_base}/+/events")
            self.client.subscribe(f"{self.topic_base}/+/response")
            self.client.subscribe(f"{self.topic_base}/+/classification")
            
        else:
            self.connected = False
            logger.error(f"❌ Falha na conexão MQTT: código {rc}")
    
    def _on_message(self, client, userdata, msg):
        """Processa mensagens MQTT recebidas"""
        try:
            self.message_count += 1
            topic = msg.topic
            payload = msg.payload.decode('utf-8')
            
            logger.debug(f"📨 MQTT RX: {topic} -> {payload}")
            
            # Extrair device_id do tópico
            parts = topic.split('/')
            if len(parts) >= 2:
                device_id = parts[1]
                
                # Processar baseado no tipo de mensagem
                if topic.endswith('/status'):
                    self._handle_status_message(device_id, payload)
                elif topic.endswith('/info'):
                    self._handle_info_message(device_id, payload)
                elif topic.endswith('/events'):
                    self._handle_event_message(device_id, payload)
                elif topic.endswith('/response'):
                    self._handle_response_message(device_id, payload)
                elif topic.endswith('/classification'):
                    self._handle_classification_message(device_id, payload)
                    
        except Exception as e:
            logger.error(f"❌ Erro processando mensagem MQTT: {e}")
    
    def _handle_status_message(self, device_id, payload):
        """Processa mensagens de status"""
        try:
            data = json.loads(payload)
            
            # Atualizar dispositivo
            updates = {
                'status': 'online',
                'last_seen': datetime.now().isoformat(),
                'protocol': 'mqtt'
            }
            
            # Adicionar dados específicos se existirem
            if 'memory_free' in data:
                updates['memory_free'] = data['memory_free']
            if 'uptime' in data:
                updates['uptime'] = data['uptime']
            if 'firmware_version' in data:
                updates['firmware_version'] = data['firmware_version']
            
            self.device_manager.add_device(device_id, updates)
            self.device_manager.update_device(device_id, updates)
            
            logger.info(f"✅ Status atualizado: {device_id}")
            
        except json.JSONDecodeError:
            logger.warning(f"Payload de status não é JSON: {payload}")
        except Exception as e:
            logger.error(f"Erro processando status: {e}")
    
    def _handle_info_message(self, device_id, payload):
        """Processa informações completas do dispositivo"""
        try:
            data = json.loads(payload)
            
            updates = {
                'status': 'online',
                'last_seen': datetime.now().isoformat(),
                'hardware_info': data.get('hardware', {}),
                'system_info': data.get('system', {}),
                'config': data.get('config', {}),
                'firmware_version': data.get('firmware_version', '1.0.0'),
                'device_name': data.get('device_name', f'ESP32_{device_id[-6:]}')
            }
            
            self.device_manager.add_device(device_id, updates)
            self.device_manager.update_device(device_id, updates)
            
            logger.info(f"📋 Informações recebidas: {device_id}")
            
        except Exception as e:
            logger.error(f"Erro processando informações: {e}")
    
    def _handle_event_message(self, device_id, payload):
        """Processa eventos dos dispositivos"""
        try:
            data = json.loads(payload)
            event_type = data.get('type', 'unknown')
            
            if event_type == 'movement_detected':
                updates = {
                    'last_movement': datetime.now().isoformat(),
                    'classifications_count': self.device_manager.devices.get(device_id, {}).get('classifications_count', 0) + 1
                }
                self.device_manager.update_device(device_id, updates)
                logger.info(f"🚨 Movimento detectado: {device_id}")
            
        except Exception as e:
            logger.error(f"Erro processando evento: {e}")
    
    def _handle_response_message(self, device_id, payload):
        """Processa respostas dos dispositivos ESP32"""
        try:
            data = json.loads(payload)
            command = data.get('command', 'unknown')
            
            logger.info(f"📩 Resposta de {device_id}: {command}")
            
            # Atualizar dispositivo com dados da resposta
            if command == 'STATUS':
                self._update_device_from_status(device_id, data)
            elif command == 'PONG':
                updates = {
                    'status': 'online',
                    'last_seen': datetime.now().isoformat(),
                    'last_pong': datetime.now().isoformat()
                }
                self.device_manager.update_device(device_id, updates)
                
        except Exception as e:
            logger.error(f"Erro processando resposta: {e}")
    
    def _update_device_from_status(self, device_id, status_data):
        """Atualiza dispositivo com dados de status do ESP32"""
        updates = {
            'status': 'online',
            'last_seen': datetime.now().isoformat(),
            'hardware_info': status_data.get('hardware', {}),
            'system_info': status_data.get('system', {}),
            'memory': status_data.get('memory', {}),
            'firmware_version': status_data.get('firmware_version', '1.0.0'),
            'device_name': f"ESP32_{device_id[-6:]}"
        }
        
        self.device_manager.add_device(device_id, updates)
        self.device_manager.update_device(device_id, updates)
    
    def _handle_classification_message(self, device_id, payload):
        """Processa mensagens de classificação com ML"""
        try:
            data = json.loads(payload)
            features = data.get('features', [])
            
            if features:
                # Usar servidor ML para classificação
                prediction_result = self.ml_client.predict("waste_classifier", features)
                
                if prediction_result:
                    # Atualizar dispositivo
                    updates = {
                        'last_classification': datetime.now().isoformat(),
                        'classifications_count': self.device_manager.devices.get(device_id, {}).get('classifications_count', 0) + 1,
                        'last_prediction': prediction_result
                    }
                    self.device_manager.update_device(device_id, updates)
                    
                    # Mover servo baseado na classificação
                    predicted_class = prediction_result.get('result', {}).get('class', 'unknown')
                    waste_mapping = {
                        'plastic': 0, 'paper': 90, 'glass': 180, 
                        'metal': 270, 'organic': 45
                    }
                    angle = waste_mapping.get(predicted_class, 0)
                    
                    self.publish_command(device_id, 'MOVE_SERVO', {'angle': angle})
                    
                    logger.info(f"🎯 Classificação ML para {device_id}: {predicted_class} (ângulo: {angle}°)")
                    
                    # Publicar resultado
                    self.publish_command(device_id, 'CLASSIFICATION_RESULT', {
                        'prediction': prediction_result,
                        'servo_angle': angle
                    })
            
        except Exception as e:
            logger.error(f"Erro processando classificação: {e}")
    
    def _on_disconnect(self, client, userdata, rc):
        """Callback de desconexão MQTT"""
        self.connected = False
        if rc != 0:
            logger.warning("⚠️ MQTT desconectado inesperadamente")
        else:
            logger.info("✅ MQTT desconectado")
    
    def publish_command(self, device_id, command, params=None):
        """Publica comando no formato esperado pelo ESP32"""
        if not self.connected:
            logger.warning("❌ MQTT não conectado")
            return False
        
        try:
            topic = f"{self.topic_base}/{device_id}/control"
            
            # Formatar mensagem no padrão ESP32
            message = {
                'command': command,
                'params': params or {}
            }
            
            result = self.client.publish(topic, json.dumps(message))
            
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                logger.info(f"📤 Comando enviado para ESP32: {command} -> {device_id}")
                return True
            else:
                logger.error(f"❌ Erro enviando comando: código {result.rc}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Erro ao publicar comando: {e}")
            return False
    
    def request_device_info(self, device_id):
        """Solicita informações completas do dispositivo"""
        return self.publish_command(device_id, "GET_INFO")
    
    def classify_with_device(self, device_id, features, move_servo=True):
        """Classifica usando ML e controla dispositivo"""
        try:
            # Fazer predição no servidor ML
            prediction_result = self.ml_client.predict("waste_classifier", features)
            
            if not prediction_result:
                return None
            
            # Atualizar dispositivo local
            updates = {
                'last_classification': datetime.now().isoformat(),
                'classifications_count': self.device_manager.devices.get(device_id, {}).get('classifications_count', 0) + 1,
                'last_prediction': prediction_result
            }
            self.device_manager.update_device(device_id, updates)
            
            # Mover servo se solicitado
            if move_servo:
                predicted_class = prediction_result.get('result', {}).get('class', 'unknown')
                waste_mapping = {
                    'plastic': 0, 'paper': 90, 'glass': 180, 
                    'metal': 270, 'organic': 45
                }
                angle = waste_mapping.get(predicted_class, 0)
                
                self.publish_command(device_id, 'MOVE_SERVO', {'angle': angle})
            
            return prediction_result
            
        except Exception as e:
            logger.error(f"Erro na classificação com dispositivo: {e}")
            return None
    
    def get_status(self):
        """Retorna status do MQTT"""
        return {
            'connected': self.connected,
            'broker': f"{self.broker}:{self.port}",
            'message_count': self.message_count,
            'devices_count': len(self.device_manager.devices)
        }

# Filtros para templates
def format_datetime(value):
    try:
        if value:
            return datetime.fromisoformat(value).strftime("%d/%m/%Y %H:%M:%S")
    except:
        pass
    return "—"

def format_filesize(size):
    try:
        if size is None:
            return "0 B"
        size = float(size)
        for unit in ["B", "KB", "MB", "GB"]:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"
    except:
        return "—"

def format_uptime(seconds):
    try:
        days = seconds // (24 * 3600)
        seconds %= (24 * 3600)
        hours = seconds // 3600
        seconds %= 3600
        minutes = seconds // 60
        seconds %= 60
        
        if days > 0:
            return f"{int(days)}d {int(hours)}h {int(minutes)}m"
        elif hours > 0:
            return f"{int(hours)}h {int(minutes)}m {int(seconds)}s"
        else:
            return f"{int(minutes)}m {int(seconds)}s"
    except:
        return "—"

def create_app():
    app = Flask(__name__)
    app.secret_key = "trashnet_dashboard_secret_2024"
    
    # Configurar filtros de template
    app.jinja_env.filters["datetime"] = format_datetime
    app.jinja_env.filters["filesize"] = format_filesize
    app.jinja_env.filters["uptime"] = format_uptime
    
    # Configuração do servidor ML
    ml_server_url = "http://localhost:8000"
    
    # Inicializar gerenciadores
    device_manager = DeviceManager()
    mqtt_manager = MQTTManager(device_manager, ml_server_url)
    ml_client = MLServerClient(ml_server_url)
    
    # Armazenar no app context
    app.device_manager = device_manager
    app.mqtt_manager = mqtt_manager
    app.ml_client = ml_client
    app.ml_server_url = ml_server_url
    
    # Configurações
    app.config["PROPAGATE_EXCEPTIONS"] = True
    app.config["JSON_SORT_KEYS"] = False
    app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 300
    
    # Importar e registrar blueprints
    from src.web.api import api_bp
    from src.web.views import views_bp
    app.register_blueprint(views_bp)
    app.register_blueprint(api_bp, url_prefix="/api")
    
    # Error handlers
    @app.errorhandler(404)
    def not_found(error):
        return render_template("error.html", 
                             error_code=404,
                             error_message="Página não encontrada"), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        return render_template("error.html",
                             error_code=500,
                             error_message="Erro interno do servidor"), 500
    
    # Rota de health check
    @app.route("/health")
    def health():
        return jsonify({
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "ml_server": ml_server_url
        })
    
    return app