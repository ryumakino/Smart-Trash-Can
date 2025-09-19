from machine import Pin, PWM
import time
from config import (
    SERVO_PIN, SERVO_FREQUENCY, SERVO_DUTY_MIN, SERVO_DUTY_MAX,
    SERVO_DUTY_RANGE, NEUTRAL_POSITION, SERVO_POSITIONS, WASTE_TYPES,
    SERVO_MOVEMENT_DELAY, MSG_SERVO_INITIALIZED, MSG_SERVO_MOVING,
    MSG_SERVO_POSITIONED, MSG_ERROR
)
from utils import log_message, safe_int, clamp

class ServoController:
    def __init__(self):
        self.servo = PWM(Pin(SERVO_PIN), freq=SERVO_FREQUENCY)
        self.current_angle = NEUTRAL_POSITION
        self.initialized = False
        
    def angle_to_duty(self, angle: int) -> int:
        """Convert angle to PWM duty cycle."""
        angle = clamp(angle, 0, 180)
        return int(SERVO_DUTY_MIN + (angle / 180) * SERVO_DUTY_RANGE)

    def initialize(self) -> bool:
        """Initialize the servo at the neutral position."""
        try:
            self.move_to_angle(NEUTRAL_POSITION)
            self.initialized = True
            log_message("INFO", "Servo initialized at neutral position")
            return True
        except Exception as e:
            log_message("ERROR", f"Servo initialization failed: {e}")
            return False

    def move_to_waste_type(self, waste_type: int) -> bool:
        """Move the servo to the position for the waste type."""
        if waste_type < 0 or waste_type >= len(SERVO_POSITIONS):
            log_message("ERROR", f"Invalid waste type: {waste_type}")
            self.move_to_angle(NEUTRAL_POSITION)
            return False
        
        target_angle = SERVO_POSITIONS[waste_type]
        return self.move_to_angle(target_angle) is not None

    def move_to_angle(self, angle: int) -> int:
        """Move servo to a specific angle."""
        try:
            angle = clamp(angle, 0, 180)
            
            # Smooth movement
            current_duty = self.servo.duty()
            target_duty = self.angle_to_duty(angle)
            
            steps = 10
            for i in range(steps + 1):
                intermediate_duty = current_duty + (target_duty - current_duty) * i // steps
                self.servo.duty(intermediate_duty)
                time.sleep_ms(SERVO_MOVEMENT_DELAY // steps)
            
            self.current_angle = angle
            return angle
            
        except Exception as e:
            log_message("ERROR", f"Servo movement failed: {e}")
            return -1

    def calibrate(self, min_duty: int = None, max_duty: int = None) -> bool:
        """Calibrate servo duty cycle values."""
        # Nota: Em MicroPython, variáveis globais do config não podem ser modificadas diretamente
        # Esta função precisaria ser adaptada para seu caso específico
        log_message("INFO", "Calibration not implemented in class version")
        return False

    def get_status(self) -> dict:
        """Get current servo status."""
        from utils import get_uptime_ms
        
        return {
            'pin': SERVO_PIN,
            'initialized': self.initialized,
            'current_angle': self.current_angle,
            'neutral_position': NEUTRAL_POSITION,
            'waste_positions': SERVO_POSITIONS,
            'frequency': SERVO_FREQUENCY,
            'duty_min': SERVO_DUTY_MIN,
            'duty_max': SERVO_DUTY_MAX,
            'duty_range': SERVO_DUTY_RANGE,
            'timestamp': get_uptime_ms()
        }

# Instância global
servo_controller = ServoController()
servo_controller.initialize()