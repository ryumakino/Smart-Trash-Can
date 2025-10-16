#!/usr/bin/env python3
"""
TrashNet Server - Servidor de Classificação de Resíduos
"""

import sys
import os
import signal
import logging

# Adicionar src ao path
SRC_DIR = os.path.join(os.path.dirname(__file__))
sys.path.insert(0, SRC_DIR)

def setup_logging():
    """Configura logging básico"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s | %(name)s | %(levelname)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    return logging.getLogger("Main")

def setup_signal_handlers(server):
    """Configura handlers para graceful shutdown"""
    def signal_handler(sig, frame):
        logger.info("Recebido sinal de interrupção, encerrando...")
        server.stop()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

def main():
    """Função principal"""
    logger = setup_logging()
    logger.info("🔧 Inicializando TrashNet Classification Server...")
    
    try:
        # Registrar serviços
        from src.core.service_factory import ServiceFactory
        from src.services.mqtt_client import MQTTClient
        from src.services.camera_manager import CameraManager
        from src.ai.trashnet_model import TrashNetModel
        from src.ai.classification_service import ClassificationService
        from src.services.main_server import TrashNetServer
        
        ServiceFactory.register_service("mqtt_client", MQTTClient)
        ServiceFactory.register_service("camera_manager", CameraManager)
        ServiceFactory.register_service("trashnet_model", TrashNetModel)
        ServiceFactory.register_service("classification_service", ClassificationService)
        ServiceFactory.register_service("main_server", TrashNetServer)
        
        # Criar e iniciar servidor
        server = ServiceFactory.create_service("main_server")
        setup_signal_handlers(server)
        
        # Iniciar servidor
        return server.start()
        
    except Exception as e:
        logger.error(f"❌ Erro fatal: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(0 if main() else 1)