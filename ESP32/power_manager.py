# power_manager.py
import machine
import time
from utils import get_logger

logger = get_logger("PowerManager")

class SleepExecutor:
    """SRP: Execução de sleep"""
    
    @staticmethod
    def light_sleep(seconds):
        try:
            machine.lightsleep(seconds * 1000)
        except Exception as e:
            logger.error(f"Light sleep falhou: {e}")
            time.sleep(seconds)  # Fallback
    
    @staticmethod
    def deep_sleep(seconds):
        try:
            machine.deepsleep(seconds * 1000)
        except Exception as e:
            logger.error(f"Deep sleep falhou: {e}")

class PowerOptimizer:
    """SRP: Otimização de energia"""
    
    @staticmethod
    def get_optimization_settings(conditions):
        battery_level = conditions.get('battery_level', 100)
        network_activity = conditions.get('network_activity', 'low')
        
        if battery_level < 20:
            return {
                'light_sleep_interval': 30,
                'deep_sleep_interval': 300,
                'recommendation': 'BATERIA_BAIXA'
            }
        elif network_activity == 'low':
            return {
                'light_sleep_interval': 10,
                'deep_sleep_interval': 180,
                'recommendation': 'ATIVIDADE_BAIXA'
            }
        else:
            return {
                'light_sleep_interval': 5,
                'deep_sleep_interval': 60,
                'recommendation': 'MODO_NORMAL'
            }

class PowerManager:
    """Facade: Gerenciador de energia"""
    
    def __init__(self):
        self.sleep_executor = SleepExecutor()
        self.optimizer = PowerOptimizer()
        self.sleep_enabled = True
    
    def light_sleep(self, seconds):
        if self.sleep_enabled:
            self.sleep_executor.light_sleep(seconds)
        else:
            time.sleep(seconds)
    
    def deep_sleep(self, seconds):
        if self.sleep_enabled:
            self.sleep_executor.deep_sleep(seconds)
    
    def get_power_status(self):
        return {
            'sleep_enabled': self.sleep_enabled,
            'wake_reason': self._get_wake_reason(),
            'timestamp': time.time()
        }
    
    def _get_wake_reason(self):
        wake_reason = machine.reset_cause()
        reasons = {
            machine.PWRON_RESET: "POWER_ON",
            machine.DEEPSLEEP_RESET: "DEEP_SLEEP",
        }
        return reasons.get(wake_reason, "UNKNOWN")
    
    def optimize(self, conditions):
        return self.optimizer.get_optimization_settings(conditions)