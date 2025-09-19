import machine
import utime as time
from hardware_utils import log_message
from udp_comm import udp_comm       # sua classe UDPComm
from serial_comm import serial_comm # sua classe SerialComm
from config import PIR_SENSOR_PIN

class IRSensor:
    def __init__(self):
        self.sensor = machine.Pin(PIR_SENSOR_PIN, machine.Pin.IN)
        self.last_state = 0
        self.interval_ms = 500
        self.udp = udp_comm
        self.serial = serial_comm
        self._callback = None  # callback para movimento
        self.detected = False  # ← Adicione este atributo para rastrear o estado

        # Inicializa UDP se fornecido
        if self.udp and not self.udp.initialized:
            self.udp.initialize()
            self.udp.discover_peer()

    def is_detected(self):
        """Retorna True se movimento está sendo detectado no momento"""
        return self.sensor.value()

    def send_message(self, message: str):
        if self.serial and self.serial.initialized:
            self.serial.send(message)
        if self.udp and self.udp.peer_addr:
            self.udp.send(message)
        log_message("INFO", f"Sensor -> {message}")

    def set_callback(self, callback):
        """Define uma função que será chamada quando movimento for detectado."""
        self._callback = callback

    def monitor(self):
        log_message("INFO", "Starting IR sensor monitoring...")
        while True:
            state = self.read()
            if state != self.last_state:
                if state == 1:
                    self.detected = True  # ← Atualiza o estado
                    self.send_message("Movement detected!")
                    if self._callback:
                        self._callback(True)
                else:
                    self.detected = False  # ← Atualiza o estado
                    self.send_message("Area free")
                    if self._callback:
                        self._callback(False)
                self.last_state = state
            time.sleep_ms(self.interval_ms)

sensor_controller = IRSensor()