from machine import Pin
import time
import _thread
from utils import log_info, log_error

class IRSensor:
    def __init__(self, pin=34, callback=None, debounce_time=200):
        self.ir = Pin(pin, Pin.IN)
        self.last_state = 0
        self.last_detection = 0
        self.callback = callback
        self.debounce_time = debounce_time  # ms
        self.running = False
        self.thread = None

    def monitor(self):
        """Monitora sensor IR com debounce"""
        log_info("Iniciando monitoramento do sensor IR")
        
        while self.running:
            try:
                current_state = self.ir.value()
                current_time = time.ticks_ms()
                
                # Detecta transição de estado com debounce
                if (current_state != self.last_state and 
                    time.ticks_diff(current_time, self.last_detection) > self.debounce_time):
                    
                    self.last_state = current_state
                    self.last_detection = current_time
                    
                    if current_state == 1:  # Detecção ativa
                        log_info("[IR] Movimento detectado")
                        if self.callback:
                            self.callback()
                
                time.sleep(0.05)  # Polling a cada 50ms
                
            except Exception as e:
                log_error(f"Erro no sensor IR: {e}")
                time.sleep(1)

    def start(self):
        """Inicia monitoramento em thread separada"""
        if not self.running:
            self.running = True
            self.thread = _thread.start_new_thread(self.monitor, ())

    def stop(self):
        """Para o monitoramento"""
        self.running = False
        log_info("Sensor IR parado")