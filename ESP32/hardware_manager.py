# hardware_manager.py
import machine
from machine import Pin, PWM
import uasyncio as asyncio
from utils import get_logger

logger = get_logger("HardwareManager")

class HardwareManager:
    """Gerenciador unificado de hardware - Responsabilidade Centralizada"""
    
    def __init__(self, config_manager):
        self.config_mgr = config_manager
        self.components = {}
        self._initialize_components()
    
    def _initialize_components(self):
        """Inicializar todos os componentes de hardware"""
        try:
            # LED de status
            system_config = self.config_mgr.get_system_config()
            self.status_led = Pin(system_config.get('STATUS_LED_PIN', 2), Pin.OUT)
            self.status_led.off()
            
            # Sensor IR
            ir_config = self.config_mgr.get_ir_config()
            self.ir_sensor = IRSensor(
                pin=ir_config.get('IR_SENSOR_PIN', 34),
                active_high=ir_config.get('ACTIVE_HIGH', True),
                check_interval=ir_config.get('CHECK_INTERVAL', 0.1),
                threshold=ir_config.get('DETECTION_THRESHOLD', 2)
            )
            
            # Servo
            servo_config = self.config_mgr.get_servo_config()
            self.servo = ServoController(
                pin=servo_config.get('SERVO_PIN', 18),
                freq=servo_config.get('SERVO_FREQ', 50),
                min_duty=servo_config.get('SERVO_MIN_DUTY', 40),
                max_duty=servo_config.get('SERVO_MAX_DUTY', 115)
            )
            
            logger.success("Todos os componentes de hardware inicializados")
            
        except Exception as e:
            logger.error(f"Erro na inicialização do hardware: {e}")
            raise
    
    def get_component(self, component_name):
        """Obter componente por nome"""
        return getattr(self, component_name, None)
    
    def set_led_status(self, status):
        """Controlar LED de status"""
        self.status_led.value(status)
    
    def blink_led(self, interval=0.5):
        """Piscar LED"""
        self.status_led.value(not self.status_led.value())
        return interval
    
    def get_hardware_info(self):
        """Obter informações do hardware"""
        return {
            'status_led': 'OK' if self.status_led else 'ERROR',
            'ir_sensor': 'OK' if self.ir_sensor else 'ERROR',
            'servo': 'OK' if self.servo else 'ERROR',
            'components_initialized': len([c for c in [self.status_led, self.ir_sensor, self.servo] if c])
        }


class IRSensor:
    """Sensor IR refatorado - Responsabilidade Específica"""
    
    def __init__(self, pin, active_high=True, check_interval=0.1, threshold=2):
        self.pin = Pin(pin, Pin.IN, Pin.PULL_DOWN if active_high else Pin.PULL_UP)
        self.active_high = active_high
        self.check_interval = check_interval
        self.threshold = threshold
        self.last_state = None
        self.running = False
        self.task = None
        self.callback = None
        self.detection_count = 0

    def is_detected(self):
        """Verificar detecção"""
        val = self.pin.value()
        return val == 1 if self.active_high else val == 0

    async def _monitor_loop(self):
        """Loop de monitoramento"""
        consecutive_detections = 0
        
        while self.running:
            try:
                detected = self.is_detected()
                consecutive_detections = consecutive_detections + 1 if detected else 0
                confirmed = consecutive_detections >= self.threshold
                
                if confirmed != self.last_state:
                    self.last_state = confirmed
                    if confirmed and self.callback:
                        self.detection_count += 1
                        await self._execute_callback()
                
                await asyncio.sleep(self.check_interval)
            except Exception as e:
                logger.error(f"Erro no loop do sensor: {e}")
                await asyncio.sleep(self.check_interval)

    async def _execute_callback(self):
        """Executar callback de forma segura"""
        try:
            if asyncio.iscoroutinefunction(self.callback):
                await self.callback()
            else:
                self.callback()
        except Exception as e:
            logger.error(f"Erro no callback do sensor: {e}")

    def start(self, callback=None):
        """Iniciar monitoramento"""
        if callback:
            self.callback = callback
            
        if not self.running:
            self.running = True
            self.task = asyncio.create_task(self._monitor_loop())
            logger.info("IRSensor iniciado")

    def stop(self):
        """Parar monitoramento"""
        self.running = False
        if self.task:
            self.task.cancel()
        logger.info("IRSensor parado")
    
    def get_status(self):
        """Obter status do sensor"""
        return {
            'running': self.running,
            'last_state': self.last_state,
            'detection_count': self.detection_count,
            'pin': self.pin.__class__.__name__,
            'active_high': self.active_high
        }


class ServoController:
    """Controlador de Servo refatorado - Responsabilidade Específica"""
    
    def __init__(self, pin=18, freq=50, min_duty=40, max_duty=115):
        self.pwm = PWM(Pin(pin))
        self.pwm.freq(freq)
        self.min_duty = min_duty
        self.max_duty = max_duty
        self.current_angle = 90
        self.last_waste_index = None
        self.move_count = 0
        self.move(90)  # Posição neutra
        logger.info("ServoController inicializado")

    def angle_to_duty(self, angle):
        """Converter ângulo para duty cycle"""
        angle = max(0, min(180, angle))
        return int(self.min_duty + (angle / 180) * (self.max_duty - self.min_duty))

    def move(self, angle):
        """Mover para ângulo específico"""
        try:
            duty = self.angle_to_duty(angle)
            self.pwm.duty(duty)
            self.current_angle = angle
            self.move_count += 1
            logger.debug(f"Servo movido para {angle}° (duty: {duty})")
            return True
        except Exception as e:
            logger.error(f"Erro ao mover servo: {e}")
            return False

    async def move_to_waste(self, waste_index, servo_config=None):
        """Mover para tipo de resíduo específico"""
        try:
            if servo_config is None:
                servo_config = {
                    'SERVO_ANGLES': [0, 45, 90, 135, 180],
                    'WASTE_TYPES': ["Repouso", "Plástico", "Papel", "Metal", "Vidro"],
                    'SERVO_RESET_DELAY': 3
                }
            
            servo_angles = servo_config.get('SERVO_ANGLES', [0, 45, 90, 135, 180])
            waste_types = servo_config.get('WASTE_TYPES', ["Repouso", "Plástico", "Papel", "Metal", "Vidro"])
            
            if waste_index < 0 or waste_index >= len(servo_angles):
                logger.error(f"Índice de resíduo inválido: {waste_index}")
                return False

            # Evitar movimento repetido
            if self.last_waste_index == waste_index:
                logger.info(f"Resíduo {waste_types[waste_index]} já selecionado")
                return True

            angle = servo_angles[waste_index]
            waste_name = waste_types[waste_index]
            
            logger.info(f"Movendo para {waste_name} (ângulo: {angle})")
            
            success = self.move(angle)
            if success:
                await asyncio.sleep(servo_config.get('SERVO_RESET_DELAY', 3))
                self.reset()
                self.last_waste_index = waste_index
                logger.success(f"Movimento para {waste_name} concluído")
            
            return success
            
        except Exception as e:
            logger.error(f"Erro ao mover para resíduo: {e}")
            return False

    def reset(self):
        """Resetar para posição neutra"""
        return self.move(90)

    def get_status(self):
        """Obter status do servo"""
        return {
            'current_position': self.current_angle,
            'last_waste_index': self.last_waste_index,
            'move_count': self.move_count,
            'initialized': True,
            'min_duty': self.min_duty,
            'max_duty': self.max_duty
        }