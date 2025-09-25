import machine
import uasyncio as asyncio
from config import IRSensorConfig
from utils import get_logger

logger = get_logger("ESP32_IR")

class IRSensor:
    def __init__(self, callback=None):
        self.active_high = IRSensorConfig.ACTIVE_HIGH
        self.pin = machine.Pin(
            IRSensorConfig.IR_SENSOR_PIN,
            machine.Pin.IN,
            machine.Pin.PULL_DOWN if self.active_high else machine.Pin.PULL_UP
        )
        self.callback = callback
        self.check_interval = IRSensorConfig.CHECK_INTERVAL
        self.last_state = None
        self.running = False
        self.task = None

    def is_detected(self):
        val = self.pin.value()
        return val == 1 if self.active_high else val == 0

    async def _monitor_loop(self):
        consecutive_detections = 0
        threshold = 2
        while self.running:
            detected = self.is_detected()
            consecutive_detections = consecutive_detections + 1 if detected else 0
            confirmed = consecutive_detections >= threshold
            if confirmed != self.last_state:
                self.last_state = confirmed
                if confirmed:
                    logger.info("[IRSensor] Movimento detectado!")
                    if self.callback:
                        await self._maybe_await_callback()
            await asyncio.sleep(self.check_interval)

    async def _maybe_await_callback(self):
        """
        Se a callback for assíncrona, faz await. Se for normal, executa direto.
        """
        if asyncio.iscoroutinefunction(self.callback):
            await self.callback()
        else:
            self.callback()

    def start(self):
        if not self.running:
            self.running = True
            self.task = asyncio.create_task(self._monitor_loop())
            logger.info("IRSensor iniciado")

    def stop(self):
        self.running = False
        if self.task:
            self.task.cancel()
        logger.info("IRSensor parado")

    def get_raw_value(self):
        return self.pin.value()
