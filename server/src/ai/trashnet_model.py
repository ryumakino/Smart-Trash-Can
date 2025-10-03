# trashnet_model.py - Adaptado para TensorFlow 2.20+ (Refatorado)
import os
os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"
import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Conv2D, MaxPooling2D, Flatten, Dense, Dropout, BatchNormalization
from tensorflow.keras.optimizers import Adam
import numpy as np
from src.core.base_classes import BaseService, ConfigurableMixin

class TrashNetModel(BaseService, ConfigurableMixin):
    def __init__(self, weights_path=None):
        super().__init__('trashnet')
        self.input_size = tuple(self.get_config_value('MODEL_INPUT_SIZE', [224, 224]))
        self.original_classes = self.get_config_value('ORIGINAL_CLASSES', ["cardboard", "glass", "metal", "paper", "plastic", "trash"])
        self.system_classes = self.get_config_value('SYSTEM_CLASSES', ["PLASTICO", "PAPEL", "VIDRO", "METAL", "LIXO", "PAPELAO"])
        self.class_mapping = self.get_config_value('CLASS_MAPPING', {})
        
        # Construir modelo
        self.model = self._build_model()
        
        if weights_path:
            self.load_weights(weights_path)
    
    def initialize(self):
        """Inicializar modelo TrashNet"""
        if self._initialized:
            return True
            
        try:
            weights_path = self.get_config_value('MODEL_WEIGHTS_PATH', 'models/trashnet_model.h5')
            if os.path.exists(weights_path):
                self.load_weights(weights_path)
                self._initialized = True
                self.logger.success("✅ Modelo TrashNet inicializado com sucesso")
            else:
                self.logger.warning("⚠️ Modelo TrashNet criado sem pesos (modo de teste)")
                self._initialized = True
                
            return True
        except Exception as e:
            self.logger.error(f"❌ Erro na inicialização do modelo: {e}")
            return False
    
    def _build_model(self):
        """Construir arquitetura CNN similar ao TrashNet"""
        model = Sequential([
            # Camada 1
            Conv2D(32, (3, 3), activation='relu', input_shape=(*self.input_size, 3)),
            BatchNormalization(),
            MaxPooling2D(2, 2),
            Dropout(0.25),
            
            # Camada 2
            Conv2D(64, (3, 3), activation='relu'),
            BatchNormalization(),
            MaxPooling2D(2, 2),
            Dropout(0.25),
            
            # Camada 3
            Conv2D(128, (3, 3), activation='relu'),
            BatchNormalization(),
            MaxPooling2D(2, 2),
            Dropout(0.25),
            
            # Camada 4
            Conv2D(256, (3, 3), activation='relu'),
            BatchNormalization(),
            MaxPooling2D(2, 2),
            Dropout(0.25),
            
            # Classificação
            Flatten(),
            Dense(512, activation='relu'),
            BatchNormalization(),
            Dropout(0.5),
            Dense(len(self.original_classes), activation='softmax')
        ])
        
        model.compile(
            optimizer=Adam(learning_rate=0.001),
            loss='categorical_crossentropy',
            metrics=['accuracy']
        )
        
        return model
    
    def load_weights(self, weights_path):
        """Carregar pesos do modelo"""
        try:
            if os.path.exists(weights_path):
                self.model.load_weights(weights_path)
                self.logger.success(f"✅ Pesos carregados: {weights_path}")
                return True
            else:
                self.logger.warning(f"⚠️ Arquivo de pesos não encontrado: {weights_path}")
                return False
        except Exception as e:
            self.logger.error(f"❌ Erro ao carregar pesos: {e}")
            return False
    
    def preprocess_image(self, image):
        """Pré-processar imagem para predição"""
        try:
            # Redimensionar
            image_resized = tf.image.resize(image, self.input_size)
            # Normalizar
            image_normalized = image_resized / 255.0
            # Adicionar dimensão do batch
            image_batch = tf.expand_dims(image_normalized, axis=0)
            return image_batch
        except Exception as e:
            self.logger.error(f"❌ Erro no pré-processamento: {e}")
            return None
    
    def predict(self, image):
        """Fazer predição na imagem"""
        try:
            # Pré-processar
            processed_image = self.preprocess_image(image)
            if processed_image is None:
                return None
            
            # Fazer predição
            predictions = self.model.predict(processed_image, verbose=0)
            confidence = np.max(predictions[0])
            class_index = np.argmax(predictions[0])
            original_class = self.original_classes[class_index]
            
            # Mapear para classe do sistema
            system_class = self.class_mapping.get(original_class, original_class.upper())
            
            return {
                'original_class': original_class,
                'system_class': system_class,
                'confidence': float(confidence),
                'all_predictions': {
                    self.original_classes[i]: float(pred) 
                    for i, pred in enumerate(predictions[0])
                }
            }
            
        except Exception as e:
            self.logger.error(f"❌ Erro na predição: {e}")
            return None
    
    def get_model_info(self):
        """Obter informações do modelo"""
        base_status = super().get_status()
        base_status.update({
            'input_size': self.input_size,
            'original_classes': self.original_classes,
            'system_classes': self.system_classes,
            'class_mapping': self.class_mapping,
            'total_parameters': self.model.count_params() if self.model else 0,
            'model_loaded': self._initialized
        })
        return base_status

def load_trashnet_model():
    """Função para carregar o modelo TrashNet (compatibilidade)"""
    from src.core.service_factory import ServiceFactory
    return ServiceFactory.get_service('trashnet_model')