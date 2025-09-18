import random
import numpy as np
import tensorflow as tf
from config import *
from camera import preprocess_image
from utils import log_message, log_error, log_info, log_success, random_waste_fallback

# -------------------------
# Main Functions
# -------------------------
def load_model():
    """Loads the machine learning model"""
    try:
        model = tf.keras.models.load_model(MODEL_PATH)
        log_success(LOG_MODEL_LOAD_OK)
        return model
    except Exception as e:
        log_error(f"{LOG_MODEL_LOAD_ERROR}: {e}")
        log_info(LOG_MODEL_FALLBACK)
        return None

def classify_waste(model, image):
    """Classifies the type of waste in the image"""
    if model is None:
        return random_waste_fallback(LOG_MODEL_NOT_LOADED)

    try:
        processed_img = preprocess_image(image)
        if processed_img is None:
            raise ValueError(LOG_MODEL_PREPROCESS_FAIL)
        
        # Prepare input for the model
        input_data = np.expand_dims(processed_img, axis=0)
        predictions = model.predict(input_data, verbose=0)

        predicted_class = int(np.argmax(predictions[0]))
        confidence = float(np.max(predictions[0]))

        log_message(LOG_PREFIX_MODEL, 
                    f"{LOG_MODEL_CLASSIFICATION}: {WASTE_TYPES[predicted_class]} (Confidence: {confidence:.2%})")

        if confidence >= CONFIDENCE_THRESHOLD:
            return predicted_class
        else:
            return random_waste_fallback(LOG_MODEL_LOW_CONFIDENCE)

    except Exception as e:
        return random_waste_fallback(f"{LOG_MODEL_CLASSIFICATION_ERROR}: {e}")

def get_model_summary(model):
    """Returns a summary of the model (useful for debugging)"""
    if model is None:
        return LOG_MODEL_NOT_LOADED
    
    summary_lines = []
    model.summary(print_fn=lambda x: summary_lines.append(x))
    return "\n".join(summary_lines)