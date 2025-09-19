from machine import Pin, Timer
import time
from config import PIR_SENSOR_PIN, MOVEMENT_TIMEOUT_MS, MSG_MOVEMENT_DETECTED, PREFIX_CANAL, MSG_TIMEOUT, DEBOUNCE_DELAY_MS
from hardware_utils import log_message

class PIRSensor:
    def __init__(self):
        self.pir_sensor = Pin(PIR_SENSOR_PIN, Pin.IN)
        self.movement_timer = Timer(1)
        self.last_movement_time = 0
        self.movement_detected = False
        self.callback_handler = None
        self.first_trigger_ignored = False  # <- flag nova

    def pir_callback(self, pin) -> None:
        """PIR sensor interrupt callback function."""
        try:
            if pin.value() == 1:
                if not self.first_trigger_ignored:
                    log_message("DEBUG", "Ignoring first PIR trigger (warm-up)")
                    self.first_trigger_ignored = True
                    return
                
                self.movement_detected = True
                self.last_movement_time = time.ticks_ms()
                
                if self.callback_handler:
                    self.callback_handler()
        except Exception as e:
            log_message("ERROR", f"PIR callback error: {e}")

    def initialize(self, callback_handler=None) -> bool:
        """Initialize PIR sensor with interrupt."""
        try:
            self.callback_handler = callback_handler
            
            # CORREÇÃO: usar sleep_ms em vez de sleep
            time.sleep_ms(2000)  # 2 segundos para estabilização
            
            self.pir_sensor.irq(trigger=Pin.IRQ_RISING, handler=self.pir_callback)
            
            # Start timeout timer
            self.movement_timer.init(period=1000, mode=Timer.PERIODIC, callback=self.check_movement_timeout)
            
            log_message("INFO", "PIR sensor initialized with interrupt")
            return True
        except Exception as e:
            log_message("ERROR", f"PIR sensor initialization failed: {e}")
            return False

    def detect_movement(self) -> bool:
        """Detect movement via PIR sensor."""
        return self.movement_detected

    def check_movement_timeout(self, timer=None) -> None:
        """Check for movement timeout."""
        current_time = time.ticks_ms()
        if (self.movement_detected and 
            time.ticks_diff(current_time, self.last_movement_time) > MOVEMENT_TIMEOUT_MS):
            log_message("WARNING", "Movement timeout - no selection made")
            self.reset_detection()

    def reset_detection(self) -> None:
        """Reset movement detection flags."""
        self.movement_detected = False
        log_message("DEBUG", "Movement detection reset")

    def get_status(self) -> dict:
        """Get current PIR sensor status."""
        return {
            'movement_detected': self.movement_detected,
            'time_since_detection': time.ticks_diff(time.ticks_ms(), self.last_movement_time) if self.movement_detected else 0,
            'sensor_value': self.pir_sensor.value(),
            'sensor_pin': PIR_SENSOR_PIN,
            'debounce_delay': DEBOUNCE_DELAY_MS,
            'last_detection_time': self.last_movement_time
        }

# Instância global
pir_sensor = PIRSensor()