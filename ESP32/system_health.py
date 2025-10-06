# system_health.py
import time
import machine
import gc
from utils import get_logger

logger = get_logger("SystemHealth")

class HealthMetric:
    """SRP: Representar uma métrica de saúde"""
    
    def __init__(self, name, value, threshold_warning, threshold_critical, unit=""):
        self.name = name
        self.value = value
        self.threshold_warning = threshold_warning
        self.threshold_critical = threshold_critical
        self.unit = unit
    
    def get_status(self) -> str:
        """Obter status da métrica"""
        if self.value >= self.threshold_critical:
            return "CRITICAL"
        elif self.value >= self.threshold_warning:
            return "WARNING"
        else:
            return "HEALTHY"
    
    def to_dict(self):
        """Converter para dicionário"""
        return {
            'name': self.name,
            'value': self.value,
            'unit': self.unit,
            'status': self.get_status(),
            'threshold_warning': self.threshold_warning,
            'threshold_critical': self.threshold_critical
        }

class HealthChecker:
    """SRP: Verificar saúde de componentes específicos"""
    
    def __init__(self, device_manager):
        self.device_manager = device_manager
    
    def check_memory_health(self) -> HealthMetric:
        """Verificar saúde da memória"""
        free_mem = gc.mem_free()
        total_mem = gc.mem_alloc() + free_mem
        memory_percent = (gc.mem_alloc() / total_mem) * 100 if total_mem > 0 else 0
        
        return HealthMetric(
            name="memory_usage",
            value=memory_percent,
            threshold_warning=70,
            threshold_critical=85,
            unit="%"
        )
    
    def check_uptime_health(self) -> HealthMetric:
        """Verificar saúde do tempo de atividade"""
        system_info = self.device_manager.get_system_info()
        uptime = system_info.get('uptime', 0)
        
        return HealthMetric(
            name="uptime",
            value=uptime,
            threshold_warning=86400,  # 24 horas - warning
            threshold_critical=604800, # 7 dias - critical (para prevent reset)
            unit="seconds"
        )
    
    def check_network_health(self) -> HealthMetric:
        """Verificar saúde da rede"""
        network_status = self.device_manager.get_network_status()
        connected = network_status.get('connected', False)
        
        return HealthMetric(
            name="network",
            value=0 if connected else 100,  # 0 = saudável, 100 = crítico
            threshold_warning=50,
            threshold_critical=80,
            unit="status"  # 0=connected, 100=disconnected
        )

class HealthAggregator:
    """SRP: Agregar resultados de saúde"""
    
    def __init__(self):
        self.metrics = []
        self.overall_status = "HEALTHY"
    
    def add_metric(self, metric: HealthMetric):
        """Adicionar métrica"""
        self.metrics.append(metric)
        self._update_overall_status()
    
    def _update_overall_status(self):
        """Atualizar status geral baseado nas métricas"""
        status_priority = {
            "CRITICAL": 3,
            "WARNING": 2, 
            "HEALTHY": 1
        }
        
        highest_priority = 1
        for metric in self.metrics:
            priority = status_priority.get(metric.get_status(), 1)
            if priority > highest_priority:
                highest_priority = priority
        
        # Mapear prioridade de volta para status
        status_map = {1: "HEALTHY", 2: "WARNING", 3: "CRITICAL"}
        self.overall_status = status_map[highest_priority]
    
    def get_health_report(self) -> dict:
        """Gerar relatório completo de saúde"""
        critical_issues = []
        warning_issues = []
        
        for metric in self.metrics:
            status = metric.get_status()
            if status == "CRITICAL":
                critical_issues.append(f"{metric.name}: {metric.value}{metric.unit}")
            elif status == "WARNING":
                warning_issues.append(f"{metric.name}: {metric.value}{metric.unit}")
        
        return {
            'overall_status': self.overall_status,
            'metrics': [metric.to_dict() for metric in self.metrics],
            'critical_issues': critical_issues,
            'warning_issues': warning_issues,
            'timestamp': time.time()
        }

class SystemHealth:
    """Facade: Sistema de saúde principal"""
    
    def __init__(self, device_manager):
        self.device_manager = device_manager
        self.health_checker = HealthChecker(device_manager)
        self.health_aggregator = HealthAggregator()
        
        self.start_time = time.time()
        self.health_check_count = 0
        self.last_health_check = 0
    
    def perform_health_check(self) -> dict:
        """Executar verificação completa de saúde"""
        try:
            # Coletar métricas
            memory_metric = self.health_checker.check_memory_health()
            uptime_metric = self.health_checker.check_uptime_health()
            network_metric = self.health_checker.check_network_health()
            
            # Adicionar ao agregador
            self.health_aggregator.add_metric(memory_metric)
            self.health_aggregator.add_metric(uptime_metric)
            self.health_aggregator.add_metric(network_metric)
            
            # Atualizar estatísticas
            self.health_check_count += 1
            self.last_health_check = time.time()
            
            # Gerar relatório
            report = self.health_aggregator.get_health_report()
            
            # Log baseado no status
            if report['overall_status'] == 'CRITICAL':
                logger.error(f"Status CRÍTICO: {report['critical_issues']}")
            elif report['overall_status'] == 'WARNING':
                logger.warning(f"Status AVISO: {report['warning_issues']}")
            else:
                logger.debug("Status SAUDÁVEL")
            
            return report
            
        except Exception as e:
            logger.error(f"Erro na verificação de saúde: {e}")
            return {
                'overall_status': 'ERROR',
                'error': str(e),
                'timestamp': time.time()
            }
    
    def get_system_status(self) -> dict:
        """Obter status completo do sistema"""
        health_report = self.perform_health_check()
        system_info = self.device_manager.get_system_info()
        
        return {
            **system_info,
            'health': health_report,
            'health_check_count': self.health_check_count,
            'last_health_check': self.last_health_check,
            'startup_time': self.start_time
        }
    
    def is_healthy(self) -> bool:
        """Verificar se o sistema está saudável"""
        report = self.perform_health_check()
        return report['overall_status'] in ['HEALTHY', 'WARNING']
    
    def get_health_stats(self) -> dict:
        """Obter estatísticas de saúde"""
        return {
            'total_checks': self.health_check_count,
            'last_check_time': self.last_health_check,
            'system_uptime': time.time() - self.start_time,
            'time_since_last_check': time.time() - self.last_health_check
        }