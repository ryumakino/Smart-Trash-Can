# trashnet_model.py - Adaptado para TensorFlow 2.20+
import os
os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"
import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Conv2D, MaxPooling2D, Flatten, Dense, Dropout, BatchNormalization
from tensorflow.keras.optimizers import Adam
import numpy as np
from config import TrashNetConfig
from utils import get_logger

logger = get_logger("TrashNetModel")

class TrashNetModel:
    def __init__(self, weights_path=None):
        self.input_size = TrashNetConfig.MODEL_INPUT_SIZE
        self.original_classes = TrashNetConfig.ORIGINAL_CLASSES
        self.system_classes = TrashNetConfig.SYSTEM_CLASSES
        self.class_mapping = TrashNetConfig.CLASS_MAPPING
        
        # Construir modelo
        self.model = self._build_model()
        
        if weights_path:
            self.load_weights(weights_path)
    
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
            
            # Fully Connected
            Flatten(),
            Dense(512, activation='relu'),
            Dropout(0.5),
            Dense(256, activation='relu'),
            Dropout(0.5),
            Dense(len(self.original_classes), activation='softmax')
        ])
        
        # Compilar modelo
        model.compile(
            optimizer=Adam(learning_rate=0.001),
            loss='categorical_crossentropy',
            metrics=['accuracy']
        )
        
        return model
    
    def load_weights(self, weights_path):
        """Carregar pesos do modelo com fallback"""
        try:
            self.model.load_weights(weights_path)
            logger.success(f"Pesos carregados de {weights_path}")
        except Exception as e:
            logger.warning(f"Pesos não encontrados, inicializando aleatoriamente: {e}")
            # Inicializar com input shape específico
            self.model.build(input_shape=(None, *self.input_size, 3))
    
    def preprocess_image(self, image):
        """Pré-processamento otimizado"""
        # Converter para tensor se necessário
        if not tf.is_tensor(image):
            image = tf.convert_to_tensor(image, dtype=tf.float32)
        
        # Redimensionar
        image_resized = tf.image.resize(image, self.input_size)
        
        # Normalizar [0, 1] se necessário
        if tf.reduce_max(image_resized) > 1.0:
            image_resized = image_resized / 255.0
        
        # Adicionar dimensão de batch
        image_batch = tf.expand_dims(image_resized, axis=0)
        
        return image_batch
    
    def predict(self, image):
        """Fazer predição com tratamento de erro"""
        try:
            # Pré-processar
            processed_image = self.preprocess_image(image)
            
            # Predição
            predictions = self.model(processed_image, training=False)
            predicted_class_idx = np.argmax(predictions[0])
            confidence = float(predictions[0][predicted_class_idx])
            
            # Mapear classes
            original_class = self.original_classes[predicted_class_idx]
            system_class = self.class_mapping.get(original_class, original_class.upper())
            
            # Encontrar índice no sistema
            try:
                system_idx = self.system_classes.index(system_class)
            except ValueError:
                system_idx = -1
            
            return {
                'original_class': original_class,
                'system_class': system_class,
                'system_index': system_idx,
                'confidence': confidence,
                'all_predictions': predictions[0].numpy().tolist()
            }
            
        except Exception as e:
            logger.error(f"Erro na predição: {e}")
            return None
    
    def summary(self):
        """Mostrar resumo do modelo"""
        self.model.summary()

# Instância global com fallback
def load_trashnet_model():
    """Carregar modelo com tratamento robusto"""
    try:
        model = TrashNetModel(TrashNetConfig.MODEL_WEIGHTS_PATH)
        
        # Teste de predição simples
        test_input = np.random.random((*TrashNetConfig.MODEL_INPUT_SIZE, 3))
        test_result = model.predict(test_input)
        
        if test_result:
            logger.success("✅ Modelo TrashNet carregado e testado com sucesso")
            return model
        else:
            logger.warning("⚠️ Modelo carregado mas predição falhou")
            return model
            
    except Exception as e:
        logger.error(f"❌ Falha crítica ao carregar modelo: {e}")
        return None

TRASHNET_MODEL = load_trashnet_model()