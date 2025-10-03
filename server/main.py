#!/usr/bin/env python3
"""
TrashNet Server - Sistema de Classificação de Resíduos com ESP32
Ponto de entrada principal
"""

import sys
import signal
import os
import logging

# Adicionar o diretório src ao path para imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Configurar logger básico inicial para o main
def setup_basic_logger():
    logger = logging.getLogger("Main")
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s | %(name)s | %(levelname)s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger

logger = setup_basic_logger()

def signal_handler(signum, frame):
    """Manipular sinais de interrupção"""
    logger.info("Recebido sinal de interrupção, encerrando...")
    sys.exit(0)

def main():
    # Registrar handlers de sinal
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Inicializar sistema
        from src.core.app_config import initialize_system, get_trash_net_server
        
        if not initialize_system():
            logger.error("Falha na inicialização do sistema")
            return 1
        
        # Obter e iniciar servidor
        server = get_trash_net_server()
        if server.start():
            # Manter o processo rodando
            try:
                while server.running:
                    signal.pause()  # Esperar por sinais
            except KeyboardInterrupt:
                logger.info("Interrompido pelo usuário")
            finally:
                server.stop()
                
            return 0
        else:
            logger.error("Falha ao iniciar servidor")
            return 1
            
    except Exception as e:
        logger.error(f"Erro fatal: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())