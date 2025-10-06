# hardware_manager.py
import machine
from machine import Pin, PWM
import uasyncio as asyncio
from utils import get_logger

logger = get_logger("HardwareManager")

class HardwareComponent:
    """Interface base para componentes - LSP"""
    
    def get_status(self):
        raise NotImplementedError
    
    def initialize(self):
        raise NotImplementedError
    
    def cleanup(self):
        raise NotImplementedError

class LEDController(HardwareComponent):
    """SRP: Controlar apenas LED"""
    
    def __init__(self, pin):
        self.pin = Pin(pin, Pin.OUT)
        self.state = False
    
    def initialize(self):
        self.off()
        return True
    
    def on(self):
        self.pin.value(1)
        self.state = True
    
    def off(self):
        self.pin.value(0)
        self.state = False
    
    def toggle(self):
        self.pin.value(not self.pin.value())
        self.state = not self.state
    
    def get_status(self):
        return {
            'type': 'LED',
            'state': self.state,
            'pin': self.pin.__class__.__name__
        }
    
    def cleanup(self):
        self.off()

class IRSensor(HardwareComponent):
    """SRP: Gerenciar sensor IR"""
    
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
    
    def initialize(self):
        self.last_state = self.is_detected()
        return True
    
    def is_detected(self):
        """Verificar detecção - SRP"""
        val = self.pin.value()
        return val == 1 if self.active_high else val == 0
    
    async def _monitor_loop(self):
        """Loop de monitoramento - SRP"""
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
        """Executar callback de forma segura - DRY"""
        try:
            if asyncio.iscoroutinefunction(self.callback):
                await self.callback()
            else:
                self.callback()
        except Exception as e:
            logger.error(f"Erro no callback: {e}")
    
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
        return {
            'type': 'IR_SENSOR',
            'running': self.running,
            'last_state': self.last_state,
            'detection_count': self.detection_count,
            'active_high': self.active_high
        }
    
    def cleanup(self):
        self.stop()

class ServoController(HardwareComponent):
    """SRP: Controlar servo motor"""
    
    def __init__(self, pin=18, freq=50, min_duty=40, max_duty=115):
        self.pwm = PWM(Pin(pin))
        self.pwm.freq(freq)
        self.min_duty = min_duty
        self.max_duty = max_duty
        self.current_angle = 90
        self.last_waste_index = None
        self.move_count = 0
    
    def initialize(self):
        self.move(90)  # Posição neutra
        return True
    
    def angle_to_duty(self, angle):
        """Converter ângulo para duty cycle - SRP"""
        angle = max(0, min(180, angle))
        return int(self.min_duty + (angle / 180) * (self.max_duty - self.min_duty))
    
    def move(self, angle):
        """Mover para ângulo específico - SRP"""
        try:
            duty = self.angle_to_duty(angle)
            self.pwm.duty(duty)
            self.current_angle = angle
            self.move_count += 1
            logger.debug(f"Servo movido para {angle}°")
            return True
        except Exception as e:
            logger.error(f"Erro ao mover servo: {e}")
            return False
    
    async def move_to_waste(self, waste_index, servo_config):
        """Mover para tipo de resíduo - OCP"""
        try:
            servo_angles = servo_config.get('SERVO_ANGLES', [0, 45, 90, 135, 180])
            waste_types = servo_config.get('WASTE_TYPES', ["Repouso", "Plástico", "Papel", "Metal", "Vidro"])
            
            if waste_index < 0 or waste_index >= len(servo_angles):
                logger.error(f"Índice inválido: {waste_index}")
                return False

            # Evitar movimento repetido - DRY
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
        return {
            'type': 'SERVO',
            'current_position': self.current_angle,
            'last_waste_index': self.last_waste_index,
            'move_count': self.move_count,
            'min_duty': self.min_duty,
            'max_duty': self.max_duty
        }
    
    def cleanup(self):
        self.reset()

class HardwareManager:
    """Composite: Gerenciar todos os componentes - SRP"""
    
    def __init__(self, system_config, ir_config, servo_config):
        self.components = {}
        self._initialize_components(system_config, ir_config, servo_config)
    
    def _initialize_components(self, system_config, ir_config, servo_config):
        """Inicializar componentes - DRY"""
        component_configs = [
            ('led', LEDController, system_config.get('STATUS_LED_PIN', 2)),
            ('ir_sensor', IRSensor, ir_config),
            ('servo', ServoController, servo_config)
        ]
        
        for name, component_class, config in component_configs:
            try:
                if name == 'led':
                    instance = component_class(config)
                else:
                    instance = component_class(**config) if isinstance(config, dict) else component_class()
                
                if instance.initialize():
                    self.components[name] = instance
                    logger.success(f"Componente {name} inicializado")
                else:
                    logger.error(f"Falha ao inicializar {name}")
                    
            except Exception as e:
                logger.error(f"Erro ao inicializar {name}: {e}")
    
    def get_component(self, component_name):
        """Obter componente por nome - ISP"""
        return self.components.get(component_name)
    
    def set_led_status(self, status):
        """Controlar LED - Facade pattern"""
        led = self.get_component('led')
        if led:
            led.on() if status else led.off()
    
    def get_hardware_info(self):
        """Obter informações de todos os componentes - DRY"""
        return {
            name: component.get_status()
            for name, component in self.components.items()
        }
    
    def cleanup_all(self):
        """Limpar todos os componentes - DRY"""
        for name, component in self.components.items():
            try:
                component.cleanup()
                logger.info(f"Componente {name} limpo")
            except Exception as e:
                logger.error(f"Erro ao limpar {name}: {e}")