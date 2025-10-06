# power_manager.py
import machine
import time
from utils import get_logger

logger = get_logger("PowerManager")

class SleepStrategy:
    """SRP: Estratégias de sleep"""
    
    @staticmethod
    def light_sleep(seconds: int):
        """Sleep leve para economizar energia"""
        try:
            logger.info(f"Entering light sleep for {seconds}s")
            machine.lightsleep(seconds * 1000)
        except Exception as e:
            logger.error(f"Light sleep error: {e}")
            time.sleep(seconds)  # Fallback
    
    @staticmethod
    def deep_sleep(seconds: int):
        """Deep sleep para longos períodos"""
        try:
            logger.info(f"Entering deep sleep for {seconds}s")
            machine.deepsleep(seconds * 1000)
        except Exception as e:
            logger.error(f"Deep sleep error: {e}")
    
    @staticmethod
    def get_wake_reason() -> str:
        """Obter motivo do wakeup"""
        wake_reason = machine.reset_cause()
        reasons = {
            machine.PWRON_RESET: "POWER_ON",
            machine.HARD_RESET: "HARD_RESET",
            machine.WDT_RESET: "WATCHDOG",
            machine.DEEPSLEEP_RESET: "DEEP_SLEEP",
            machine.SOFT_RESET: "SOFT_RESET"
        }
        return reasons.get(wake_reason, "UNKNOWN")

class PowerMonitor:
    """SRP: Monitorar consumo de energia"""
    
    def __init__(self):
        self.operation_start_time = 0
        self.sleep_start_time = 0
        self.total_operation_time = 0
        self.total_sleep_time = 0
    
    def start_operation(self):
        """Iniciar período de operação"""
        self.operation_start_time = time.time()
        if self.sleep_start_time > 0:
            self.total_sleep_time += time.time() - self.sleep_start_time
            self.sleep_start_time = 0
    
    def start_sleep(self):
        """Iniciar período de sleep"""
        self.sleep_start_time = time.time()
        if self.operation_start_time > 0:
            self.total_operation_time += time.time() - self.operation_start_time
            self.operation_start_time = 0
    
    def get_power_stats(self) -> dict:
        """Obter estatísticas de energia"""
        current_time = time.time()
        
        # Calcular tempos atuais
        current_operation = 0
        current_sleep = 0
        
        if self.operation_start_time > 0:
            current_operation = current_time - self.operation_start_time
        if self.sleep_start_time > 0:
            current_sleep = current_time - self.sleep_start_time
        
        total_operation = self.total_operation_time + current_operation
        total_sleep = self.total_sleep_time + current_sleep
        total_time = total_operation + total_sleep
        
        operation_percent = (total_operation / total_time * 100) if total_time > 0 else 0
        
        return {
            'current_operation_time': current_operation,
            'current_sleep_time': current_sleep,
            'total_operation_time': total_operation,
            'total_sleep_time': total_sleep,
            'operation_percentage': operation_percent,
            'efficiency_score': 100 - operation_percent  # Quanto menor operação, mais eficiente
        }

class PowerManager:
    """Composite: Gerenciador de energia principal"""
    
    def __init__(self):
        self.sleep_strategy = SleepStrategy()
        self.power_monitor = PowerMonitor()
        self.sleep_enabled = True
        self.wake_reason = self.sleep_strategy.get_wake_reason()
        
        logger.info(f"Wake reason: {self.wake_reason}")
        self.power_monitor.start_operation()  # Sistema inicia em operação
    
    def light_sleep(self, seconds: int):
        """Sleep leve com monitoramento"""
        if not self.sleep_enabled:
            time.sleep(seconds)
            return
        
        self.power_monitor.start_sleep()
        self.sleep_strategy.light_sleep(seconds)
        self.power_monitor.start_operation()
    
    def deep_sleep(self, seconds: int):
        """Deep sleep com monitoramento"""
        if not self.sleep_enabled:
            logger.warning("Deep sleep disabled")
            return
        
        self.power_monitor.start_sleep()
        self.sleep_strategy.deep_sleep(seconds)
        # Após deep sleep, o sistema reinicia
    
    def disable_sleep(self):
        """Desabilitar sleep (para debugging)"""
        self.sleep_enabled = False
        logger.warning("Sleep disabled")
    
    def enable_sleep(self):
        """Habilitar sleep"""
        self.sleep_enabled = True
        logger.info("Sleep enabled")
    
    def get_power_status(self) -> dict:
        """Obter status completo de energia"""
        power_stats = self.power_monitor.get_power_stats()
        
        return {
            **power_stats,
            'sleep_enabled': self.sleep_enabled,
            'wake_reason': self.wake_reason,
            'current_time': time.time()
        }
    
    def optimize_power(self, current_conditions: dict) -> dict:
        """Otimizar configurações de energia baseado nas condições"""
        recommendations = []
        
        # Analisar condições e fazer recomendações
        battery_level = current_conditions.get('battery_level', 100)
        network_activity = current_conditions.get('network_activity', 'low')
        
        if battery_level < 20:
            recommendations.append("BATERIA_BAIXA: Ativar modo economia extrema")
            # Configurações para bateria baixa
            return {
                'light_sleep_interval': 30,
                'deep_sleep_interval': 300,
                'network_scan_interval': 60,
                'recommendations': recommendations
            }
        elif network_activity == 'low':
            recommendations.append("ATIVIDADE_BAIXA: Aumentar intervalos de sleep")
            return {
                'light_sleep_interval': 10,
                'deep_sleep_interval': 180,
                'network_scan_interval': 30,
                'recommendations': recommendations
            }
        else:
            # Configurações normais
            return {
                'light_sleep_interval': 5,
                'deep_sleep_interval': 60,
                'network_scan_interval': 10,
                'recommendations': ["Modo normal de operação"]
            }