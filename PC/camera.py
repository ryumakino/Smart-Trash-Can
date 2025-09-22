import cv2
import numpy as np
from typing import Optional
from utils import log_error, log_success, log_info
import os

# Configurações
CAMERA_ID: int = 0
IMAGE_SAVE_DIR: str = "data/captured"
IMAGE_SAVE_PATH: str = f"{IMAGE_SAVE_DIR}/waste_capture"
IMAGE_WIDTH: int = 512
IMAGE_HEIGHT: int = 384
CAPTURE_WIDTH: int = 1280
CAPTURE_HEIGHT: int = 720
IMAGE_FORMAT: str = "jpg"
SAVE_IMAGES: bool = True
DISPLAY_TIME_MS: int = 1000
BLUR_KERNEL: tuple = (5, 5)
CAMERA_WARMUP_ATTEMPTS: int = 10
CAMERA_WARMUP_DELAY: float = 0.5

def ensure_directory():
    """Garante que o diretório de imagens existe"""
    if not os.path.exists(IMAGE_SAVE_DIR):
        os.makedirs(IMAGE_SAVE_DIR)
        log_info(f"Diretório criado: {IMAGE_SAVE_DIR}")

def capture_image() -> Optional[np.ndarray]:
    """Captura uma imagem da câmera."""
    ensure_directory()
    
    cap = cv2.VideoCapture(CAMERA_ID)
    if not cap.isOpened():
        log_error("Câmera não disponível")
        return None

    try:
        # Configurações da câmera
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAPTURE_WIDTH)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAPTURE_HEIGHT)
        cap.set(cv2.CAP_PROP_AUTOFOCUS, 1)
        cap.set(cv2.CAP_PROP_BRIGHTNESS, 0.5)
        cap.set(cv2.CAP_PROP_CONTRAST, 0.5)

        # Warm-up da câmera
        log_info("Aquecendo câmera...")
        for i in range(CAMERA_WARMUP_ATTEMPTS):
            ret, frame = cap.read()
            if ret:
                log_success(f"Câmera pronta após {i+1} tentativas")
                break
            time.sleep(CAMERA_WARMUP_DELAY)
        else:
            log_error("Falha no aquecimento da câmera")
            return None

        # Captura frame final
        ret, frame = cap.read()
        if not ret or frame is None:
            log_error("Falha ao capturar imagem")
            return None

        # Salva imagem se necessário
        if SAVE_IMAGES:
            timestamp = int(time.time())
            filename = f"{IMAGE_SAVE_PATH}_{timestamp}.{IMAGE_FORMAT}"
            cv2.imwrite(filename, frame)
            log_success(f"Imagem salva: {filename}")

        log_info("Imagem capturada com sucesso")
        return frame

    except Exception as e:
        log_error(f"ERRO na captura: {e}")
        return None
    finally:
        cap.release()

def preprocess_image(frame: np.ndarray) -> Optional[np.ndarray]:
    """Pré-processa a imagem para o modelo ML."""
    if frame is None:
        return None
        
    try:
        # Redimensiona
        img = cv2.resize(frame, (IMAGE_WIDTH, IMAGE_HEIGHT))
        
        # Converte cor (BGR para RGB)
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        
        # Normaliza pixels
        img = img.astype("float32") / 255.0
        
        # Aplica blur para reduzir ruído
        img = cv2.GaussianBlur(img, BLUR_KERNEL, 0)
        
        return img
        
    except Exception as e:
        log_error(f"ERRO no pré-processamento: {e}")
        return None

def display_image(frame: np.ndarray, title: str = "Imagem Capturada") -> None:
    """Exibe a imagem (apenas para debug)."""
    try:
        # Converte back para BGR para exibição
        display_frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        cv2.imshow(title, display_frame)
        cv2.waitKey(DISPLAY_TIME_MS)
        cv2.destroyAllWindows()
    except Exception as e:
        log_error(f"ERRO ao exibir imagem: {e}")

# Adiciona import time se necessário
import time