from machine import Pin, PWM
import time
from config_manager import ConfigManager
from utils import get_logger

logger = get_logger("ServoController")

class ServoController:
    def __init__(self, pin=None):
        self.config_mgr = ConfigManager()
        servo_config = self.config_mgr.get_servo_config()
        
        pin = pin or servo_config.get('SERVO_PIN', 18)
        self.pwm = PWM(Pin(pin))
        self.pwm.freq(servo_config.get('SERVO_FREQ', 50))
        self.current_angle = 90
        self.servo_config = servo_config
        self.move(90)  # Posição neutra
        logger.info("Servo inicializado")
    
    def angle_to_duty(self, angle):
        """Converte ângulo para duty cycle"""
        angle = max(0, min(180, angle))
        min_duty = self.servo_config.get('SERVO_MIN_DUTY', 40)
        max_duty = self.servo_config.get('SERVO_MAX_DUTY', 115)
        return int(min_duty + (angle / 180) * (max_duty - min_duty))
    
    def move(self, angle):
        """Move servo para ângulo específico"""
        try:
            duty = self.angle_to_duty(angle)
            self.pwm.duty(duty)
            self.current_angle = angle
            return True
        except Exception as e:
            logger.error(f"Erro no servo: {e}")
            return False
    
    def waste_angles(self, waste_index: int):
        """Move o servo de acordo com o índice do resíduo, evitando movimentos repetidos"""
        try:
            servo_angles = self.servo_config.get('SERVO_ANGLES', [0, 30, 60, 90, 120, 150])
            waste_types = self.servo_config.get('WASTE_TYPES', ["PLASTICO", "PAPEL", "VIDRO", "METAL", "LIXO", "PAPELAO"])
            
            # Verifica se o índice é válido
            if waste_index < 0 or waste_index >= len(servo_angles):
                logger.error(f"Índice inválido para resíduo: {waste_index}")
                return

            # Verifica se já estamos no mesmo tipo de resíduo
            if hasattr(self, "last_waste_index") and self.last_waste_index == waste_index:
                logger.info(f"Resíduo {waste_types[waste_index]} já selecionado. Servo não será movido.")
                return

            angle = servo_angles[waste_index]
            waste_name = waste_types[waste_index]

            logger.info(f"Movendo servo para {waste_name} (ângulo: {angle})")
            self.move(angle)
            time.sleep(self.servo_config.get('SERVO_RESET_DELAY', 3))
            self.reset()
            logger.success(f"Servo resetado após movimentar {waste_name}")

            # Atualiza o último resíduo movimentado
            self.last_waste_index = waste_index

        except Exception as e:
            logger.error(f"Erro ao mover o servo: {e}")
    
    def reset(self):
        """Volta para posição neutra"""
        self.move(90)
        logger.info("Resetando posição")