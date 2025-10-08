# hardware_manager.py - CORREÇÕES
from machine import Pin, PWM
import uasyncio as asyncio
import time  # CORREÇÃO: Adicionar import
from utils import get_logger

logger = get_logger("HardwareManager")

class PinManager:
    @staticmethod
    def create_output(pin):
        return Pin(pin, Pin.OUT)
    
    @staticmethod
    def create_input(pin, pull=None):
        if pull == Pin.PULL_UP:
            return Pin(pin, Pin.IN, Pin.PULL_UP)
        elif pull == Pin.PULL_DOWN:
            return Pin(pin, Pin.IN, Pin.PULL_DOWN)
        return Pin(pin, Pin.IN)

class PWMManager:
    @staticmethod
    def create_pwm(pin, freq=50):
        pwm = PWM(Pin(pin))
        pwm.freq(freq)
        return pwm
    
    @staticmethod
    def angle_to_duty(angle, min_duty=40, max_duty=115):
        angle = max(0, min(180, angle))
        return int(min_duty + (angle / 180) * (max_duty - min_duty))

class HardwareComponent:
    def get_status(self):
        raise NotImplementedError
    
    def initialize(self):
        raise NotImplementedError
    
    def cleanup(self):
        raise NotImplementedError

class BaseComponent:
    def initialize(self):
        raise NotImplementedError
    
    def cleanup(self):
        raise NotImplementedError
    
    def get_status(self):
        raise NotImplementedError

class LEDController(BaseComponent):
    def __init__(self, pin):
        self.pin = PinManager.create_output(pin)
        self.state = False
    
    def initialize(self):
        self.off()
        return True
    
    def on(self): self._set_state(True)
    def off(self): self._set_state(False)
    
    def _set_state(self, state):
        self.pin.value(state)
        self.state = state
    
    def get_status(self):
        return {'type': 'LED', 'state': self.state}
    
    def cleanup(self):
        self.off()

class IRSensor(HardwareComponent):
    def __init__(self, pin, active_high=True, check_interval=0.1, threshold=2):
        try:
            if active_high:
                self.pin = Pin(pin, Pin.IN, Pin.PULL_DOWN)
            else:
                self.pin = Pin(pin, Pin.IN, Pin.PULL_UP)
        except:
            self.pin = Pin(pin, Pin.IN)

        self.active_high = active_high
        self.check_interval = check_interval
        self.threshold = threshold
        self.last_state = None
        self.running = False
        self.task = None
        self.callback = None
        self.detection_count = 0
    
    def initialize(self):
        self.last_state = self.is_detected()
        return True
    
    def is_detected(self):
        val = self.pin.value()
        return val == 1 if self.active_high else val == 0
    
    async def _monitor_loop(self):
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
                logger.error(f"Erro no monitoramento: {e}")
                await asyncio.sleep(self.check_interval)
    
    async def _execute_callback(self):
        try:
            if asyncio.iscoroutinefunction(self.callback):
                await self.callback()
            else:
                self.callback()
        except Exception as e:
            logger.error(f"Erro no callback: {e}")
    
    def start(self, callback=None):
        if callback:
            self.callback = callback
            
        if not self.running:
            self.running = True
            self.task = asyncio.create_task(self._monitor_loop())
            logger.info("IRSensor iniciado")
    
    def stop(self):
        self.running = False
        if self.task:
            self.task.cancel()
        logger.info("IRSensor parado")
    
    def get_status(self):
        return {
            'type': 'IR_SENSOR',
            'running': self.running,
            'last_state': self.last_state,
            'detection_count': self.detection_count,
            'active_high': self.active_high
        }
    
    def cleanup(self):
        self.stop()

class ServoController(BaseComponent):
    def __init__(self, pin=18, freq=50, min_duty=40, max_duty=115):
        try:
            self.pwm = PWMManager.create_pwm(pin, freq)
            self.min_duty = min_duty
            self.max_duty = max_duty
            self.available = True
        except Exception as e:
            logger.error(f"Servo não disponível: {e}")
            self.available = False
        
        self.current_angle = 90
    
    def initialize(self):
        return self.move(90)
    
    def move(self, angle):
        if not self.available:
            return False
        
        try:
            duty = PWMManager.angle_to_duty(angle, self.min_duty, self.max_duty)
            self.pwm.duty(duty)
            self.current_angle = angle
            return True
        except Exception as e:
            logger.error(f"Erro ao mover servo: {e}")
            return False
    
    def get_status(self):
        return {
            'type': 'SERVO', 
            'current_angle': self.current_angle,
            'available': self.available
        }
    
    def cleanup(self):
        if self.available:
            self.move(90)

class HardwareManager:
    def __init__(self, system_config, ir_config, servo_config):
        self.components = {}
        self._initialize_components(system_config, ir_config, servo_config)
    
    def _initialize_components(self, system_config, ir_config, servo_config):
        components_config = [
            ('led', LEDController, system_config.get('STATUS_LED_PIN', 2)),
            ('servo', ServoController, {
                'pin': servo_config.get('SERVO_PIN', 18),
                'freq': servo_config.get('SERVO_FREQ', 50),
                'min_duty': servo_config.get('SERVO_MIN_DUTY', 40),
                'max_duty': servo_config.get('SERVO_MAX_DUTY', 115)
            }),
            # CORREÇÃO: Adicionar sensor IR com nome correto
            ('ir', IRSensor, {
                'pin': ir_config.get('IR_SENSOR_PIN', 34),
                'active_high': ir_config.get('ACTIVE_HIGH', True),
                'check_interval': ir_config.get('CHECK_INTERVAL', 0.1),
                'threshold': ir_config.get('DETECTION_THRESHOLD', 2)
            })
        ]
        
        for name, component_class, config in components_config:
            try:
                if isinstance(config, dict):
                    instance = component_class(**config)
                else:
                    instance = component_class(config)
                
                if instance.initialize():
                    self.components[name] = instance
                    logger.success(f"Componente {name} inicializado")
            except Exception as e:
                logger.error(f"Erro ao inicializar {name}: {e}")
    
    def get_component(self, name):
        return self.components.get(name)
    
    def get_hardware_info(self):
        return {name: comp.get_status() for name, comp in self.components.items()}
    
    def cleanup_all(self):
        for name, component in self.components.items():
            try:
                component.cleanup()
            except Exception as e:
                logger.error(f"Erro ao limpar {name}: {e}")