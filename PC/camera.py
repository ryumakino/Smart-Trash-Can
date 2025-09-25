import cv2
import numpy as np
import os
import time
from typing import Optional
from config import CameraConfig
from utils import log_error, log_info

def capture_image() -> Optional[np.ndarray]:
    """Captura uma imagem única da câmera e retorna em formato compatível com o modelo"""
    cap = cv2.VideoCapture(CameraConfig.CAMERA_INDEX)

    if not cap.isOpened():
        log_error("Câmera não disponível")
        return None

    try:
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, CameraConfig.CAPTURE_WIDTH)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CameraConfig.CAPTURE_HEIGHT)

        # Aquece a câmera
        for _ in range(CameraConfig.CAMERA_WARMUP_ATTEMPTS):
            ret, frame = cap.read()
            if ret:
                break
            time.sleep(CameraConfig.CAMERA_WARMUP_DELAY)
        else:
            log_error("Falha no aquecimento da câmera")
            return None

        # Timer para estabilização de luz
        log_info("Câmera ativada. Aguardando 3 segundos para estabilização da luz...")
        for i in range(3, 0, -1):
            log_info(f"Capturando em {i} segundo(s)...")
            time.sleep(1)

        # Captura final
        log_info("📸 Capturando imagem agora!")
        ret, frame = cap.read()
        if not ret or frame is None:
            log_error("Falha ao capturar imagem")
            return None

        processed = preprocess_image(frame)

        log_info("Imagem capturada com sucesso")
        return processed

    except Exception as e:
        log_error(f"ERRO na captura: {e}")
        return None
    finally:
        cap.release()

def preprocess_image(frame: np.ndarray) -> Optional[np.ndarray]:
    """Pré-processa a imagem para o modelo ML"""
    try:
        img = cv2.resize(frame, (224, 224))  # tamanho esperado pelo modelo
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        img = img.astype("float32") / 255.0  # normalização
        return img
    except Exception as e:
        log_error(f"ERRO no pré-processamento: {e}")
        return None

def save_image_to_test(image_array, filename_prefix="captured"):
    """Salva a imagem na pasta 'test/'"""
    try:
        test_dir = "test"
        if not os.path.exists(test_dir):
            os.makedirs(test_dir)
            log_info(f"Diretório criado: {test_dir}")

        timestamp = int(time.time())
        filename = f"{test_dir}/{filename_prefix}_{timestamp}.jpg"

        if len(image_array.shape) == 3:
            image_bgr = cv2.cvtColor((image_array * 255).astype('uint8'), cv2.COLOR_RGB2BGR)
        else:
            image_bgr = (image_array * 255).astype('uint8')

        cv2.imwrite(filename, image_bgr)
        log_info(f"Imagem salva em: {filename}")
        return filename
    except Exception as e:
        log_error(f"Erro ao salvar imagem na pasta test: {e}")
        return None
