import os
os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"

import tensorflow as tf
import numpy as np
from typing import Dict, Any, Optional
from src.core.base_classes import BaseService

class TrashNetModel(BaseService):
    """Modelo de classificação de resíduos"""
    
    def __init__(self):
        super().__init__("TrashNetModel")
        self.model = None
        self.input_size = (224, 224)
        self.class_mapping = {}
        
    def _initialize_impl(self) -> bool:
        from src.config.config_manager import CONFIG_MANAGER
        trashnet_config = CONFIG_MANAGER.get_trashnet_config()
        
        # Carregar configurações
        self.input_size = tuple(trashnet_config.get("MODEL_INPUT_SIZE", [224, 224]))
        self.class_mapping = trashnet_config.get("CLASS_MAPPING", {})
        
        # Construir modelo
        self.model = self._build_model()
        
        # Carregar pesos
        weights_path = trashnet_config.get("MODEL_WEIGHTS_PATH", "models/trashnet_model.h5")
        if os.path.exists(weights_path):
            self.model.load_weights(weights_path)
            self.logger.info(f"✅ Pesos carregados: {weights_path}")
            return True
        else:
            self.logger.error(f"❌ Pesos não encontrados: {weights_path}")
            return False
    
    def _cleanup_impl(self):
        self.model = None
    
    def _build_model(self):
        """Constrói a arquitetura CNN"""
        model = tf.keras.Sequential([
            tf.keras.layers.Conv2D(32, (3, 3), activation='relu', 
                                 input_shape=(*self.input_size, 3)),
            tf.keras.layers.BatchNormalization(),
            tf.keras.layers.MaxPooling2D(2, 2),
            tf.keras.layers.Dropout(0.25),
            
            tf.keras.layers.Conv2D(64, (3, 3), activation='relu'),
            tf.keras.layers.BatchNormalization(),
            tf.keras.layers.MaxPooling2D(2, 2),
            tf.keras.layers.Dropout(0.25),
            
            tf.keras.layers.Conv2D(128, (3, 3), activation='relu'),
            tf.keras.layers.BatchNormalization(),
            tf.keras.layers.MaxPooling2D(2, 2),
            tf.keras.layers.Dropout(0.25),
            
            tf.keras.layers.Flatten(),
            tf.keras.layers.Dense(512, activation='relu'),
            tf.keras.layers.BatchNormalization(),
            tf.keras.layers.Dropout(0.5),
            tf.keras.layers.Dense(6, activation='softmax')
        ])
        
        model.compile(
            optimizer=tf.keras.optimizers.Adam(learning_rate=0.001),
            loss='categorical_crossentropy',
            metrics=['accuracy']
        )
        
        return model
    
    def preprocess_image(self, image) -> Optional:
        """Pré-processa imagem para predição"""
        try:
            image_resized = tf.image.resize(image, self.input_size)
            image_normalized = image_resized / 255.0
            image_batch = tf.expand_dims(image_normalized, axis=0)
            return image_batch
        except Exception as e:
            self.logger.error(f"❌ Erro no pré-processamento: {e}")
            return None
    
    def predict(self, image) -> Optional[Dict[str, Any]]:
        """Faz predição na imagem"""
        try:
            processed_image = self.preprocess_image(image)
            if processed_image is None:
                return None
            
            predictions = self.model.predict(processed_image, verbose=0)
            confidence = np.max(predictions[0])
            class_index = np.argmax(predictions[0])
            
            # Mapear para classes do sistema
            original_classes = ["cardboard", "glass", "metal", "paper", "plastic", "trash"]
            original_class = original_classes[class_index]
            system_class = self.class_mapping.get(original_class, original_class.upper())
            
            return {
                'original_class': original_class,
                'system_class': system_class,
                'confidence': float(confidence),
                'class_index': int(class_index),
                'success': True
            }
            
        except Exception as e:
            self.logger.error(f"❌ Erro na predição: {e}")
            return {
                'success': False,
                'error': str(e)
            }