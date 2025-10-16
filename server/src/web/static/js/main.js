// Sistema de Notificações
class NotificationSystem {
    static show(message, type = 'info', duration = 5000) {
        const container = document.getElementById('notification-container');
        const notification = document.createElement('div');
        notification.className = `notification ${type}`;
        
        const icons = {
            info: 'fas fa-info-circle',
            success: 'fas fa-check-circle',
            error: 'fas fa-exclamation-circle',
            warning: 'fas fa-exclamation-triangle'
        };
        
        notification.innerHTML = `
            <i class="${icons[type]}" style="color: var(--${type})"></i>
            <span>${message}</span>
            <button class="btn-icon" onclick="this.parentElement.remove()">
                <i class="fas fa-times"></i>
            </button>
        `;
        
        container.appendChild(notification);
        
        if (duration > 0) {
            setTimeout(() => {
                if (notification.parentElement) {
                    notification.remove();
                }
            }, duration);
        }
    }
}

// Sistema de Loading
class LoadingManager {
    static show() {
        const overlay = document.getElementById('loading-overlay');
        if (overlay) {
            overlay.style.display = 'flex';
        }
    }
    
    static hide() {
        const overlay = document.getElementById('loading-overlay');
        if (overlay) {
            overlay.style.display = 'none';
        }
    }
}

// Tratamento de Erros Global
window.addEventListener('error', (event) => {
    console.error('Erro global:', event.error);
    NotificationSystem.show('Ocorreu um erro inesperado', 'error');
});

// Atualiza tabela de classificações recentes com tratamento de erro
async function loadRecentClassifications() {
    try {
        LoadingManager.show();
        const res = await fetch("/api/classifications/recent?limit=20");
        
        if (!res.ok) {
            throw new Error(`HTTP ${res.status}: ${res.statusText}`);
        }
        
        const data = await res.json();
        const tbody = document.querySelector("#recent-table tbody");
        
        if (!tbody) {
            console.warn('Tabela de classificações recentes não encontrada');
            return;
        }
        
        tbody.innerHTML = "";
        
        if (!data || data.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="5" class="text-center text-muted">
                        <i class="fas fa-inbox"></i>
                        Nenhuma classificação encontrada
                    </td>
                </tr>
            `;
            return;
        }
        
        data.forEach((row) => {
            const tr = document.createElement("tr");
            const timestamp = row.timestamp ? new Date(row.timestamp).toLocaleString('pt-BR') : '—';
            const confidence = row.confidence ? (row.confidence * 100).toFixed(1) + '%' : '—';
            const deviceId = row.device_id || "—";
            const systemClass = row.system_class || "Desconhecida";
            
            tr.innerHTML = `
                <td>${timestamp}</td>
                <td>
                    <span class="class-badge">${systemClass}</span>
                </td>
                <td>
                    <div class="confidence-bar">
                        <div class="confidence-fill" style="width: ${row.confidence * 100}%"></div>
                        <span>${confidence}</span>
                    </div>
                </td>
                <td>${deviceId}</td>
                <td>
                    ${row.image_path ? `
                        <a href="/${row.image_path}" target="_blank" class="btn-icon" title="Ver imagem">
                            <i class="fas fa-eye"></i>
                        </a>
                    ` : ''}
                </td>
            `;
            tbody.appendChild(tr);
        });
        
    } catch (error) {
        console.error('Erro ao carregar classificações:', error);
        NotificationSystem.show('Erro ao carregar classificações recentes', 'error');
    } finally {
        LoadingManager.hide();
    }
}

// Gráfico com tratamento de erro
let classificationChart = null;

async function loadClassificationChart() {
    try {
        const res = await fetch("/api/classifications/chart");
        
        if (!res.ok) {
            throw new Error(`HTTP ${res.status}: ${res.statusText}`);
        }
        
        const data = await res.json();
        const ctx = document.getElementById('classification-chart');
        
        if (!ctx) {
            console.warn('Canvas do gráfico não encontrado');
            return;
        }
        
        if (classificationChart) {
            classificationChart.destroy();
        }
        
        const labels = Object.keys(data);
        const values = Object.values(data);
        
        // Cores dinâmicas baseadas nos valores
        const backgroundColors = values.map((_, index) => {
            const hue = (index * 137.5) % 360; // Golden angle para distribuição de cores
            return `hsla(${hue}, 70%, 60%, 0.8)`;
        });
        
        classificationChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Quantidade de Classificações',
                    data: values,
                    backgroundColor: backgroundColors,
                    borderColor: backgroundColors.map(color => color.replace('0.8', '1')),
                    borderWidth: 2,
                    borderRadius: 6,
                    borderSkipped: false,
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        backgroundColor: 'var(--bg-card)',
                        titleColor: 'var(--text-primary)',
                        bodyColor: 'var(--text-primary)',
                        borderColor: 'var(--border-color)',
                        borderWidth: 1,
                        cornerRadius: 8,
                        displayColors: true,
                        callbacks: {
                            label: function(context) {
                                return `Classificações: ${context.parsed.y}`;
                            }
                        }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        grid: {
                            color: 'var(--border-color)',
                            drawBorder: false
                        },
                        ticks: {
                            color: 'var(--text-secondary)'
                        }
                    },
                    x: {
                        grid: {
                            display: false
                        },
                        ticks: {
                            color: 'var(--text-secondary)',
                            maxRotation: 45
                        }
                    }
                },
                animation: {
                    duration: 1000,
                    easing: 'easeOutQuart'
                }
            }
        });
        
    } catch (error) {
        console.error('Erro ao carregar gráfico:', error);
        NotificationSystem.show('Erro ao carregar gráfico de classificações', 'error');
        
        // Mostrar mensagem de erro no canvas
        const ctx = document.getElementById('classification-chart');
        if (ctx) {
            ctx.innerHTML = `
                <div class="text-center text-muted p-4">
                    <i class="fas fa-chart-bar fa-3x mb-2"></i>
                    <p>Erro ao carregar dados do gráfico</p>
                </div>
            `;
        }
    }
}

// Atualização de estatísticas do sistema
async function loadSystemStats() {
    try {
        const res = await fetch("/api/system/stats");
        
        if (!res.ok) {
            throw new Error(`HTTP ${res.status}: ${res.statusText}`);
        }
        
        const data = await res.json();
        
        // Atualizar métricas
        const metrics = {
            'cpu': data.cpu,
            'memory': data.memory,
            'disk': data.disk
        };
        
        Object.entries(metrics).forEach(([key, value]) => {
            const element = document.getElementById(key);
            if (element) {
                element.textContent = value !== undefined ? `${value}%` : '—';
                
                // Adicionar classe baseada no valor
                element.className = '';
                if (value >= 80) {
                    element.classList.add('text-danger');
                } else if (value >= 60) {
                    element.classList.add('text-warning');
                }
            }
        });
        
        // Atualizar status do sistema
        const statusIndicator = document.getElementById('status-indicator');
        const systemStatus = document.getElementById('system-status');
        
        if (statusIndicator && systemStatus) {
            statusIndicator.className = 'status-indicator online';
            systemStatus.textContent = 'Sistema Operacional';
            systemStatus.className = 'text-success';
        }
        
    } catch (error) {
        console.error('Erro ao carregar estatísticas do sistema:', error);
        
        // Atualizar status para offline
        const statusIndicator = document.getElementById('status-indicator');
        const systemStatus = document.getElementById('system-status');
        
        if (statusIndicator && systemStatus) {
            statusIndicator.className = 'status-indicator offline';
            systemStatus.textContent = 'Sistema Offline';
            systemStatus.className = 'text-danger';
        }
        
        NotificationSystem.show('Erro ao conectar com o servidor', 'error');
    }
}

// Atualizar hora atual
function updateCurrentTime() {
    const timeElement = document.getElementById('current-time');
    if (timeElement) {
        const now = new Date();
        timeElement.textContent = now.toLocaleTimeString('pt-BR');
    }
}

// Inicialização
document.addEventListener('DOMContentLoaded', function() {
    // Carregar dados iniciais
    loadRecentClassifications();
    loadClassificationChart();
    loadSystemStats();
    updateCurrentTime();
    
    // Configurar intervalos
    setInterval(loadRecentClassifications, 10000); // 10 segundos
    setInterval(loadSystemStats, 30000); // 30 segundos
    setInterval(updateCurrentTime, 1000); // 1 segundo
    
    // Esconder loading após carregamento completo
    window.addEventListener('load', () => {
        setTimeout(LoadingManager.hide, 500);
    });
});

// Exportar para uso global
window.NotificationSystem = NotificationSystem;
window.LoadingManager = LoadingManager;