from machine import Pin
import uasyncio as asyncio
from utils import get_logger

logger = get_logger("LEDIndicator")

class LEDIndicator:
    """Indicador LED de status"""
    
    def __init__(self, pin=2):
        try:
            self.led = Pin(pin, Pin.OUT)
            self.state = False
            self.available = True
            self.off()  # Inicia desligado
            logger.success("✅ LED inicializado")
        except Exception as e:
            logger.error(f"❌ LED não disponível: {e}")
            self.available = False
    
    def on(self):
        if self.available:
            self.led.value(1)
            self.state = True
    
    def off(self):
        if self.available:
            self.led.value(0)
            self.state = False
    
    def toggle(self):
        if self.available:
            self.led.value(not self.led.value())
            self.state = not self.state
    
    async def blink(self, times=3, delay=0.2):
        """Piscar LED padrão"""
        for _ in range(times):
            self.toggle()
            await asyncio.sleep(delay)
        self.off()
    
    def get_status(self):
        return {
            'type': 'led',
            'state': self.state,
            'available': self.available
        }