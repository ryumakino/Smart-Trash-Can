# web_dashboard.py - Dashboard web (Refatorado)
from flask import Flask, render_template, jsonify, request
import threading
import time
from datetime import datetime
from src.core.base_classes import BaseService, ConfigurableMixin

class WebDashboard(BaseService, ConfigurableMixin):
    def __init__(self):
        super().__init__('server')
        self.host = self.get_config_value('HOST', '0.0.0.0')
        self.port = self.get_config_value('PORT', 5000)
        
        self.app = Flask(__name__)
        self.app.secret_key = self.get_config_value('SECRET_KEY', 'trashnet_server_secret_2024')
        self.db = None
        self.start_time = datetime.now()
        
        self.setup_routes()

    def initialize(self):
        """Inicializar dashboard web"""
        if self._initialized:
            return True
            
        try:
            from src.services.database import ClassificationDB
            self.db = ClassificationDB()
            self.db.initialize()
            
            self._initialized = True
            self.logger.success("✅ WebDashboard inicializado")
            return True
        except Exception as e:
            self.logger.error(f"❌ Erro na inicialização: {e}")
            return False

    def setup_routes(self):
        """Configurar rotas da aplicação Flask"""
        
        @self.app.before_request
        def log_request_info():
            """Log de todas as requisições"""
            self.logger.debug(f"📥 Request: {request.method} {request.path}")

        @self.app.route('/')
        def index():
            """Página principal"""
            self.logger.info("📄 Servindo página principal")
            return render_template('dashboard.html')

        @self.app.route('/api/status')
        def api_status():
            """API de status do sistema"""
            self.logger.info("📊 API Status solicitada")
            try:
                from src.core.app_config import get_trash_net_server
                trash_net_server = get_trash_net_server()
                if trash_net_server:
                    status = trash_net_server.get_system_status()
                    self.logger.info("✅ Status retornado com sucesso")
                    return jsonify(status)
                else:
                    self.logger.error("❌ Servidor não disponível")
                    return jsonify({
                        'status': 'error',
                        'message': 'Server not available',
                        'timestamp': datetime.now().isoformat()
                    }), 500
            except Exception as e:
                self.logger.error(f"❌ Erro no /api/status: {e}")
                return jsonify({
                    'status': 'error',
                    'message': str(e),
                    'timestamp': datetime.now().isoformat()
                }), 500

        @self.app.route('/api/system_info')
        def api_system_info():
            """API de informações do sistema"""
            self.logger.info("🔧 API System Info solicitada")
            try:
                from src.utils.utils import get_system_info
                system_info = get_system_info()
                self.logger.info("✅ System Info retornado com sucesso")
                return jsonify(system_info)
            except Exception as e:
                self.logger.error(f"❌ Erro no /api/system_info: {e}")
                return jsonify({
                    'error': str(e),
                    'timestamp': datetime.now().isoformat()
                }), 500

        @self.app.route('/api/devices')
        def get_devices():
            """API para listar dispositivos"""
            self.logger.info("📱 API Devices solicitada")
            try:
                from src.core.app_config import get_device_registry
                device_registry = get_device_registry()
                devices = device_registry.get_device_stats()
                self.logger.info(f"✅ Devices retornado: {len(devices.get('device_list', []))} dispositivos")
                return jsonify(devices)
            except Exception as e:
                self.logger.error(f"❌ Erro no /api/devices: {e}")
                return jsonify({
                    'error': str(e),
                    'timestamp': datetime.now().isoformat()
                }), 500

        @self.app.route('/api/statistics')
        def get_statistics():
            """API para obter estatísticas"""
            self.logger.info("📈 API Statistics solicitada")
            try:
                if not self.db:
                    from src.services.database import ClassificationDB
                    self.db = ClassificationDB()
                    
                stats = self.db.get_statistics()
                from src.core.app_config import get_device_registry
                device_registry = get_device_registry()
                stats['server_uptime'] = str(datetime.now() - self.start_time).split('.')[0]
                stats['device_count'] = len(device_registry.get_connected_devices())
                
                # Adicionar informações do sistema
                from src.utils.utils import get_system_info
                stats['system_info'] = get_system_info()
                
                self.logger.info("✅ Statistics retornado com sucesso")
                return jsonify(stats)
            except Exception as e:
                self.logger.error(f"❌ Erro no /api/statistics: {e}")
                return jsonify({
                    'error': str(e),
                    'timestamp': datetime.now().isoformat()
                }), 500

        @self.app.route('/api/classifications')
        def get_classifications():
            """API para obter classificações recentes"""
            self.logger.info("🗂️ API Classifications solicitada")
            try:
                if not self.db:
                    from src.services.database import ClassificationDB
                    self.db = ClassificationDB()
                    
                classifications = self.db.get_recent_classifications(50)
                self.logger.info(f"✅ Classifications retornado: {len(classifications)} classificações")
                return jsonify([
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
                    for row in classifications
                ])
            except Exception as e:
                self.logger.error(f"❌ Erro no /api/classifications: {e}")
                return jsonify({
                    'error': str(e),
                    'timestamp': datetime.now().isoformat()
                }), 500

        @self.app.route('/api/classify_now', methods=['GET', 'POST'])
        def classify_now():
            """Endpoint para forçar classificação"""
            self.logger.info("🤖 API Classify Now solicitada")
            try:
                start_time = time.time()
                from src.core.app_config import get_classification_service
                classification_service = get_classification_service()
                result = classification_service.classify_waste()
                processing_time = time.time() - start_time
                
                if result:
                    if not self.db:
                        from src.services.database import ClassificationDB
                        self.db = ClassificationDB()
                    self.db.save_classification(result)
                    self.logger.info(f"✅ Classificação realizada: {result['system_class']}")
                    return jsonify({
                        'success': True, 
                        'result': result,
                        'processing_time': processing_time
                    })
                else:
                    self.logger.warning("⚠️ Classificação falhou")
                    return jsonify({
                        'success': False, 
                        'error': 'Classification failed',
                        'processing_time': processing_time
                    }), 500
            except Exception as e:
                self.logger.error(f"❌ Erro no /api/classify_now: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e),
                    'processing_time': 0
                }), 500

        @self.app.route('/api/discover_devices', methods=['GET', 'POST'])
        def discover_devices():
            """Forçar descoberta de dispositivos"""
            self.logger.info("🔍 API Discover Devices solicitada")
            try:
                from src.core.app_config import get_server_communicator
                server_communicator = get_server_communicator()
                server_communicator.broadcast_to_devices("HEARTBEAT_REQUEST")
                self.logger.info("✅ Discovery broadcast enviado")
                return jsonify({'success': True, 'message': 'Discovery broadcast sent'})
            except Exception as e:
                self.logger.error(f"❌ Erro no /api/discover_devices: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500

        @self.app.route('/api/config', methods=['GET', 'POST'])
        def handle_config():
            """API para gerenciar configuração"""
            self.logger.info("⚙️ API Config solicitada")
            try:
                from src.config.config_manager import CONFIG_MANAGER
                if request.method == 'GET':
                    config = CONFIG_MANAGER.get_all_config()
                    # Remover chaves sensíveis
                    if 'AUTH_KEY' in config.get('NetworkConfig', {}):
                        config['NetworkConfig']['AUTH_KEY'] = '***HIDDEN***'
                    self.logger.info("✅ Config retornado com sucesso")
                    return jsonify(config)
                
                elif request.method == 'POST':
                    new_config = request.get_json()
                    if CONFIG_MANAGER.update_config(new_config):
                        self.logger.info("✅ Config atualizado com sucesso")
                        return jsonify({'success': True, 'message': 'Configuração atualizada'})
                    else:
                        self.logger.error("❌ Erro ao salvar configuração")
                        return jsonify({'success': False, 'error': 'Erro ao salvar configuração'}), 500
                        
            except Exception as e:
                self.logger.error(f"❌ Erro no /api/config: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500

        @self.app.route('/api/health')
        def health_check():
            """Health check endpoint"""
            self.logger.debug("❤️ Health check solicitado")
            return jsonify({
                'status': 'healthy',
                'timestamp': datetime.now().isoformat(),
                'uptime': str(datetime.now() - self.start_time)
            })

        # Error handlers
        @self.app.errorhandler(404)
        def not_found(error):
            self.logger.warning(f"❌ 404 - Endpoint não encontrado: {request.path}")
            return jsonify({
                'error': 'Endpoint not found',
                'path': request.path,
                'timestamp': datetime.now().isoformat()
            }), 404

        @self.app.errorhandler(500)
        def internal_error(error):
            self.logger.error(f"💥 500 - Erro interno no servidor: {error}")
            return jsonify({
                'error': 'Internal server error',
                'timestamp': datetime.now().isoformat()
            }), 500

    def start(self):
        """Iniciar dashboard web"""
        if not self.initialize():
            return False
            
        def run():
            try:
                self.logger.info(f"Dashboard web iniciado em http://{self.host}:{self.port}")
                debug_mode = self.get_config_value('DEBUG', False)
                self.app.run(host=self.host, port=self.port, debug=debug_mode, use_reloader=False)
            except Exception as e:
                self.logger.error(f"Erro ao iniciar dashboard: {e}")
        
        thread = threading.Thread(target=run, daemon=True)
        thread.start()
        return True

    def get_status(self):
        """Obter status do dashboard web"""
        base_status = super().get_status()
        base_status.update({
            'host': self.host,
            'port': self.port,
            'uptime': str(datetime.now() - self.start_time),
            'flask_running': True
        })
        return base_status