# camera_manager.py - Refatorado com BaseService
import cv2
import time
import os
from threading import Lock
from src.core.base_classes import BaseService, ConfigurableMixin

class CameraManager(BaseService, ConfigurableMixin):
    def __init__(self):
        super().__init__('camera')
        self.camera_lock = Lock()
        self.camera = None
        
    def initialize(self):
        """Inicializar câmera usando configuração centralizada"""
        if self._initialized:
            return True
            
        with self.camera_lock:
            try:
                camera_index = self.get_config_value('CAMERA_INDEX', 0)
                self.camera = cv2.VideoCapture(camera_index)
                
                if not self.camera.isOpened():
                    # Tentar diferentes índices (configurável)
                    max_camera_index = self.get_config_value('MAX_CAMERA_INDEX', 3)
                    for i in range(max_camera_index):
                        self.camera = cv2.VideoCapture(i)
                        if self.camera.isOpened():
                            self.logger.info(f"Câmera encontrada no índice {i}")
                            break
                    else:
                        self.logger.error("Nenhuma câmera detectada")
                        return False
                
                # Configurar usando valores da configuração
                self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, self.get_config_value('CAPTURE_WIDTH', 640))
                self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, self.get_config_value('CAPTURE_HEIGHT', 480))
                self.camera.set(cv2.CAP_PROP_FPS, 30)
                
                # Aquecimento com valores configuráveis
                warmup_attempts = self.get_config_value('CAMERA_WARMUP_ATTEMPTS', 5)
                warmup_delay = self.get_config_value('CAMERA_WARMUP_DELAY', 0.5)
                
                for _ in range(warmup_attempts):
                    ret, frame = self.camera.read()
                    if ret:
                        break
                    time.sleep(warmup_delay)
                
                self._initialized = True
                self.logger.success("Câmera inicializada com sucesso")
                return True
                
            except Exception as e:
                self.logger.error(f"Erro na inicialização da câmera: {e}")
                return False
    
    def capture_image(self):
        """Capturar imagem da câmera"""
        if not self.initialize():
            return None
            
        try:
            with self.camera_lock:
                ret, frame = self.camera.read()
                if not ret or frame is None:
                    self.logger.error("Falha ao capturar imagem")
                    return None
                
                # Converter BGR para RGB (OpenCV usa BGR, modelo espera RGB)
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                self.logger.info("Imagem capturada com sucesso")
                return frame_rgb
                
        except Exception as e:
            self.logger.error(f"Erro na captura: {e}")
            return None
    
    def save_image(self, image, filename_prefix="capture"):
        """Salvar imagem para debug/teste"""
        try:
            test_images_dir = self.get_config_value('TEST_IMAGES_DIR', 'test_images', 'system')
            os.makedirs(test_images_dir, exist_ok=True)
            timestamp = int(time.time())
            filename = f"{test_images_dir}/{filename_prefix}_{timestamp}.jpg"
            
            # Converter RGB para BGR para salvar com OpenCV
            image_bgr = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
            cv2.imwrite(filename, image_bgr)
            self.logger.info(f"Imagem salva: {filename}")
            return filename
            
        except Exception as e:
            self.logger.error(f"Erro ao salvar imagem: {e}")
            return None
    
    def cleanup(self):
        """Liberar recursos da câmera"""
        with self.camera_lock:
            if self.camera and self.camera.isOpened():
                self.camera.release()
            self._initialized = False
            self.logger.info("Câmera liberada")