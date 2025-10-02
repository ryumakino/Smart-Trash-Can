# power_manager.py - Gerenciamento de energia
import machine
import time
from utils import get_logger

logger = get_logger("PowerManager")

class PowerManager:
    def __init__(self):
        self.wake_reason = machine.reset_cause()
        self.sleep_enabled = True
        logger.info(f"Wake reason: {self.wake_reason}")
    
    def light_sleep(self, seconds):
        """Sleep leve para economizar energia"""
        if not self.sleep_enabled:
            time.sleep(seconds)
            return
            
        try:
            logger.info(f"Entering light sleep for {seconds}s")
            # Configurar wake-up sources
            machine.lightsleep(seconds * 1000)
        except Exception as e:
            logger.error(f"Light sleep error: {e}")
            time.sleep(seconds)
    
    def deep_sleep(self, seconds):
        """Deep sleep para longos períodos"""
        if not self.sleep_enabled:
            logger.warning("Deep sleep disabled")
            return
            
        try:
            logger.info(f"Entering deep sleep for {seconds}s")
            # Configurar GPIO wake-up se necessário
            machine.deepsleep(seconds * 1000)
        except Exception as e:
            logger.error(f"Deep sleep error: {e}")
    
    def disable_sleep(self):
        """Desabilitar sleep (para debugging)"""
        self.sleep_enabled = False
        logger.warning("Sleep disabled")
    
    def enable_sleep(self):
        """Habilitar sleep"""
        self.sleep_enabled = True
        logger.info("Sleep enabled")