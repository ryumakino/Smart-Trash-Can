import cv2
import time
import threading
from typing import Optional
from src.core.base_classes import BaseService

class CameraManager(BaseService):
    """Gerenciador de câmera para captura de imagens"""
    
    def __init__(self):
        super().__init__("CameraManager")
        self.camera = None
        self.lock = threading.Lock()
        
    def _initialize_impl(self) -> bool:
        from src.config.config_manager import CONFIG_MANAGER
        camera_config = CONFIG_MANAGER.get_camera_config()
        
        camera_index = camera_config.get("CAMERA_INDEX", 0)
        self.camera = cv2.VideoCapture(camera_index)
        
        if not self.camera.isOpened():
            self.logger.error(f"❌ Não foi possível abrir câmera no índice {camera_index}")
            return False
        
        # Configurar resolução
        width = camera_config.get("CAPTURE_WIDTH", 640)
        height = camera_config.get("CAPTURE_HEIGHT", 480)
        self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        
        # Warmup da câmera
        self._warmup_camera()
        
        self.logger.info(f"✅ Câmera inicializada: {width}x{height}")
        return True
    
    def _cleanup_impl(self):
        if self.camera and self.camera.isOpened():
            self.camera.release()
    
    def _warmup_camera(self):
        """Aguarda a câmera estabilizar"""
        for i in range(5):
            ret, frame = self.camera.read()
            if ret:
                break
            time.sleep(0.5)
    
    def capture_frame(self) -> Optional:
        """Captura um frame da câmera de forma thread-safe"""
        with self.lock:
            if not self.camera or not self.camera.isOpened():
                self.logger.error("Câmera não disponível")
                return None
            
            ret, frame = self.camera.read()
            if ret and frame is not None:
                # Converter BGR para RGB
                return cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            else:
                self.logger.error("Falha ao capturar frame")
                return None