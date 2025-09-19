import cv2
import numpy as np
import traceback
from typing import Optional, Any
from config import (
    CAMERA_ID,
    CAPTURE_WIDTH,
    CAPTURE_HEIGHT,
    CAMERA_WARMUP_ATTEMPTS,
    SAVE_IMAGES,
    IMAGE_SAVE_PATH,
    IMAGE_FORMAT,
    IMAGE_WIDTH,
    IMAGE_HEIGHT,
    BLUR_KERNEL,
    DISPLAY_TIME_MS,
    LOG_MOVEMENT_DETECTED,
    LOG_CLASSIFICATION_ERROR,
    LOG_SEND_OK,
    LOG_SEND_FAIL,
    LOG_IMAGE_FAIL,
    LOG_IMAGE_ERROR,
    WASTE_TYPES
)
from setup_communication import send_waste_type
from utils import log_error, log_success, log_camera

def process_movement(model: Optional[Any]) -> None:
    """Processa movimento detectado e classificação de lixo."""
    from ml_model import classify_waste

    log_camera(LOG_MOVEMENT_DETECTED)
    try:
        image = capture_image()
        if image is not None:
            waste_type = None
            try:
                if model:
                    waste_type = classify_waste(model, image)
                if waste_type is None:
                    log_error(LOG_CLASSIFICATION_ERROR)
            except Exception as e:
                log_error(f"{LOG_CLASSIFICATION_ERROR}: {e}")
                traceback.print_exc()

            # Envia tipo de lixo para ESP32
            if waste_type is not None and send_waste_type(waste_type):
                log_success(f"{LOG_SEND_OK}: {waste_type} ({WASTE_TYPES[waste_type]})")
            else:
                log_error(LOG_SEND_FAIL)
        else:
            log_error(LOG_IMAGE_FAIL)
    except Exception as e:
        log_error(f"{LOG_IMAGE_ERROR}: {e}")
        traceback.print_exc()


def capture_image() -> Optional[np.ndarray]:
    """Captura uma imagem da câmera e salva se necessário."""
    cap = cv2.VideoCapture(CAMERA_ID)
    try:
        if not cap.isOpened():
            log_error("Camera unavailable")
            return None

        cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAPTURE_WIDTH)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAPTURE_HEIGHT)
        cap.set(cv2.CAP_PROP_AUTOFOCUS, 1)

        frame, ret = None, False
        for _ in range(CAMERA_WARMUP_ATTEMPTS):
            ret, frame = cap.read()
            if ret:
                break

        if not ret or frame is None:
            log_error("Failed to capture image")
            return None

        if SAVE_IMAGES:
            filename = f"{IMAGE_SAVE_PATH}.{IMAGE_FORMAT}"
            cv2.imwrite(filename, frame)
            log_success(f"Image captured and saved as {filename}")
        else:
            log_success("Image captured (not saved)")

        return frame
    except Exception as e:
        log_error(f"ERROR capturing image: {e}")
        return None
    finally:
        cap.release()


def preprocess_image(frame: np.ndarray) -> Optional[np.ndarray]:
    """Pré-processa a imagem para entrada do modelo ML."""
    if frame is None:
        return None
    try:
        img = cv2.resize(frame, (IMAGE_WIDTH, IMAGE_HEIGHT))
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        img = img.astype("float32") / 255.0
        img = cv2.GaussianBlur(img, BLUR_KERNEL, 0)
        return img
    except Exception as e:
        log_error(f"ERROR in image preprocessing: {e}")
        return None


def display_image(frame: np.ndarray, title: str = "Captured Image") -> None:
    """Exibe a imagem (para debug)."""
    try:
        display_frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        cv2.imshow(title, display_frame)
        cv2.waitKey(DISPLAY_TIME_MS)
        cv2.destroyAllWindows()
    except Exception as e:
        log_error(f"ERROR displaying image: {e}")
