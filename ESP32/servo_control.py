from machine import Pin, PWM
import time
from config import ServoConfig
from utils import get_logger

logger = get_logger("Servo")

class ServoController:
    def __init__(self, pin=ServoConfig.SERVO_PIN):
        self.pwm = PWM(Pin(pin))
        self.pwm.freq(ServoConfig.SERVO_FREQ)
        self.current_angle = 90
        self.move(90)  # Posição neutra
        logger.info("Servo inicializado")
    
    def angle_to_duty(self, angle):
        """Converte ângulo para duty cycle"""
        angle = max(0, min(180, angle))
        return int(ServoConfig.SERVO_MIN_DUTY + 
                  (angle / 180) * (ServoConfig.SERVO_MAX_DUTY - ServoConfig.SERVO_MIN_DUTY))
    
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
            # Verifica se o índice é válido
            if waste_index < 0 or waste_index >= len(ServoConfig.SERVO_ANGLES):
                logger.error(f"Índice inválido para resíduo: {waste_index}")
                return

            # Verifica se já estamos no mesmo tipo de resíduo
            if hasattr(self, "last_waste_index") and self.last_waste_index == waste_index:
                logger.info(f"Resíduo {ServoConfig.WASTE_TYPES[waste_index]} já selecionado. Servo não será movido.")
                return

            angle = ServoConfig.SERVO_ANGLES[waste_index]
            waste_name = ServoConfig.WASTE_TYPES[waste_index]

            logger.info(f"Movendo servo para {waste_name} (ângulo: {angle})")
            self.move(angle)
            time.sleep(ServoConfig.SERVO_RESET_DELAY)
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