# web_dashboard.py - Dashboard atualizado para múltiplos dispositivos
from flask import Flask, render_template, jsonify, request
import threading
import time
from datetime import datetime
from database import ClassificationDB
from classification_service import CLASSIFICATION_SERVICE
from device_registry import DEVICE_REGISTRY
from server_communicator import SERVER_COMMUNICATOR
from main import TRASH_NET_SERVER
from utils import get_logger

logger = get_logger("WebDashboard")

class WebDashboard:
    def __init__(self, host='0.0.0.0', port=5000):
        self.app = Flask(__name__)
        self.host = host
        self.port = port
        self.db = ClassificationDB()
        self.start_time = datetime.now()
        self.setup_routes()

    def setup_routes(self):
        @self.app.route('/')
        def index():
            return render_template('dashboard.html')

        @self.app.route('/api/devices')
        def get_devices():
            devices = DEVICE_REGISTRY.get_device_stats()
            return jsonify(devices)

        @self.app.route('/api/devices/<device_id>/command', methods=['POST'])
        def send_device_command(device_id):
            command = request.json.get('command')
            if command:
                success = TRASH_NET_SERVER.send_system_command(device_id, command)
                return jsonify({'success': success, 'command': command})
            return jsonify({'success': False, 'error': 'No command provided'})

        @self.app.route('/api/system/status')
        def get_system_status():
            status = TRASH_NET_SERVER.get_system_status()
            return jsonify(status)

        @self.app.route('/api/classifications')
        def get_classifications():
            classifications = self.db.get_recent_classifications(50)
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
                    'model_type': 'unknown'
                }
                for row in classifications
            ])

        @self.app.route('/api/statistics')
        def get_statistics():
            stats = self.db.get_statistics()
            stats['server_uptime'] = str(datetime.now() - self.start_time).split('.')[0]
            stats['device_count'] = len(DEVICE_REGISTRY.get_connected_devices())
            return jsonify(stats)

        @self.app.route('/api/classify_now')
        def classify_now():
            """Endpoint para forçar classificação"""
            # Esta é uma classificação manual, não associada a um dispositivo específico
            start_time = time.time()
            result = CLASSIFICATION_SERVICE.classify_waste()
            processing_time = time.time() - start_time
            
            if result:
                self.db.save_classification(result)
                return jsonify({
                    'success': True, 
                    'result': result,
                    'processing_time': processing_time
                })
            else:
                return jsonify({
                    'success': False, 
                    'error': 'Classification failed',
                    'processing_time': processing_time
                })

        @self.app.route('/api/discover_devices')
        def discover_devices():
            """Forçar descoberta de dispositivos"""
            # O servidor já faz descoberta automática, esta é apenas para forçar
            SERVER_COMMUNICATOR.broadcast_to_devices("HEARTBEAT_REQUEST")
            return jsonify({'success': True, 'message': 'Discovery broadcast sent'})

    def start(self):
        """Iniciar dashboard web"""
        def run():
            logger.info(f"🌐 Dashboard web iniciado em http://{self.host}:{self.port}")
            self.app.run(host=self.host, port=self.port, debug=False, use_reloader=False)
        
        thread = threading.Thread(target=run, daemon=True)
        thread.start()

# Instância global
WEB_DASHBOARD = WebDashboard()