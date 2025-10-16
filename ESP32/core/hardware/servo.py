# core/hardware_manager.py - HARDWARE COM CLASSES OTIMIZADAS
from machine import Pin, PWM
from utils import get_logger

logger = get_logger("Servo")

SERVO_PIN = 18
SERVO_FREQ = 50
SERVO_MIN_DUTY = 40
SERVO_MAX_DUTY = 115

class ServoController:
    """Controlador para servo motor"""
    def __init__(self):
        try:
            self.pwm = PWM(Pin(SERVO_PIN, Pin.OUT))
            self.pwm.freq(SERVO_FREQ)
            self.min_duty = SERVO_MIN_DUTY
            self.max_duty = SERVO_MAX_DUTY
            self.current_angle = 90
            self.available = True
            logger.success("✅ Servo inicializado")
        except Exception as e:
            logger.error(f"❌ Servo não disponível: {e}")
            self.available = False
    
    def move(self, angle):
        if not self.available:
            return False
        
        try:
            angle = max(0, min(180, angle))
            duty_range = self.max_duty - self.min_duty
            duty = int(self.min_duty + (angle / 180) * duty_range)
            
            duty_u16 = int((duty / 1023) * 65535)
            
            self.pwm.duty_u16(duty_u16)
            self.current_angle = angle
            logger.debug(f"🔧 Servo movido para {angle}°")
            return True
        except Exception as e:
            logger.error(f"❌ Erro movimento servo: {e}")
            return False
    
    def move_to_waste_type(self, waste_index):
        """Move servo para tipo de lixo específico"""
        angles = [0, 45, 90, 135, 180]
        if 0 <= waste_index < len(angles):
            return self.move(angles[waste_index])
        return False
    
    def get_status(self):
        return {
            'type': 'servo',
            'angle': self.current_angle,
            'available': self.available
        }
    
    def cleanup(self):
        """Limpeza do servo"""
        if self.available:
            self.move(90)  # Posição neutra
            self.pwm.deinit()
