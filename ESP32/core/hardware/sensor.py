from machine import Pin
import uasyncio as asyncio
import time
from utils import get_logger

logger = get_logger("Sensor")

IR_PIN = 34

class IRSensor:
    """Sensor infravermelho de movimento"""
    
    def __init__(self):
        try:
            self.pin = Pin(IR_PIN, Pin.IN, Pin.PULL_UP)
            self.callback = None
            self.detection_count = 0
            self.last_detection = 0
            self.available = True
            logger.success("✅ Sensor IR inicializado")
        except Exception as e:
            logger.error(f"❌ Sensor IR não disponível: {e}")
            self.available = False
    
    async def start_monitoring(self):
        """Inicia monitoramento contínuo do sensor"""
        if not self.available:
            return
        
        last_state = self.pin.value()
        logger.info("🔍 Iniciando monitoramento IR")
        
        while True:
            try:
                current_state = self.pin.value()
                
                # Detecção de movimento (queda para LOW)
                if current_state == 0 and last_state == 1:
                    self.detection_count += 1
                    self.last_detection = time.time()
                    
                    if self.callback:
                        await self.callback()
                
                last_state = current_state
                await asyncio.sleep(0.1)  # 100ms
                
            except Exception as e:
                logger.error(f"❌ Erro monitoramento IR: {e}")
                await asyncio.sleep(1)
    
    def get_status(self):
        return {
            'type': 'ir_sensor',
            'detections': self.detection_count,
            'last_detection': self.last_detection,
            'available': self.available
        }