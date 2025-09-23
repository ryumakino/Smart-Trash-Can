import machine
import time
import _thread
from config import ESP32Config
from utils import get_logger

logger = get_logger("ESP32_IR")

# --- Classe IRSensor ---
class IRSensor:
    def __init__(self, pin=ESP32Config.IR_SENSOR_PIN, callback=None, check_interval=0.1, active_high=True):
        self.active_high = active_high
        self.pin = machine.Pin(pin, machine.Pin.IN,
                               machine.Pin.PULL_DOWN if active_high else machine.Pin.PULL_UP)
        self.callback = callback
        self.check_interval = check_interval
        self.last_state = None
        self.running = True
        _thread.start_new_thread(self._monitor, ())

    def is_detected(self):
        val = self.pin.value()
        return val == 1 if self.active_high else val == 0

    def _monitor(self):
        consecutive_detections = 0
        threshold = 2
        while self.running:
            detected = self.is_detected()
            consecutive_detections = consecutive_detections + 1 if detected else 0
            confirmed = consecutive_detections >= threshold
            if confirmed != self.last_state:
                self.last_state = confirmed
                if confirmed:
                    logger.info(f"[IRSensor] Movimento detectado! Pin={self.pin.value()}")
                    if self.callback:
                        self.callback()
            time.sleep(self.check_interval)

    def get_raw_value(self):
        return self.pin.value()

    def stop(self):
        self.running = False
