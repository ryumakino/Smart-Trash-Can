# services/main_server.py - SERVIDOR ATUALIZADO
import time
from datetime import datetime
from typing import Dict, Any
from src.core.base_classes import BaseService

class TrashNetServer(BaseService):
    """Servidor principal - Processa requisições dos ESP32"""
    
    def __init__(self):
        super().__init__("TrashNetServer")
        self.running = False
        self.mqtt_client = None
        self.classification_service = None
        self.active_requests = {}  # Track active classification requests
        
    def _initialize_impl(self) -> bool:
        from src.core.service_factory import ServiceFactory
        
        # Obter serviços
        self.mqtt_client = ServiceFactory.get_service("mqtt_client")
        self.classification_service = ServiceFactory.get_service("classification_service")
        
        if not self.mqtt_client or not self.classification_service:
            self.logger.error("❌ Serviços essenciais não disponíveis")
            return False
        
        # Inicializar serviços
        if not self.mqtt_client.initialize():
            self.logger.error("❌ Falha ao inicializar MQTT")
            return False
        
        if not self.classification_service.initialize():
            self.logger.error("❌ Falha ao inicializar serviço de classificação")
            return False
        
        # Configurar handlers MQTT para ESP32
        self._setup_esp32_handlers()
        
        self.logger.info("✅ TrashNetServer inicializado - Pronto para requisições dos ESP32")
        return True
    
    def _cleanup_impl(self):
        self.running = False
        if self.mqtt_client:
            self.mqtt_client.cleanup()
        if self.classification_service:
            self.classification_service.cleanup()
    
    def _setup_esp32_handlers(self):
        """Configura handlers para mensagens dos ESP32"""
        from src.config.config_manager import CONFIG_MANAGER
        mqtt_config = CONFIG_MANAGER.get_mqtt_config()
        topic_prefix = mqtt_config.get("TOPIC_PREFIX", "trashnet")
        
        # Handler para requisições de classificação
        classification_topic = f"{topic_prefix}/classification/request"
        self.mqtt_client.register_message_handler(
            classification_topic, 
            self._handle_classification_request
        )
        
        # Handler para requisições de classificação de dispositivos específicos
        device_classification_topic = f"{topic_prefix}/devices/+/classification/request"
        self.mqtt_client.register_message_handler(
            device_classification_topic,
            self._handle_classification_request
        )
        
        # Handler para status dos dispositivos
        status_topic = f"{topic_prefix}/+/status"
        self.mqtt_client.register_message_handler(
            status_topic,
            self._handle_device_status
        )
        
        # Handler para eventos dos dispositivos
        events_topic = f"{topic_prefix}/+/events"
        self.mqtt_client.register_message_handler(
            events_topic,
            self._handle_device_event
        )
    
    def _handle_classification_request(self, topic: str, payload: Dict[str, Any]):
        """Processa requisições de classificação dos ESP32"""
        try:
            # Extrair device_id do tópico ou payload
            device_id = self._extract_device_id(topic, payload)
            request_id = payload.get('request_id', str(time.time()))
            
            self.logger.info(f"🎯 Requisição de classificação de: {device_id}")
            
            # Registrar requisição ativa
            self.active_requests[request_id] = {
                'device_id': device_id,
                'topic': topic,
                'timestamp': time.time(),
                'payload': payload
            }
            
            # Executar classificação
            result = self.classification_service.classify_waste()
            
            # Adicionar informações da requisição ao resultado
            if result:
                result.update({
                    'device_id': device_id,
                    'request_id': request_id,
                    'server_timestamp': datetime.now().isoformat()
                })
                
                # Publicar resultado
                self._publish_classification_result(device_id, result)
                
                # Limpar requisição
                if request_id in self.active_requests:
                    del self.active_requests[request_id]
            else:
                # Publicar erro
                self._publish_classification_error(device_id, request_id, "Falha na classificação")
                
        except Exception as e:
            self.logger.error(f"❌ Erro ao processar requisição: {e}")
            # Tentar publicar erro mesmo em caso de exceção
            try:
                device_id = self._extract_device_id(topic, payload)
                request_id = payload.get('request_id', 'unknown')
                self._publish_classification_error(device_id, request_id, str(e))
            except:
                pass
    
    def _handle_device_status(self, topic: str, payload: Dict[str, Any]):
        """Processa mensagens de status dos dispositivos"""
        try:
            device_id = topic.split('/')[1]  # Extrair device_id do tópico
            self.logger.debug(f"📊 Status de {device_id}: {payload.get('status', 'unknown')}")
            
            # Aqui você pode armazenar o status do dispositivo se necessário
            # ou tomar ações baseadas no status
            
        except Exception as e:
            self.logger.error(f"❌ Erro processando status: {e}")
    
    def _handle_device_event(self, topic: str, payload: Dict[str, Any]):
        """Processa eventos dos dispositivos"""
        try:
            device_id = topic.split('/')[1]  # Extrair device_id do tópico
            event_type = payload.get('type', 'unknown')
            
            self.logger.info(f"📢 Evento de {device_id}: {event_type}")
            
            # Log de eventos importantes
            if event_type in ['movement_detected', 'classification_completed', 'classification_failed']:
                self.logger.info(f"🔔 Evento importante: {device_id} - {event_type}")
                
        except Exception as e:
            self.logger.error(f"❌ Erro processando evento: {e}")
    
    def _extract_device_id(self, topic: str, payload: Dict[str, Any]) -> str:
        """Extrai device_id do tópico ou payload"""
        # Tentar do payload primeiro
        device_id = payload.get('device_id')
        if device_id:
            return device_id
        
        # Tentar extrair do tópico
        if '/devices/' in topic:
            parts = topic.split('/')
            device_index = parts.index('devices') + 1
            if device_index < len(parts):
                return parts[device_index]
        
        # Fallback
        return "unknown_device"
    
    def _publish_classification_result(self, device_id: str, result: Dict[str, Any]):
        """Publica resultado da classificação para o ESP32"""
        try:
            # Preparar mensagem de resultado
            result_message = {
                'success': result.get('success', False),
                'waste_type': result.get('system_class', 'INDETERMINADO'),
                'confidence': result.get('confidence', 0),
                'class_index': result.get('class_index', -1),
                'timestamp': result.get('timestamp'),
                'processing_time': result.get('processing_time', 0),
                'request_id': result.get('request_id'),
                'server_timestamp': result.get('server_timestamp')
            }
            
            # Publicar para dispositivo específico
            if device_id != "unknown_device":
                success = self.mqtt_client.publish_to_device(
                    device_id, 
                    'classification/result', 
                    result_message
                )
                
                if success:
                    self.logger.success(
                        f"✅ Resultado enviado para {device_id}: "
                        f"{result_message['waste_type']} "
                        f"(Confiança: {result_message['confidence']:.2%})"
                    )
                else:
                    self.logger.error(f"❌ Falha ao enviar resultado para {device_id}")
            
            # Publicar também em tópico genérico (opcional)
            from src.config.config_manager import CONFIG_MANAGER
            mqtt_config = CONFIG_MANAGER.get_mqtt_config()
            topic_prefix = mqtt_config.get("TOPIC_PREFIX", "trashnet")
            
            generic_topic = f"{topic_prefix}/classification/result"
            self.mqtt_client.publish_generic(generic_topic, result_message)
            
        except Exception as e:
            self.logger.error(f"❌ Erro publicando resultado: {e}")
    
    def _publish_classification_error(self, device_id: str, request_id: str, error_msg: str):
        """Publica erro de classificação"""
        try:
            error_message = {
                'success': False,
                'error': error_msg,
                'request_id': request_id,
                'timestamp': datetime.now().isoformat(),
                'waste_type': 'INDETERMINADO',
                'confidence': 0,
                'class_index': -1
            }
            
            if device_id != "unknown_device":
                self.mqtt_client.publish_to_device(
                    device_id, 
                    'classification/result', 
                    error_message
                )
            
            self.logger.error(f"❌ Erro publicado para {device_id}: {error_msg}")
            
        except Exception as e:
            self.logger.error(f"❌ Erro publicando erro: {e}")
    
    def _cleanup_old_requests(self):
        """Limpa requisições antigas para evitar memory leak"""
        current_time = time.time()
        old_requests = []
        
        for request_id, request_data in self.active_requests.items():
            if current_time - request_data['timestamp'] > 300:  # 5 minutos
                old_requests.append(request_id)
        
        for request_id in old_requests:
            del self.active_requests[request_id]
            self.logger.debug(f"🧹 Requisição antiga removida: {request_id}")
    
    def start(self) -> bool:
        """Inicia o servidor"""
        if not self.initialize():
            return False
        
        self.running = True
        self.logger.info("🚀 TrashNet Server iniciado - Aguardando requisições dos ESP32")
        
        # Loop principal
        try:
            last_cleanup = time.time()
            
            while self.running:
                # Limpar requisições antigas a cada minuto
                if time.time() - last_cleanup > 60:
                    self._cleanup_old_requests()
                    last_cleanup = time.time()
                
                time.sleep(1)
                
        except KeyboardInterrupt:
            self.logger.info("⏹️  Interrompido pelo usuário")
        finally:
            self.stop()
        
        return True
    
    def stop(self):
        """Para o servidor"""
        self.logger.info("🛑 Parando TrashNet Server...")
        self.running = False
        self.cleanup()