# system_health.py
import gc
import machine
import time
from utils import get_logger

logger = get_logger("SystemHealth")

class SystemHealth:
    def __init__(self):
        self.start_time = time.time()
        self.health_check_interval = 60
        self.last_check = 0
        self.health_thresholds = {
            'memory_critical': 4000,
            'memory_warning': 8000,
            'gc_threshold': 20000
        }
        
    def get_memory_info(self):
        """Obter informações de memória"""
        gc.collect()
        total_memory = gc.mem_free() + gc.mem_alloc()
        free_percent = (gc.mem_free() / total_memory) * 100 if total_memory > 0 else 0
        
        return {
            'free': gc.mem_free(),
            'allocated': gc.mem_alloc(),
            'total': total_memory,
            'free_percent': free_percent
        }
    
    def get_uptime(self):
        """Tempo de atividade do sistema"""
        return time.time() - self.start_time
    
    def check_health(self):
        """Verificar saúde do sistema"""
        current_time = time.time()
        
        if current_time - self.last_check < self.health_check_interval:
            return True
            
        self.last_check = current_time
        
        try:
            memory = self.get_memory_info()
            uptime = self.get_uptime()
            
            logger.info(f"Health check: {uptime:.0f}s uptime, {memory['free_percent']:.1f}% memory free")
            
            memory_ok = self._check_memory_health(memory)
            
            if memory['free'] < self.health_thresholds['gc_threshold']:
                gc.collect()
                logger.debug("Garbage collection performed")
                
            return memory_ok
            
        except Exception as e:
            logger.error(f"Health check error: {e}")
            return False
    
    def _check_memory_health(self, memory_info):
        """Verificar saúde da memória"""
        if memory_info['free'] < self.health_thresholds['memory_critical']:
            logger.error("Memória crítica! Sistema pode instabilizar.")
            return False
        elif memory_info['free'] < self.health_thresholds['memory_warning']:
            logger.warning("Memória baixa")
            return True
        else:
            return True
    
    def get_system_status(self):
        """Status completo do sistema"""
        memory = self.get_memory_info()
        
        return {
            'uptime': self.get_uptime(),
            'memory_free': memory['free'],
            'memory_allocated': memory['allocated'],
            'memory_free_percent': memory['free_percent'],
            'last_check': self.last_check,
            'health_status': 'HEALTHY' if self.check_health() else 'WARNING'
        }