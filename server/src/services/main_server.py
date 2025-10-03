#!/usr/bin/env python3
"""
Servidor principal do sistema TrashNet
"""

import time
import threading
import queue
import json
from src.core.base_classes import BaseService, ConfigurableMixin

class TrashNetServer(BaseService, ConfigurableMixin):
    def __init__(self):
        super().__init__('server')
        self.running = True
        self.classification_queue = queue.Queue()
        self.classification_thread = threading.Thread(
            target=self._classification_processor, 
            daemon=True
        )

    def initialize(self):
        """Inicializar servidor principal"""
        if self._initialized:
            return True
            
        try:
            self._initialized = True
            self.logger.success("TrashNetServer inicializado")
            return True
        except Exception as e:
            self.logger.error(f"Erro na inicialização: {e}")
            return False

    def start(self):
        """Iniciar servidor principal"""
        if not self.initialize():
            return False
            
        self.logger.info("Iniciando Servidor TrashNet...")
        
        try:
            # Configurar callback de movimento
            from src.core.app_config import get_server_communicator
            communicator = get_server_communicator()
            communicator.set_movement_callback(self._handle_movement_detected)
            
            # Iniciar componentes
            communicator.start()
                
            self.classification_thread.start()
            
            self._main_loop()
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Erro ao iniciar servidor: {e}")
            return False

    def _main_loop(self):
        """Loop principal do servidor"""
        while self.running:
            time.sleep(1)

    def _classification_processor(self):
        """Processar classificações na fila"""
        while self.running:
            try:
                if not self.classification_queue.empty():
                    device_id, device_ip = self.classification_queue.get_nowait()
                    self._process_classification(device_id, device_ip)
                time.sleep(0.1)
            except Exception as e:
                self.logger.error(f"Erro no processador: {e}")
                time.sleep(1)

    def _handle_movement_detected(self, device_id, device_ip):
        """Manipular detecção de movimento"""
        self.logger.info(f"🎯 Movimento detectado: {device_id}")
        self.classification_queue.put((device_id, device_ip))

    def _process_classification(self, device_id, device_ip):
        """Processar classificação para dispositivo"""
        try:
            from src.core.app_config import (
                get_device_registry, 
                get_classification_service,
                get_server_communicator,
                get_database
            )
            
            device_registry = get_device_registry()
            device_info = device_registry.get_device(device_id)
            
            if not device_info:
                self.logger.error(f"Dispositivo {device_id} não encontrado")
                return

            device_name = device_info.get('device_name', device_id)
            self.logger.info(f"🔍 Iniciando classificação para {device_name}")
            
            # Executar classificação
            classification_service = get_classification_service()
            result = classification_service.classify_waste()
            
            if result:
                self._handle_classification_result(device_id, device_name, result)
            else:
                self._handle_classification_failure(device_id)
                
        except Exception as e:
            self.logger.error(f"❌ Erro ao processar classificação para {device_id}: {e}")
            from src.core.app_config import get_server_communicator
            get_server_communicator().send_to_device(device_id, "WASTE_TYPE:-1:ERRO")

    def _handle_classification_result(self, device_id, device_name, result):
        """Manipular resultado bem-sucedido da classificação"""
        from src.core.app_config import get_database, get_server_communicator
        
        # Salvar no banco
        database = get_database()
        result['device_id'] = device_id
        database.save_classification(result)
        
        # Encontrar system_index se não estiver presente
        if 'system_index' not in result:
            from src.core.app_config import TRASHNET_CONFIG
            system_classes = TRASHNET_CONFIG.get("SYSTEM_CLASSES", ["PLASTICO", "PAPEL", "VIDRO", "METAL", "LIXO", "PAPELAO"])
            try:
                system_index = system_classes.index(result['system_class'])
            except ValueError:
                system_index = -1
            result['system_index'] = system_index
        
        # Enviar comando para dispositivo
        communicator = get_server_communicator()
        command = f"WASTE_TYPE:{result['system_index']}:{result['system_class']}"
        
        if communicator.send_to_device(device_id, command):
            icon = "🎭" if result.get('is_mock') else "✅"
            self.logger.success(
                f"{icon} Resíduo classificado para {device_name}: "
                f"{result['system_class']} (Confiança: {result['confidence']:.2%})"
            )
            
            # Enviar status atualizado
            status_update = f"CLASSIFICATION_RESULT:{json.dumps(result)}"
            communicator.send_to_device(device_id, status_update)
        else:
            self.logger.error(f"❌ Falha ao enviar comando para {device_name}")

    def _handle_classification_failure(self, device_id):
        """Manipular falha na classificação"""
        from src.core.app_config import get_server_communicator
        communicator = get_server_communicator()
        communicator.send_to_device(device_id, "WASTE_TYPE:-1:INDETERMINADO")
        self.logger.warning(f"❌ Classificação falhou para {device_id}")

    def stop(self):
        """Parar servidor"""
        self.running = False
        from src.core.app_config import get_server_communicator
        communicator = get_server_communicator()
        if communicator:
            communicator.stop()
        self.logger.info("🛑 Servidor TrashNet parado")

    def get_system_status(self):
        """Obter status completo do sistema"""
        from src.core.app_config import (
            get_server_communicator,
            get_classification_service, 
            get_database
        )
        
        communicator = get_server_communicator()
        classification_service = get_classification_service()
        database = get_database()
        
        return {
            'server': self.get_status(),
            'communication': communicator.get_communication_stats() if communicator else {},
            'classification_service': classification_service.get_status() if classification_service else {},
            'database': database.get_statistics() if database else {}
        }

    def send_system_command(self, device_id, command):
        """Enviar comando de sistema para dispositivo"""
        try:
            from src.core.app_config import get_server_communicator
            communicator = get_server_communicator()
            
            if command == "RESTART":
                return communicator.send_to_device(device_id, "SYSTEM_COMMAND:RESTART")
            elif command == "STATUS":
                return communicator.send_to_device(device_id, "SYSTEM_COMMAND:STATUS")
            elif command == "DISCOVER":
                return communicator.send_to_device(device_id, "SYSTEM_COMMAND:DISCOVER")
            elif command == "GET_INFO":
                return communicator.send_to_device(device_id, "SYSTEM_COMMAND:GET_INFO")
            else:
                self.logger.warning(f"Comando não reconhecido: {command}")
                return False
                
        except Exception as e:
            self.logger.error(f"Erro ao enviar comando para {device_id}: {e}")
            return False