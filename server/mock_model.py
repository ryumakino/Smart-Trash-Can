# mock_model.py - Modelo simulado para quando não há pesos treinados
import numpy as np
from config import TrashNetConfig
from utils import get_logger

logger = get_logger("MockModel")

class MockTrashNetModel:
    def __init__(self):
        self.input_size = TrashNetConfig.MODEL_INPUT_SIZE
        self.original_classes = TrashNetConfig.ORIGINAL_CLASSES
        self.system_classes = TrashNetConfig.SYSTEM_CLASSES
        self.class_mapping = TrashNetConfig.CLASS_MAPPING
        logger.warning("⚠️ Usando modelo simulado (sem pesos treinados)")

    def predict(self, image):
        """Predição simulada para testes"""
        try:
            # Simular processamento
            np.random.seed(hash(str(image.shape)) % 1000)
            
            # Gerar predições aleatórias (mais realistas)
            fake_predictions = np.random.dirichlet(np.ones(6) * 10, size=1)[0]
            predicted_class_idx = np.argmax(fake_predictions)
            confidence = float(fake_predictions[predicted_class_idx])
            
            # Ajustar confiança para ser mais realista
            confidence = max(0.6, min(0.95, confidence))
            
            original_class = self.original_classes[predicted_class_idx]
            system_class = self.class_mapping.get(original_class, original_class.upper())
            
            try:
                system_idx = self.system_classes.index(system_class)
            except ValueError:
                system_idx = 0
            
            logger.info(f"🎭 Predição simulada: {system_class} ({confidence:.2%})")
            
            return {
                'original_class': original_class,
                'system_class': system_class,
                'system_index': system_idx,
                'confidence': confidence,
                'all_predictions': fake_predictions.tolist(),
                'is_mock': True  # Flag para identificar que é simulado
            }
            
        except Exception as e:
            logger.error(f"Erro no modelo simulado: {e}")
            return None

def create_fallback_model():
    """Criar modelo de fallback"""
    return MockTrashNetModel()