import numpy as np
from typing import Optional, Any
import traceback
from config import (
    MODEL_PATH,
    LOG_MODEL_OK,
    LOG_MODEL_FAIL,
    LOG_MODEL_NOT_LOADED,
    LOG_MODEL_PREPROCESS_FAIL,
    LOG_PREFIX_MODEL,
    LOG_MODEL_CLASSIFICATION,
    WASTE_TYPES,
    CONFIDENCE_THRESHOLD,
    LOG_MODEL_LOW_CONFIDENCE,
    LOG_MODEL_CLASSIFICATION_ERROR
)
from camera import preprocess_image
from utils import log_message, log_error, log_success

def setup_ml_model() -> Optional[Any]:
    """Carrega o modelo ML treinado."""
    try:
        model = load_model()
        if model:
            log_success(LOG_MODEL_OK)
            return model
    except Exception as e:
        log_error(f"ML setup error: {e}")
        traceback.print_exc()
    log_message(LOG_PREFIX_MODEL, LOG_MODEL_FAIL)
    return None

def load_model() -> Optional[Any]:
    """Retorna o modelo ML (mock ou real)."""
    # Substituir por código real de carregamento de modelo
    # Ex.: tf.keras.models.load_model(MODEL_PATH)
    return "trained_model_mock"

def classify_waste(model: Optional[Any], image: np.ndarray) -> Optional[int]:
    """Classifica a imagem capturada e retorna tipo de lixo."""
    if model is None:
        log_error(LOG_MODEL_NOT_LOADED)
        return None

    try:
        processed_img = preprocess_image(image)
        if processed_img is None:
            log_error(LOG_MODEL_PREPROCESS_FAIL)
            return None

        # Mock prediction (substituir por inferência real)
        predicted_class = np.random.randint(0, len(WASTE_TYPES))
        confidence = np.random.uniform(0.5, 1.0)

        log_message(LOG_PREFIX_MODEL,
                    f"{LOG_MODEL_CLASSIFICATION}: {WASTE_TYPES[predicted_class]} (Confidence: {confidence:.2%})")

        if confidence >= CONFIDENCE_THRESHOLD:
            return predicted_class
        else:
            log_error(LOG_MODEL_LOW_CONFIDENCE)
            return None

    except Exception as e:
        log_error(f"{LOG_MODEL_CLASSIFICATION_ERROR}: {e}")
        traceback.print_exc()
        return None

def get_model_summary(model: Optional[Any]) -> str:
    """Retorna resumo do modelo (mock)."""
    if model is None:
        return LOG_MODEL_NOT_LOADED
    return "Model summary not implemented (mock)"
