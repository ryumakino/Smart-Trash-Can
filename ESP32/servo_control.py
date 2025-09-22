from machine import Pin, PWM
import time
from utils import log_info, log_error

class Servo:
    def __init__(self, pin=18, freq=50, min_duty=40, max_duty=155, neutral=90):
        self.pin = pin
        self.freq = freq
        self.min_duty = min_duty
        self.max_duty = max_duty
        self.neutral = neutral
        self.duty_range = max_duty - min_duty
        self.current_angle = neutral
        
        try:
            self.pwm = PWM(Pin(self.pin), freq=self.freq)
            self.move(self.neutral)  # Posição inicial
            log_info(f"Servo inicializado no pino {pin}")
        except Exception as e:
            log_error(f"Erro ao inicializar servo: {e}")
            self.pwm = None

    def angle_to_duty(self, angle):
        """Converte ângulo para valor de duty cycle"""
        angle = max(0, min(180, angle))
        duty = int(self.min_duty + (angle / 180) * self.duty_range)
        return duty

    def move(self, angle):
        """Move servo para ângulo específico"""
        if self.pwm is None:
            log_error("Servo não disponível")
            return False
            
        try:
            angle = max(0, min(180, angle))
            duty = self.angle_to_duty(angle)
            self.pwm.duty(duty)
            self.current_angle = angle
            
            log_info(f"Servo movido para {angle}°")
            return True
            
        except Exception as e:
            log_error(f"Erro ao mover servo: {e}")
            return False

    def reset_servo(self):
        """Retorna servo para posição neutra"""
        log_info(f"Resetando servo para {self.neutral}°")
        return self.move(self.neutral)

    def sweep(self, start=0, end=180, step=10, delay=0.1):
        """Movimento de varredura para teste"""
        if self.pwm is None:
            return
            
        log_info("Iniciando teste de varredura do servo")
        for angle in range(start, end + 1, step):
            self.move(angle)
            time.sleep(delay)
        self.reset_servo()