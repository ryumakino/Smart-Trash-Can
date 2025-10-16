# ai/classification_service.py - ATUALIZADO PARA LOGS MELHORES
import time
from datetime import datetime
from typing import Dict, Any
from src.core.base_classes import BaseService

class ClassificationService(BaseService):
    """Serviço de classificação - orquestra câmera e modelo"""
    
    def __init__(self):
        super().__init__("ClassificationService")
        self.model = None
        self.camera = None
        self.classification_count = 0
        
    def _initialize_impl(self) -> bool:
        from src.core.service_factory import ServiceFactory
        
        self.model = ServiceFactory.get_service("trashnet_model")
        self.camera = ServiceFactory.get_service("camera_manager")
        
        if not self.model or not self.camera:
            self.logger.error("❌ Dependências não disponíveis")
            return False
        
        if not self.model.initialize():
            self.logger.error("❌ Falha ao inicializar modelo")
            return False
        
        if not self.camera.initialize():
            self.logger.error("❌ Falha ao inicializar câmera")
            return False
        
        self.logger.info("✅ Serviço de classificação inicializado")
        return True
    
    def _cleanup_impl(self):
        if self.model:
            self.model.cleanup()
        if self.camera:
            self.camera.cleanup()
    
    def classify_waste(self) -> Dict[str, Any]:
        """Executa classificação completa: captura + predição"""
        start_time = time.time()
        self.classification_count += 1
        
        try:
            self.logger.info("🔍 Iniciando classificação...")
            
            # Capturar imagem
            frame = self.camera.capture_frame()
            if frame is None:
                self.logger.error("❌ Falha ao capturar imagem da câmera")
                return self._create_error_response("Falha ao capturar imagem")
            
            self.logger.debug("✅ Imagem capturada com sucesso")
            
            # Fazer predição
            result = self.model.predict(frame)
            if not result.get('success', False):
                error_msg = result.get('error', 'Falha na predição')
                self.logger.error(f"❌ Falha na predição: {error_msg}")
                return self._create_error_response(error_msg)
            
            # Enriquecer resultado
            processing_time = time.time() - start_time
            result.update({
                'timestamp': datetime.now().isoformat(),
                'processing_time': processing_time,
                'classification_id': self.classification_count
            })
            
            # Verificar confiança
            from src.config.config_manager import CONFIG_MANAGER
            threshold = CONFIG_MANAGER.get_trashnet_config().get("CONFIDENCE_THRESHOLD", 0.6)
            
            if result['confidence'] < threshold:
                self.logger.warning(
                    f"⚠️ Confiança baixa: {result['system_class']} "
                    f"(Confiança: {result['confidence']:.2%}, "
                    f"Threshold: {threshold:.2%})"
                )
                result['low_confidence'] = True
            else:
                self.logger.success(
                    f"✅ Classificação #{self.classification_count}: "
                    f"{result['system_class']} "
                    f"(Confiança: {result['confidence']:.2%}, "
                    f"Tempo: {processing_time:.2f}s)"
                )
            
            # Salvar imagem para debug (opcional)
            if self.classification_count % 10 == 0:  # A cada 10 classificações
                try:
                    filename = f"classification_{self.classification_count}.jpg"
                    self.camera.save_frame(frame, filename)
                    result['image_saved'] = filename
                except Exception as e:
                    self.logger.debug(f"⚠️ Não foi possível salvar imagem: {e}")
            
            # Notificar observadores
            self.notify_observers("classification_completed", result)
            
            return result
            
        except Exception as e:
            error_msg = f"Erro no serviço de classificação: {e}"
            self.logger.error(f"❌ {error_msg}")
            return self._create_error_response(error_msg)
    
    def _create_error_response(self, error_msg: str) -> Dict[str, Any]:
        """Cria resposta de erro padronizada"""
        return {
            'success': False,
            'error': error_msg,
            'timestamp': datetime.now().isoformat(),
            'system_class': 'INDETERMINADO',
            'confidence': 0.0,
            'class_index': -1
        }
    
    def get_status(self) -> Dict[str, Any]:
        status = super().get_status()
        status.update({
            'model_available': self.model.is_initialized if self.model else False,
            'camera_available': self.camera.is_initialized if self.camera else False,
            'classification_count': self.classification_count,
            'last_classification': datetime.now().isoformat()
        })
        return status