# camera_manager_refactored.py – DRY + SOLID
import cv2, time, os, threading
from src.core.base_classes import BaseService, ConfigurableMixin

class CameraManager(BaseService, ConfigurableMixin):
    def __init__(self):
        super().__init__('camera')
        self._lock = threading.Lock()
        self._camera = None

    # ---------- lifecycle ---------- #
    def initialize(self) -> bool:
        if self._initialized: return True
        with self._lock:
            self._camera = self._try_open_camera()
            if self._camera is None:
                self.logger.error("Nenhuma câmera detectada")
                return False
            self._warmup()
            self._initialized = True
            self.logger.success("Câmera inicializada com sucesso")
            return True

    # ---------- public api ---------- #
    def capture_image(self):
        if not self.initialize(): return None
        with self._lock:
            ok, frame = self._camera.read()
            if not ok or frame is None:
                self.logger.error("Falha ao capturar imagem")
                return None
            return cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    def save_image(self, image, prefix="capture"):
        try:
            folder = self.get_config_value('TEST_IMAGES_DIR', 'test_images', 'system')
            os.makedirs(folder, exist_ok=True)
            path = f"{folder}/{prefix}_{int(time.time())}.jpg"
            cv2.imwrite(path, cv2.cvtColor(image, cv2.COLOR_RGB2BGR))
            self.logger.info(f"Imagem salva: {path}")
            return path
        except Exception as e:
            self.logger.error(f"Erro ao salvar imagem: {e}")
            return None

    def cleanup(self):
        with self._lock:
            if self._camera and self._camera.isOpened():
                self._camera.release()
            self._initialized = False
            self.logger.info("Câmera liberada")

    # ---------- helpers ---------- #
    def _try_open_camera(self):
        idx = self.get_config_value('CAMERA_INDEX', 0)
        max_idx = self.get_config_value('MAX_CAMERA_INDEX', 3)
        for i in [idx] + list(range(max_idx)):
            cam = cv2.VideoCapture(i)
            if cam.isOpened():
                self.logger.info(f"Câmera encontrada no índice {i}")
                self._setup_resolution(cam)
                return cam
        return None

    def _setup_resolution(self, cam):
        w = self.get_config_value('CAPTURE_WIDTH', 640)
        h = self.get_config_value('CAPTURE_HEIGHT', 480)
        cam.set(cv2.CAP_PROP_FRAME_WIDTH, w)
        cam.set(cv2.CAP_PROP_FRAME_HEIGHT, h)
        cam.set(cv2.CAP_PROP_FPS, 30)

    def _warmup(self):
        attempts = self.get_config_value('CAMERA_WARMUP_ATTEMPTS', 5)
        delay = self.get_config_value('CAMERA_WARMUP_DELAY', 0.5)
        for _ in range(attempts):
            if self._camera.read()[0]: break
            time.sleep(delay)