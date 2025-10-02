# main.py - Servidor principal atualizado para ESP32
import time
import threading
import queue
import sys
import json
from classification_service import CLASSIFICATION_SERVICE
from server_communicator import SERVER_COMMUNICATOR
from web_dashboard import WEB_DASHBOARD
from database import ClassificationDB
from device_registry import DEVICE_REGISTRY
from utils import get_logger

logger = get_logger("TrashNetServer")

class TrashNetServer:
    def __init__(self):
        self.communicator = SERVER_COMMUNICATOR
        self.db = ClassificationDB()
        self.running = True
        
        # Fila para processamento de classificações
        self.classification_queue = queue.Queue()
        
        # Thread para processar classificações
        self.classification_thread = threading.Thread(target=self._classification_processor, daemon=True)

    def start(self):
        """Iniciar servidor com verificações"""
        logger.info("🚀 Iniciando Servidor TrashNet para ESP32...")
        
        # Verificar inicialização do serviço
        if not CLASSIFICATION_SERVICE.model:
            logger.error("❌ Serviço de classificação não inicializado corretamente")
            logger.info("💡 Dica: Execute em modo de teste ou adicione modelo treinado")
        
        # Iniciar componentes
        try:
            # Configurar callback para movimento detectado
            self.communicator.set_movement_callback(self._handle_movement_detected)
            
            # Iniciar componentes
            self.communicator.start()
            WEB_DASHBOARD.start()
            self.classification_thread.start()
            
            logger.success("✅ Servidor TrashNet iniciado com sucesso!")
            logger.info("📊 Dashboard: http://localhost:5000")
            logger.info("📡 Aguardando dispositivos ESP32...")
            logger.info("⏹️  Pressione Ctrl+C para parar")

            # Loop principal
            while self.running:
                time.sleep(1)
                
        except Exception as e:
            logger.error(f"❌ Erro ao iniciar servidor: {e}")
            self.stop()

    def stop(self):
        """Parar servidor gracefulmente"""
        self.running = False
        self.communicator.stop()
        logger.info("🛑 Servidor TrashNet parado")

    def _classification_processor(self):
        """Processar classificações na fila"""
        while self.running:
            try:
                if not self.classification_queue.empty():
                    device_id, device_ip = self.classification_queue.get_nowait()
                    self._process_classification(device_id, device_ip)
                else:
                    time.sleep(0.1)
            except Exception as e:
                logger.error(f"Erro no processador de classificação: {e}")
                time.sleep(1)

    def _handle_movement_detected(self, device_id, device_ip):
        """Manipular detecção de movimento do dispositivo"""
        logger.info(f"🎯 Movimento detectado pelo dispositivo {device_id}")
        self.classification_queue.put((device_id, device_ip))

    def _process_classification(self, device_id, device_ip):
        """Processar classificação para dispositivo específico"""
        try:
            device_info = DEVICE_REGISTRY.get_device(device_id)
            if not device_info:
                logger.error(f"Dispositivo {device_id} não encontrado no registro")
                return

            device_name = device_info.get('device_name', device_id)
            logger.info(f"🔍 Iniciando classificação para {device_name}")
            
            # Executar classificação
            result = CLASSIFICATION_SERVICE.classify_waste()
            
            if result:
                # Salvar no banco
                self.db.save_classification(result)
                
                # Enviar comando para o dispositivo
                command = f"WASTE_TYPE:{result['system_index']}:{result['system_class']}"
                success = self.communicator.send_to_device(device_id, command)
                
                if success:
                    icon = "🎭" if result.get('is_mock') else "✅"
                    logger.success(
                        f"{icon} Resíduo classificado para {device_name}: "
                        f"{result['system_class']} (Confiança: {result['confidence']:.2%})"
                    )
                    
                    # Enviar status atualizado
                    status_update = f"CLASSIFICATION_RESULT:{json.dumps(result)}"
                    self.communicator.send_to_device(device_id, status_update)
                else:
                    logger.error(f"❌ Falha ao enviar comando para {device_name}")
                
            else:
                logger.warning(f"❌ Classificação falhou para {device_name}")
                self.communicator.send_to_device(device_id, "WASTE_TYPE:-1:INDETERMINADO")
                
        except Exception as e:
            logger.error(f"❌ Erro ao processar classificação para {device_id}: {e}")
            self.communicator.send_to_device(device_id, "WASTE_TYPE:-1:ERRO")

    def send_system_command(self, device_id, command):
        """Enviar comando de sistema para dispositivo"""
        try:
            if command == "RESTART":
                return self.communicator.send_to_device(device_id, "SYSTEM_COMMAND:RESTART")
            elif command == "STATUS":
                return self.communicator.send_to_device(device_id, "SYSTEM_COMMAND:STATUS")
            elif command == "DISCOVER":
                return self.communicator.send_to_device(device_id, "SYSTEM_COMMAND:DISCOVER")
            elif command == "GET_INFO":
                return self.communicator.send_to_device(device_id, "SYSTEM_COMMAND:GET_INFO")
            else:
                logger.warning(f"Comando não reconhecido: {command}")
                return False
                
        except Exception as e:
            logger.error(f"Erro ao enviar comando para {device_id}: {e}")
            return False

    def get_system_status(self):
        """Obter status completo do sistema"""
        comm_stats = self.communicator.get_communication_stats()
        service_status = CLASSIFICATION_SERVICE.get_status()
        db_stats = self.db.get_statistics()
        
        return {
            'server': {
                'running': self.running,
                'status': 'operational'
            },
            'communication': comm_stats,
            'classification_service': service_status,
            'database': db_stats
        }

# Instância global do servidor
TRASH_NET_SERVER = TrashNetServer()

def main():
    """Função principal com tratamento de erro"""
    server = TRASH_NET_SERVER
    
    try:
        # Iniciar servidor
        server.start()
        
    except KeyboardInterrupt:
        logger.info("👋 Interrompido pelo usuário")
    except Exception as e:
        logger.error(f"💥 Erro fatal: {e}")
    finally:
        server.stop()
        sys.exit(0)

if __name__ == "__main__":
    main()