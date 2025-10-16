# classification_service_refactored.py – DRY + SOLID
import time
from datetime import datetime
from src.core.base_classes import BaseService, ConfigurableMixin

class ClassificationService(BaseService, ConfigurableMixin):
    def __init__(self):
        super().__init__('trashnet')
        self._model = None
        self._camera = None
        self._is_mock = False

    # ---------- lifecycle ---------- #
    def initialize(self) -> bool:
        if self._initialized: return True
        self.logger.info("Inicializando serviço de classificação...")
        self._model = self._load_model()
        self._camera = self._load_camera()
        if not self._model or not self._camera or not self._camera.initialize():
            return False
        self._initialized = True
        self.logger.success("Serviço de classificação inicializado")
        return True

    # ---------- public api ---------- #
    def classify_waste(self):
        try:
            self.logger.info("=== INICIANDO CLASSIFICAÇÃO ===")
            start = time.time()

            image = self._camera.capture_image()
            if image is None: return None

            saved_path = self._camera.save_image(image, "classification")
            result = self._model.predict(image)
            if result is None: return None

            self._enrich_result(result, saved_path, start)
            return result
        except Exception as e:
            self.logger.error(f"Erro no serviço de classificação: {e}")
            return None

    def get_status(self):
        base = super().get_status()
        base.update({
            'model_loaded': self._model is not None,
            'model_type': 'mock' if self._is_mock else 'real',
            'camera_initialized': self._camera.is_initialized if self._camera else False,
            'status': 'operational' if self._model and self._camera and self._camera.is_initialized else 'degraded'
        })
        return base

    # ---------- helpers ---------- #
    def _load_model(self):
        from src.core.app_config import get_trashnet_model
        model = get_trashnet_model()
        if not model:
            self.logger.error("Nenhum modelo disponível")
        return model

    def _load_camera(self):
        from src.core.app_config import get_camera_manager
        return get_camera_manager()

    def _enrich_result(self, result, saved_path, start):
        threshold = self.get_config_value('CONFIDENCE_THRESHOLD', 0.6)
        if not self._is_mock and result['confidence'] < threshold:
            self.logger.warning(f"Confiança baixa: {result['confidence']:.2%}")
            return None
        result['timestamp'] = datetime.now().isoformat()
        result['image_path'] = saved_path
        result['processing_time'] = time.time() - start
        result['model_type'] = 'mock' if self._is_mock else 'real'
        icon = "🎭" if self._is_mock else "✅"
        self.logger.success(f"{icon} Classificação concluída: {result['system_class']} (Confiança: {result['confidence']:.2%}, Tempo: {result['processing_time']:.2f}s)")