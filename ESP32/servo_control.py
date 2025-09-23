from machine import Pin, PWM
import time
from config import ESP32Config
from utils import get_logger

logger = get_logger("Servo")

class ServoController:
    def __init__(self, pin=ESP32Config.SERVO_PIN):
        self.pwm = PWM(Pin(pin))
        self.pwm.freq(ESP32Config.SERVO_FREQ)
        self.current_angle = 90
        self.move(90)  # Posição neutra
        logger.info("Servo inicializado")
    
    def angle_to_duty(self, angle):
        """Converte ângulo para duty cycle"""
        angle = max(0, min(180, angle))
        return int(ESP32Config.SERVO_MIN_DUTY + 
                  (angle / 180) * (ESP32Config.SERVO_MAX_DUTY - ESP32Config.SERVO_MIN_DUTY))
    
    def move(self, angle):
        """Move servo para ângulo específico"""
        try:
            duty = self.angle_to_duty(angle)
            self.pwm.duty(duty)
            self.current_angle = angle
            logger.info(f"Servo: {angle}°")
            return True
        except Exception as e:
            logger.error(f"Erro no servo: {e}")
            return False
    
    def reset(self):
        """Volta para posição neutra"""
        self.move(90)