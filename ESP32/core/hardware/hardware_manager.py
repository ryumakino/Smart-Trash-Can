from utils import get_logger
from core.hardware.sensor import IRSensor
from core.hardware.servo import ServoController
from core.hardware.led import LEDIndicator

logger = get_logger("Hardware")

class HardwareManager:
    """Facade para gerenciar todo o hardware - CORRIGIDO"""
    
    def __init__(self, config_methods):
        self.config = config_methods
        self.components = {}
        self._initialize_components()
    
    def _initialize_components(self):
        """Inicializa todos os componentes de hardware"""
        try:
            self.components['led'] = LEDIndicator() 
            self.components['servo'] = ServoController()
            
            # IR Sensor
            self.components['ir_sensor'] = IRSensor()
            
            logger.success("✅ Todos os componentes de hardware inicializados")
            
        except Exception as e:
            logger.error(f"❌ Erro inicialização hardware: {e}")
    
    def get_component(self, name):
        """Obtém componente pelo nome"""
        return self.components.get(name)
    
    def get_hardware_info(self):
        """Retorna status de todo o hardware"""
        return {name: comp.get_status() for name, comp in self.components.items()}
    
    def cleanup(self):
        """Limpeza de todos os componentes"""
        for name, component in self.components.items():
            try:
                if hasattr(component, 'cleanup'):
                    component.cleanup()
                elif hasattr(component, 'off'):
                    component.off()
            except Exception as e:
                logger.error(f"❌ Erro limpando {name}: {e}")