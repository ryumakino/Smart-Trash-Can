import numpy as np
import traceback
from typing import Optional, Dict, Any
from config import MLConfig
from utils import log_info, log_error
from camera import capture_image, save_image_to_test
import cv2
from tensorflow.keras.models import Model
from tensorflow.keras.layers import Dense, Flatten, Input
from resnet50 import ResNet50

# --- Modelo ML ---
class TrashNetModel:
    def __init__(self, weights_path: str):
        self.input_shape = (224, 224, 3)
        self.classes = ["cardboard", "glass", "metal", "paper", "plastic", "trash"]
        self.cls_mapping = {
            "cardboard": "PAPELAO",
            "glass": "VIDRO",
            "metal": "METAL",
            "paper": "PAPEL",
            "plastic": "PLASTICO",
            "trash": "LIXO"
        }
        self.model = self._build_model()
        self.model.load_weights(weights_path)

    def _build_model(self) -> Model:
        inputs = Input(shape=self.input_shape)
        x = ResNet50(input_tensor=inputs)
        x = Flatten()(x)
        x = Dense(1024, activation='relu')(x)
        x = Dense(1024, activation='relu')(x)
        predictions = Dense(6, activation='softmax')(x)
        model = Model(inputs=inputs, outputs=predictions)
        return model

    def predict(self, image_array: np.ndarray) -> np.ndarray:
        if image_array.shape[:2] != (224, 224):
            image_resized = cv2.resize(image_array, (224, 224))
        else:
            image_resized = image_array
        image_batch = np.expand_dims(image_resized, axis=0)
        predictions = self.model.predict(image_batch, verbose=0)
        return predictions[0]

# --- Carregamento global do modelo ---
def load_model() -> Optional[TrashNetModel]:
    try:
        weights_path = MLConfig.MODEL_WEIGHTS_PATH
        model = TrashNetModel(weights_path)
        log_info("Modelo TrashNet carregado com sucesso")
        return model
    except Exception as e:
        log_error(f"Falha ao carregar modelo TrashNet: {e}")
        return None

MODEL = load_model()

# --- Classificação ---
def classify_waste() -> Optional[Dict[str, Any]]:
    try:
        log_info("=== INICIANDO CLASSIFICAÇÃO AUTOMÁTICA ===")
        
        # 1. Captura imagem
        processed_img = capture_image()
        if processed_img is None:
            log_error("Falha na captura da imagem")
            return None

        # 2. Salva imagem
        saved_filename = save_image_to_test(processed_img, "waste_capture")
        if saved_filename is None:
            log_error("Falha ao salvar imagem")
            return None

        # 3. Modelo
        model = MODEL
        if model is None:
            log_error("Modelo não carregado")
            return None

        # 4. Predição
        probabilities = model.predict(processed_img)
        predicted_class = int(np.argmax(probabilities))
        confidence = float(probabilities[predicted_class])

        original_class_name = model.classes[predicted_class]
        system_class_name = model.cls_mapping.get(original_class_name, original_class_name.upper())

        log_info(f"Classe detectada: {original_class_name} → Sistema: {system_class_name} (Confiança: {confidence:.2%})")

        if confidence < MLConfig.CONFIDENCE_THRESHOLD:
            log_error(f"Baixa confiança ({confidence:.2%})")
            return None

        try:
            system_index = MLConfig.WASTE_TYPES.index(system_class_name)
        except ValueError:
            log_error(f"Classe {system_class_name} não encontrada no sistema")
            return None

        return {
            "index": system_index,
            "name": system_class_name,
            "confidence": confidence
        }

    except Exception as e:
        log_error(f"ERRO na classificação ML: {e}")
        traceback.print_exc()
        return None
