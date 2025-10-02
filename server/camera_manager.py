import cv2
import time
import os
from threading import Lock
from config import CameraConfig, SystemConfig
from utils import get_logger

logger = get_logger("CameraManager")

class CameraManager:
    def __init__(self):
        self.camera_lock = Lock()
        self.camera = None
        self.is_initialized = False
        
    def initialize(self):
        """Inicializar câmera"""
        with self.camera_lock:
            if self.is_initialized:
                return True
                
            try:
                self.camera = cv2.VideoCapture(CameraConfig.CAMERA_INDEX)
                
                if not self.camera.isOpened():
                    # Tentar diferentes índices de câmera
                    for i in range(3):
                        self.camera = cv2.VideoCapture(i)
                        if self.camera.isOpened():
                            logger.info(f"Câmera encontrada no índice {i}")
                            break
                    else:
                        logger.error("Nenhuma câmera detectada")
                        return False
                
                # Configurar câmera
                self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, CameraConfig.CAPTURE_WIDTH)
                self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, CameraConfig.CAPTURE_HEIGHT)
                self.camera.set(cv2.CAP_PROP_FPS, 30)
                
                # Aquecimento
                for _ in range(CameraConfig.CAMERA_WARMUP_ATTEMPTS):
                    ret, frame = self.camera.read()
                    if ret:
                        break
                    time.sleep(CameraConfig.CAMERA_WARMUP_DELAY)
                
                self.is_initialized = True
                logger.success("Câmera inicializada com sucesso")
                return True
                
            except Exception as e:
                logger.error(f"Erro na inicialização da câmera: {e}")
                return False
    
    def capture_image(self):
        """Capturar imagem da câmera"""
        if not self.initialize():
            return None
            
        try:
            with self.camera_lock:
                ret, frame = self.camera.read()
                if not ret or frame is None:
                    logger.error("Falha ao capturar imagem")
                    return None
                
                # Converter BGR para RGB (OpenCV usa BGR, modelo espera RGB)
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                logger.info("Imagem capturada com sucesso")
                return frame_rgb
                
        except Exception as e:
            logger.error(f"Erro na captura: {e}")
            return None
    
    def save_image(self, image, filename_prefix="capture"):
        """Salvar imagem para debug/teste"""
        try:
            os.makedirs(SystemConfig.TEST_IMAGES_DIR, exist_ok=True)
            timestamp = int(time.time())
            filename = f"{SystemConfig.TEST_IMAGES_DIR}/{filename_prefix}_{timestamp}.jpg"
            
            # Converter RGB para BGR para salvar com OpenCV
            image_bgr = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
            cv2.imwrite(filename, image_bgr)
            logger.info(f"Imagem salva: {filename}")
            return filename
            
        except Exception as e:
            logger.error(f"Erro ao salvar imagem: {e}")
            return None
    
    def cleanup(self):
        """Liberar recursos da câmera"""
        with self.camera_lock:
            if self.camera and self.camera.isOpened():
                self.camera.release()
            self.is_initialized = False
            logger.info("Câmera liberada")

# Instância global
CAMERA_MANAGER = CameraManager()