# system_health.py - CORREÇÕES
import time
import gc
from utils import get_logger

logger = get_logger("SystemHealth")

class MetricCalculator:
    @staticmethod
    def calculate_memory_usage():
        try:
            free_mem = gc.mem_free()
            # CORREÇÃO: mem_alloc pode não estar disponível
            try:
                allocated_mem = gc.mem_alloc()
                total_mem = allocated_mem + free_mem
                if total_mem > 0:
                    return (allocated_mem / total_mem) * 100
            except:
                pass
            return 0
        except:
            return 0
    
    @staticmethod
    def calculate_uptime(startup_time):
        return time.time() - startup_time

class HealthEvaluator:
    def __init__(self, warning_threshold=70, critical_threshold=85):
        self.warning_threshold = warning_threshold
        self.critical_threshold = critical_threshold
    
    def evaluate_metric(self, value, name):
        try:
            if value >= self.critical_threshold:
                return "CRITICAL", f"{name} crítico: {value:.1f}%"
            elif value >= self.warning_threshold:
                return "WARNING", f"{name} alto: {value:.1f}%"
            return "HEALTHY", None
        except:
            return "UNKNOWN", f"Erro ao avaliar {name}"

class HealthMonitor:
    def __init__(self, device_manager):
        self.device_manager = device_manager
        self.metric_calc = MetricCalculator()
        self.evaluator = HealthEvaluator()
        self.health_check_count = 0
    
    def perform_health_check(self):
        try:
            self.health_check_count += 1
            
            memory_usage = self.metric_calc.calculate_memory_usage()
            uptime = self.metric_calc.calculate_uptime(
                self.device_manager.system_metrics.startup_time
            )
            
            memory_status, memory_issue = self.evaluator.evaluate_metric(memory_usage, "Memória")
            
            issues = []
            if memory_issue:
                issues.append(memory_issue)
            
            overall_status = "CRITICAL" if "CRITICAL" in memory_status else \
                           "WARNING" if "WARNING" in memory_status else "HEALTHY"
            
            if overall_status == "CRITICAL":
                logger.error(f"Status CRÍTICO: {issues}")
            elif overall_status == "WARNING":
                logger.warning(f"Status AVISO: {issues}")
            else:
                logger.debug("Status SAUDÁVEL")
            
            return {
                'overall_status': overall_status,
                'memory_usage': memory_usage,
                'uptime': uptime,
                'issues': issues,
                'check_count': self.health_check_count,
                'timestamp': time.time()
            }
            
        except Exception as e:
            logger.error(f"Erro na verificação de saúde: {e}")
            return {
                'overall_status': 'ERROR',
                'error': str(e),
                'timestamp': time.time()
            }