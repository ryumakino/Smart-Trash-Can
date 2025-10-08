# web_dashboard.py - Dashboard web (Refatorado)
from flask import Flask, render_template, jsonify, request
import threading
import time
import sys
import os
from datetime import datetime

# Adicionar o diretório pai ao path para imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

class WebDashboard:
    def __init__(self):
        self.host = '0.0.0.0'
        self.port = 5000
        
        self.app = Flask(__name__)
        self.app.secret_key = 'trashnet_server_secret_2024'
        self.db = None
        self.start_time = datetime.now()
        self._initialized = False
        
        # Logger simplificado
        self.logger = self._setup_logger()
        
        self.setup_routes()

    def _setup_logger(self):
        """Logger simplificado"""
        class SimpleLogger:
            def info(self, msg): print(f"[WebDashboard] 📝 {msg}")
            def error(self, msg): print(f"[WebDashboard] ❌ {msg}")
            def warning(self, msg): print(f"[WebDashboard] ⚠️ {msg}")
            def success(self, msg): print(f"[WebDashboard] ✅ {msg}")
            def debug(self, msg): print(f"[WebDashboard] 🔍 {msg}")
        return SimpleLogger()

    def initialize(self):
        """Inicializar dashboard web"""
        if self._initialized:
            return True
            
        try:
            # Tentar importar o banco de dados se disponível
            try:
                from services.database import ClassificationDB
                self.db = ClassificationDB()
                if hasattr(self.db, 'initialize'):
                    self.db.initialize()
            except ImportError:
                self.logger.warning("Database não disponível - continuando sem DB")
            
            self._initialized = True
            self.logger.success("WebDashboard inicializado")
            return True
        except Exception as e:
            self.logger.error(f"Erro na inicialização: {e}")
            return False

    def setup_routes(self):
        """Configurar rotas da aplicação Flask"""
        
        @self.app.before_request
        def log_request_info():
            """Log de todas as requisições"""
            self.logger.debug(f"Request: {request.method} {request.path}")

        @self.app.route('/')
        def index():
            """Página principal"""
            self.logger.info("Servindo página principal")
            return render_template('dashboard.html')

        @self.app.route('/api/status')
        def api_status():
            """API de status do sistema"""
            self.logger.info("API Status solicitada")
            try:
                # Status básico do servidor
                status = {
                    'status': 'operational',
                    'timestamp': datetime.now().isoformat(),
                    'server_uptime': str(datetime.now() - self.start_time),
                    'services': {
                        'web_dashboard': 'running',
                        'api': 'available'
                    }
                }
                self.logger.info("Status retornado com sucesso")
                return jsonify(status)
            except Exception as e:
                self.logger.error(f"Erro no /api/status: {e}")
                return jsonify({
                    'status': 'error',
                    'message': str(e),
                    'timestamp': datetime.now().isoformat()
                }), 500

        @self.app.route('/api/system_info')
        def api_system_info():
            """API de informações do sistema"""
            self.logger.info("API System Info solicitada")
            try:
                system_info = {
                    'python_version': sys.version,
                    'platform': sys.platform,
                    'server_time': datetime.now().isoformat(),
                    'start_time': self.start_time.isoformat()
                }
                self.logger.info("System Info retornado com sucesso")
                return jsonify(system_info)
            except Exception as e:
                self.logger.error(f"Erro no /api/system_info: {e}")
                return jsonify({
                    'error': str(e),
                    'timestamp': datetime.now().isoformat()
                }), 500

        @self.app.route('/api/devices')
        def get_devices():
            """API para listar dispositivos"""
            self.logger.info("API Devices solicitada")
            try:
                # Buscar dispositivos do ServerCommunicator se disponível
                devices = self._get_esp32_devices()
                
                response = {
                    'device_list': list(devices.values()),
                    'total_devices': len(devices),
                    'connected_devices': sum(1 for d in devices.values() if d.get('connected', False)),
                    'timestamp': datetime.now().isoformat()
                }
                
                self.logger.info(f"Devices retornado: {len(devices)} dispositivos")
                return jsonify(response)
            except Exception as e:
                self.logger.error(f"Erro no /api/devices: {e}")
                return jsonify({
                    'error': str(e),
                    'device_list': [],
                    'timestamp': datetime.now().isoformat()
                }), 500

        @self.app.route('/api/statistics')
        def get_statistics():
            """API para obter estatísticas"""
            self.logger.info("API Statistics solicitada")
            try:
                stats = {
                    'total_classifications': 0,
                    'by_class': [],
                    'hourly_data': [],
                    'server_uptime': str(datetime.now() - self.start_time).split('.')[0],
                    'device_count': len(self._get_esp32_devices())
                }
                
                # Tentar obter estatísticas do banco se disponível
                if self.db and hasattr(self.db, 'get_statistics'):
                    try:
                        db_stats = self.db.get_statistics()
                        stats.update(db_stats)
                    except Exception as e:
                        self.logger.warning(f"Erro ao obter stats do DB: {e}")
                
                self.logger.info("Statistics retornado com sucesso")
                return jsonify(stats)
            except Exception as e:
                self.logger.error(f"Erro no /api/statistics: {e}")
                return jsonify({
                    'error': str(e),
                    'timestamp': datetime.now().isoformat()
                }), 500

        @self.app.route('/api/classifications')
        def get_classifications():
            """API para obter classificações recentes"""
            self.logger.info("API Classifications solicitada")
            try:
                classifications = []
                
                # Tentar obter do banco se disponível
                if self.db and hasattr(self.db, 'get_recent_classifications'):
                    try:
                        db_classifications = self.db.get_recent_classifications(50)
                        classifications = [
                            {
                                'id': row[0],
                                'timestamp': row[1],
                                'original_class': row[2],
                                'system_class': row[3],
                                'system_index': row[4],
                                'confidence': row[5],
                                'image_path': row[6],
                                'processing_time': row[7],
                                'model_type': row[8] if len(row) > 8 else 'unknown'
                            }
                            for row in db_classifications
                        ]
                    except Exception as e:
                        self.logger.warning(f"Erro ao obter classifications do DB: {e}")
                
                self.logger.info(f"Classifications retornado: {len(classifications)} classificações")
                return jsonify(classifications)
            except Exception as e:
                self.logger.error(f"Erro no /api/classifications: {e}")
                return jsonify({
                    'error': str(e),
                    'timestamp': datetime.now().isoformat()
                }), 500

        @self.app.route('/api/classify_now', methods=['GET', 'POST'])
        def classify_now():
            """Endpoint para forçar classificação"""
            self.logger.info("API Classify Now solicitada")
            try:
                # Simular classificação (substitua pela lógica real)
                result = {
                    'system_class': 'Plástico',
                    'confidence': 0.85,
                    'processing_time': 1.2,
                    'timestamp': datetime.now().isoformat()
                }
                
                # Salvar no banco se disponível
                if self.db and hasattr(self.db, 'save_classification'):
                    try:
                        self.db.save_classification(result)
                    except Exception as e:
                        self.logger.warning(f"Erro ao salvar classificação: {e}")
                
                self.logger.info(f"Classificação realizada: {result['system_class']}")
                return jsonify({
                    'success': True, 
                    'result': result,
                    'processing_time': result['processing_time']
                })
                
            except Exception as e:
                self.logger.error(f"Erro no /api/classify_now: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e),
                    'processing_time': 0
                }), 500

        @self.app.route('/api/discover_devices', methods=['GET', 'POST'])
        def discover_devices():
            """Forçar descoberta de dispositivos"""
            self.logger.info("API Discover Devices solicitada")
            try:
                server_communicator = self._get_server_communicator()
                if server_communicator:
                    server_communicator.broadcast_discovery()
                    self.logger.info("Discovery broadcast enviado")
                    return jsonify({'success': True, 'message': 'Discovery broadcast sent'})
                else:
                    self.logger.warning("ServerCommunicator não disponível")
                    return jsonify({'success': False, 'error': 'ServerCommunicator not available'})
                    
            except Exception as e:
                self.logger.error(f"Erro no /api/discover_devices: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500

        # ========== NOVAS ROTAS PARA ESP32 ==========

        @self.app.route('/api/esp32_devices')
        def get_esp32_devices():
            """API para listar dispositivos ESP32 conectados"""
            self.logger.info("API ESP32 Devices solicitada")
            try:
                server_communicator = self._get_server_communicator()
                
                if server_communicator:
                    devices = server_communicator.get_connected_devices()
                    server_stats = server_communicator.get_server_stats()
                    
                    response = {
                        'devices': devices,
                        'server_stats': server_stats,
                        'total_devices': len(devices),
                        'timestamp': datetime.now().isoformat()
                    }
                    
                    self.logger.info(f"ESP32 Devices retornado: {len(devices)} dispositivos")
                    return jsonify(response)
                else:
                    self.logger.warning("ServerCommunicator não disponível")
                    return jsonify({
                        'error': 'ServerCommunicator not available',
                        'devices': {},
                        'server_stats': {},
                        'timestamp': datetime.now().isoformat()
                    })
                    
            except Exception as e:
                self.logger.error(f"Erro no /api/esp32_devices: {e}")
                return jsonify({
                    'error': str(e),
                    'devices': {},
                    'server_stats': {},
                    'timestamp': datetime.now().isoformat()
                }), 500

        @self.app.route('/api/esp32/send_command', methods=['POST'])
        def send_esp32_command():
            """API para enviar comandos para ESP32"""
            self.logger.info("API Send ESP32 Command solicitada")
            try:
                data = request.get_json()
                device_id = data.get('device_id')
                command_type = data.get('command_type')
                command_data = data.get('command_data', {})
                
                if not device_id or not command_type:
                    return jsonify({
                        'success': False,
                        'error': 'device_id e command_type são obrigatórios'
                    }), 400
                
                server_communicator = self._get_server_communicator()
                if not server_communicator:
                    return jsonify({
                        'success': False,
                        'error': 'ServerCommunicator não disponível'
                    }), 500
                
                success = False
                message = ""
                
                if command_type == 'WASTE_COMMAND':
                    waste_index = command_data.get('waste_index', 0)
                    waste_name = command_data.get('waste_name', f'Tipo {waste_index}')
                    success = server_communicator.send_waste_command(device_id, waste_index, waste_name)
                    message = f"Comando de resíduo enviado para {device_id}"
                    
                elif command_type == 'SYSTEM_COMMAND':
                    command = command_data.get('command', 'STATUS')
                    success = server_communicator.send_system_command(device_id, command)
                    message = f"Comando de sistema {command} enviado para {device_id}"
                    
                elif command_type == 'DISCOVERY':
                    success = server_communicator.broadcast_discovery()
                    message = "Broadcast discovery enviado"
                    
                else:
                    message = f"Tipo de comando não suportado: {command_type}"
                
                if success:
                    self.logger.success(message)
                    return jsonify({
                        'success': True,
                        'message': message
                    })
                else:
                    self.logger.error(message)
                    return jsonify({
                        'success': False,
                        'error': message
                    }), 500
                    
            except Exception as e:
                self.logger.error(f"Erro no /api/esp32/send_command: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500

        @self.app.route('/api/esp32/setup_config', methods=['POST'])
        def setup_esp32_config():
            """API para enviar configurações para ESP32"""
            self.logger.info("API Setup ESP32 Config solicitada")
            try:
                data = request.get_json()
                device_id = data.get('device_id')
                config_data = data.get('config', {})
                
                if not device_id or not config_data:
                    return jsonify({
                        'success': False,
                        'error': 'device_id e config são obrigatórios'
                    }), 400
                
                server_communicator = self._get_server_communicator()
                if not server_communicator:
                    return jsonify({
                        'success': False,
                        'error': 'ServerCommunicator não disponível'
                    }), 500
                
                # Verificar se o dispositivo existe
                devices = server_communicator.get_connected_devices()
                if device_id not in devices:
                    return jsonify({
                        'success': False,
                        'error': f'Dispositivo {device_id} não encontrado'
                    }), 404
                
                # Enviar configuração para o ESP32
                setup_msg = {
                    'type': 'SETUP_CONFIG',
                    'config': config_data,
                    'restart_required': data.get('restart_required', False),
                    'timestamp': time.time()
                }
                
                device_info = devices[device_id]
                ip = device_info.get('ip_address')
                
                if ip:
                    success = server_communicator._send_to_esp32(setup_msg, ip)
                    if success:
                        self.logger.success(f"Configuração enviada para {device_id}")
                        return jsonify({
                            'success': True,
                            'message': f'Configuração enviada para {device_id}'
                        })
                    else:
                        self.logger.error(f"Falha ao enviar configuração para {device_id}")
                        return jsonify({
                            'success': False,
                            'error': f'Falha ao enviar configuração para {device_id}'
                        }), 500
                else:
                    return jsonify({
                        'success': False,
                        'error': f'IP não encontrado para {device_id}'
                    }), 500
                    
            except Exception as e:
                self.logger.error(f"Erro no /api/esp32/setup_config: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500

        @self.app.route('/api/health')
        def health_check():
            """Health check endpoint"""
            self.logger.debug("Health check solicitado")
            return jsonify({
                'status': 'healthy',
                'timestamp': datetime.now().isoformat(),
                'uptime': str(datetime.now() - self.start_time)
            })

        # Error handlers
        @self.app.errorhandler(404)
        def not_found(error):
            self.logger.warning(f"404 - Endpoint não encontrado: {request.path}")
            return jsonify({
                'error': 'Endpoint not found',
                'path': request.path,
                'timestamp': datetime.now().isoformat()
            }), 404

        @self.app.errorhandler(500)
        def internal_error(error):
            self.logger.error(f"500 - Erro interno no servidor: {error}")
            return jsonify({
                'error': 'Internal server error',
                'timestamp': datetime.now().isoformat()
            }), 500

    def _get_server_communicator(self):
        """Obter instância do ServerCommunicator se disponível"""
        try:
            # Tentar importar de forma relativa
            from src.services.server_communicator import ServerCommunicator
            # Esta é uma instância global - você precisará ajustar conforme sua implementação
            return ServerCommunicator()
        except ImportError:
            try:
                # Tentar importar de outro local
                from src.services.server_communicator import ServerCommunicator
                return ServerCommunicator()
            except ImportError:
                self.logger.warning("ServerCommunicator não disponível")
                return None

    def _get_esp32_devices(self):
        """Obter dispositivos ESP32"""
        server_communicator = self._get_server_communicator()
        if server_communicator:
            return server_communicator.get_connected_devices()
        return {}

    def start(self):
        """Iniciar dashboard web"""
        if not self.initialize():
            return False
            
        def run():
            try:
                self.logger.info(f"Dashboard web iniciado em http://{self.host}:{self.port}")
                self.app.run(host=self.host, port=self.port, debug=False, use_reloader=False)
            except Exception as e:
                self.logger.error(f"Erro ao iniciar dashboard: {e}")
        
        thread = threading.Thread(target=run, daemon=True)
        thread.start()
        return True

    def get_status(self):
        """Obter status do dashboard web"""
        return {
            'host': self.host,
            'port': self.port,
            'uptime': str(datetime.now() - self.start_time),
            'flask_running': True,
            'initialized': self._initialized
        }

# Para teste direto
if __name__ == "__main__":
    dashboard = WebDashboard()
    dashboard.start()
    
    # Manter o thread principal vivo
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Dashboard encerrado")