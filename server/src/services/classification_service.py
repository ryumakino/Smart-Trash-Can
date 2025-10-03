# classification_service.py - Serviço com fallback (Refatorado)
import time
from datetime import datetime
from src.core.base_classes import BaseService, ConfigurableMixin

class ClassificationService(BaseService, ConfigurableMixin):
    def __init__(self):
        super().__init__('trashnet')
        self.model = None
        self.camera = None
        self.is_mock = False
    
    def initialize(self):
        """Inicializar serviço com fallback"""
        if self._initialized:
            return True
            
        self.logger.info("Inicializando serviço de classificação...")
        
        # Tentar carregar modelo real
        from src.core.app_config import get_trashnet_model
        self.model = get_trashnet_model()
        
        if not self.model:
            self.logger.error("Nenhum modelo disponível")
            return False
        
        # Inicializar câmera
        from src.core.app_config import get_camera_manager
        self.camera = get_camera_manager()
        
        if not self.camera.initialize():
            self.logger.error("Falha ao inicializar câmera")
            return False
        
        self._initialized = True
        self.logger.success("Serviço de classificação inicializado")
        return True
    
    def classify_waste(self):
        """Classificar resíduo com tratamento robusto"""
        try:
            self.logger.info("=== INICIANDO CLASSIFICAÇÃO ===")
            start_time = time.time()
            
            # 1. Capturar imagem
            self.logger.info("Capturando imagem...")
            image = self.camera.capture_image()
            if image is None:
                self.logger.error("Falha na captura da imagem")
                return None
            
            # 2. Salvar imagem para debug
            saved_path = self.camera.save_image(image, "classification")
            
            # 3. Fazer predição
            self.logger.info("Executando classificação...")
            result = self.model.predict(image)
            if result is None:
                self.logger.error("Falha na classificação")
                return None
            
            # 4. Adicionar flag de mock
            if self.is_mock:
                result['is_mock'] = True
            
            # 5. Validar confiança (apenas para modelo real)
            confidence_threshold = self.get_config_value('CONFIDENCE_THRESHOLD', 0.6)
            if not self.is_mock and result['confidence'] < confidence_threshold:
                self.logger.warning(f"Confiança baixa: {result['confidence']:.2%}")
                return None
            
            # 6. Log do resultado
            elapsed_time = time.time() - start_time
            status_icon = "🎭" if self.is_mock else "✅"
            
            self.logger.success(
                f"{status_icon} Classificação concluída: {result['system_class']} "
                f"(Confiança: {result['confidence']:.2%}, "
                f"Tempo: {elapsed_time:.2f}s)"
            )
            
            # Adicionar metadados
            result['timestamp'] = datetime.now().isoformat()
            result['image_path'] = saved_path
            result['processing_time'] = elapsed_time
            result['model_type'] = 'mock' if self.is_mock else 'real'
            
            return result
            
        except Exception as e:
            self.logger.error(f"Erro no serviço de classificação: {e}")
            return None
    
    def get_status(self):
        """Obter status detalhado do serviço"""
        base_status = super().get_status()
        base_status.update({
            'model_loaded': self.model is not None,
            'model_type': 'mock' if self.is_mock else 'real',
            'camera_initialized': self.camera.is_initialized if self.camera else False,
            'status': 'operational' if self.model and self.camera and self.camera.is_initialized else 'degraded'
        })
        return base_status