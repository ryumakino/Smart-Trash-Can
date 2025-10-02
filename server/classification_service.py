# classification_service.py - Serviço com fallback
import time
from datetime import datetime
from trashnet_model import load_trashnet_model
from mock_model import create_fallback_model
from camera_manager import CAMERA_MANAGER
from config import TrashNetConfig
from utils import get_logger

logger = get_logger("ClassificationService")

class ClassificationService:
    def __init__(self):
        self.model = None
        self.camera = CAMERA_MANAGER
        self.is_mock = False
        self.initialize()
    
    def initialize(self):
        """Inicializar serviço com fallback"""
        logger.info("Inicializando serviço de classificação...")
        
        # Tentar carregar modelo real
        self.model = load_trashnet_model()
        
        # Fallback para modelo simulado se necessário
        if not self.model and TrashNetConfig.USE_FALLBACK:
            self.model = create_fallback_model()
            self.is_mock = True
            logger.warning("✅ Usando modelo simulado (modo de teste)")
        
        if not self.model:
            logger.error("❌ Nenhum modelo disponível")
            return False
        
        # Inicializar câmera
        if not self.camera.initialize():
            logger.error("❌ Falha ao inicializar câmera")
            return False
        
        logger.success("✅ Serviço de classificação inicializado")
        return True
    
    def classify_waste(self):
        """Classificar resíduo com tratamento robusto"""
        try:
            logger.info("=== INICIANDO CLASSIFICAÇÃO ===")
            start_time = time.time()
            
            # 1. Capturar imagem
            logger.info("📸 Capturando imagem...")
            image = self.camera.capture_image()
            if image is None:
                logger.error("❌ Falha na captura da imagem")
                return None
            
            # 2. Salvar imagem para debug
            saved_path = self.camera.save_image(image, "classification")
            
            # 3. Fazer predição
            logger.info("🤖 Executando classificação...")
            result = self.model.predict(image)
            if result is None:
                logger.error("❌ Falha na classificação")
                return None
            
            # 4. Adicionar flag de mock
            if self.is_mock:
                result['is_mock'] = True
            
            # 5. Validar confiança (apenas para modelo real)
            if not self.is_mock and result['confidence'] < TrashNetConfig.CONFIDENCE_THRESHOLD:
                logger.warning(f"⚠️ Confiança baixa: {result['confidence']:.2%}")
                return None
            
            # 6. Log do resultado
            elapsed_time = time.time() - start_time
            status_icon = "🎭" if self.is_mock else "✅"
            
            logger.success(
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
            logger.error(f"❌ Erro no serviço de classificação: {e}")
            return None
    
    def get_status(self):
        """Obter status detalhado do serviço"""
        return {
            'model_loaded': self.model is not None,
            'model_type': 'mock' if self.is_mock else 'real',
            'camera_initialized': self.camera.is_initialized,
            'timestamp': datetime.now().isoformat(),
            'status': 'operational' if self.model and self.camera.is_initialized else 'degraded'
        }

# Instância global do serviço
CLASSIFICATION_SERVICE = ClassificationService()