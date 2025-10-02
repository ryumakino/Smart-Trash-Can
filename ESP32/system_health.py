# system_health.py - Monitoramento de saúde do sistema (refatorado)
import gc
import machine
import time
from utils import get_logger

logger = get_logger("SystemHealth")

class SystemHealth:
    def __init__(self):
        self.start_time = time.time()
        self.health_check_interval = 60  # segundos
        self.last_check = 0
        self.health_thresholds = {
            'memory_critical': 4000,    # 4KB
            'memory_warning': 8000,     # 8KB
            'gc_threshold': 20000       # 20KB
        }
        
    def get_memory_info(self):
        """Obter informações de memória de forma padronizada"""
        gc.collect()  # Forçar coleta antes de medir
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
        """Verificar saúde do sistema com limites configuráveis"""
        current_time = time.time()
        
        # Verificar apenas no intervalo configurado
        if current_time - self.last_check < self.health_check_interval:
            return True
            
        self.last_check = current_time
        
        try:
            memory = self.get_memory_info()
            uptime = self.get_uptime()
            
            # Log status
            logger.info(f"Uptime: {uptime:.0f}s, Memory: {memory['free_percent']:.1f}% free")
            
            # Verificar condições de memória
            memory_ok = self._check_memory_health(memory)
            
            # Coleta de lixo se necessário
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
            logger.warning("Memória baixa - realizando coleta de lixo...")
            gc.collect()
            return True
        else:
            return True
    
    def get_system_status(self):
        """Status completo do sistema para relatórios"""
        memory = self.get_memory_info()
        
        return {
            'uptime': self.get_uptime(),
            'memory_free': memory['free'],
            'memory_allocated': memory['allocated'],
            'memory_free_percent': memory['free_percent'],
            'gc_enabled': gc.isenabled(),
            'reset_cause': machine.reset_cause(),
            'health_thresholds': self.health_thresholds
        }
    
    def set_health_thresholds(self, thresholds):
        """Configurar limites de saúde personalizados"""
        self.health_thresholds.update(thresholds)
        logger.info(f"Limites de saúde atualizados: {self.health_thresholds}")