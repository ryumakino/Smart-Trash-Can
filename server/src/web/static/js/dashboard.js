// dashboard.js - Dashboard com métricas do sistema (CORRIGIDO)

class DashboardManager {
    static init() {
        this.currentPage = 1;
        this.pageSize = 10;
        
        this.initializeCharts();
        this.loadAllData();
        this.setupEventListeners();
        this.startAutoRefresh();
    }

    static initializeCharts() {
        // Remover gráficos de classificações
        // Manter apenas gráficos do sistema se necessário
    }

    static setupEventListeners() {
        // Remover listeners de paginação de classificações
        
        // Atualização manual
        const refreshBtn = document.querySelector('[onclick="refreshAllData()"]');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => this.loadAllData());
        }
    }

    static startAutoRefresh() {
        // Atualizar métricas a cada 10 segundos
        this.metricsInterval = setInterval(() => {
            this.loadSystemMetrics();
        }, 10000);
        
        // Atualizar gráficos a cada 30 segundos (se houver)
        this.chartsInterval = setInterval(() => {
            // Removido carregamento de gráficos de classificações
        }, 30000);
    }

    static async loadAllData() {
        try {
            LoadingManager.show();
            
            await Promise.all([
                this.loadSystemMetrics(),
                this.loadSystemAlerts() // Manter alertas do sistema
            ]);
            
            this.updateLastUpdateTime();
            NotificationSystem.show('Dados atualizados com sucesso', 'success', 2000);
            
        } catch (error) {
            console.error('Erro ao carregar dados:', error);
            NotificationSystem.show('Erro ao carregar dados do dashboard', 'error');
        } finally {
            LoadingManager.hide();
        }
    }

    static async loadSystemMetrics() {
        try {
            const endpoints = [
                '/api/system/metrics',
                '/api/devices/summary'
            ];

            const responses = await Promise.all(
                endpoints.map(url => fetch(url).then(r => r.ok ? r.json() : Promise.reject(`HTTP ${r.status}`)))
            );

            const [system, devices] = responses;
            this.updateSystemMetrics(system);
            
        } catch (error) {
            console.error('Erro ao carregar métricas do sistema:', error);
        }
    }

    // MANTER APENAS updateSystemMetrics E FUNÇÕES RELACIONADAS AO SISTEMA
    static updateSystemMetrics(system) {
        if (!system) return;

        // === CPU ===
        const cpuUsage = system.cpu?.usage_percent || 0;
        const cpuElement = document.getElementById('cpu-usage');
        const cpuProgress = document.getElementById('cpu-progress');
        const cpuCoresElement = document.getElementById('cpu-cores');
        const cpuFrequencyElement = document.getElementById('cpu-frequency');
        
        if (cpuElement && cpuProgress) {
            cpuElement.textContent = `${cpuUsage.toFixed(1)}%`;
            // Garantir que a barra sempre tenha pelo menos 1% de largura
            const progressWidth = Math.max(cpuUsage, 1);
            cpuProgress.style.width = `${progressWidth}%`;
            cpuProgress.className = `progress-fill ${this.getUsageLevelClass(cpuUsage)}`;
        }
        
        if (cpuCoresElement) {
            const physicalCores = system.cpu?.cores_physical || 0;
            const logicalCores = system.cpu?.cores_logical || 0;
            cpuCoresElement.textContent = `${physicalCores} físicos / ${logicalCores} lógicos`;
        }
        
        if (cpuFrequencyElement && system.cpu?.frequency) {
            const freq = system.cpu.frequency;
            cpuFrequencyElement.textContent = `${(freq.current / 1000).toFixed(1)} GHz`;
        }

        // === Load Average ===
        const loadElement = document.getElementById('load-average');
        if (loadElement && system.cpu?.load_avg) {
            const loadAvg = system.cpu.load_avg;
            loadElement.textContent = `${loadAvg[0].toFixed(2)}, ${loadAvg[1].toFixed(2)}, ${loadAvg[2].toFixed(2)}`;
        }

        // === Estatísticas de CPU ===
        const cpuStatsElement = document.getElementById('cpu-stats');
        if (cpuStatsElement && system.cpu?.stats) {
            const stats = system.cpu.stats;
            cpuStatsElement.innerHTML = `
                <div>CTX Switches: ${(stats.ctx_switches || 0).toLocaleString('pt-BR')}</div>
                <div>Interrupts: ${(stats.interrupts || 0).toLocaleString('pt-BR')}</div>
                <div>Soft IRQs: ${(stats.soft_interrupts || 0).toLocaleString('pt-BR')}</div>
            `;
        }

        // === Context Switches e Interrupts ===
        const contextSwitchesElement = document.getElementById('context-switches');
        const interruptsElement = document.getElementById('interrupts-count');
        
        if (contextSwitchesElement && system.cpu?.stats) {
            contextSwitchesElement.textContent = (system.cpu.stats.ctx_switches || 0).toLocaleString('pt-BR');
        }
        
        if (interruptsElement && system.cpu?.stats) {
            interruptsElement.textContent = (system.cpu.stats.interrupts || 0).toLocaleString('pt-BR');
        }

        // === Uso de CPU por Core ===
        this.updateCpuCoresChart(system.cpu?.usage_per_core || []);

        // === Memória ===
        const memoryUsage = system.memory?.percent || 0;
        const memoryElement = document.getElementById('memory-usage');
        const memoryProgress = document.getElementById('memory-progress');
        const memoryDetailsElement = document.getElementById('memory-details');
        
        if (memoryElement && memoryProgress) {
            memoryElement.textContent = `${memoryUsage.toFixed(1)}%`;
            const progressWidth = Math.max(memoryUsage, 1);
            memoryProgress.style.width = `${progressWidth}%`;
            memoryProgress.className = `progress-fill ${this.getUsageLevelClass(memoryUsage)}`;
        }
        
        if (memoryDetailsElement && system.formatted) {
            memoryDetailsElement.textContent = 
                `${system.formatted.memory_used} / ${system.formatted.memory_total}`;
        }

        // === Memória Swap ===
        const swapElement = document.getElementById('swap-usage');
        const swapProgress = document.getElementById('swap-progress');
        if (swapElement && swapProgress && system.memory) {
            const swapUsage = system.memory.swap_percent || 0;
            swapElement.textContent = `${swapUsage.toFixed(1)}%`;
            const progressWidth = Math.max(swapUsage, 1);
            swapProgress.style.width = `${progressWidth}%`;
            swapProgress.className = `progress-fill ${this.getUsageLevelClass(swapUsage)}`;
        }

        // === Detalhes do Swap ===
        const swapDetailsElement = document.getElementById('swap-details');
        if (swapDetailsElement && system.formatted) {
            swapDetailsElement.textContent = 
                `${system.formatted.swap_used} / ${system.formatted.swap_total}`;
        }

        // === Eficiência de Memória ===
        const memoryEfficiencyElement = document.getElementById('memory-efficiency');
        if (memoryEfficiencyElement && system.performance) {
            const efficiency = system.performance.memory_efficiency || 0;
            memoryEfficiencyElement.textContent = `${efficiency.toFixed(1)}%`;
            memoryEfficiencyElement.className = `metric-value ${this.getUsageLevelClass(efficiency)}`;
        }

        // === Atividade de Swap ===
        const swapActivityElement = document.getElementById('swap-activity');
        if (swapActivityElement && system.performance) {
            const activity = system.performance.swap_activity || 0;
            swapActivityElement.textContent = `${activity.toLocaleString('pt-BR')} páginas/s`;
        }

        // === Memória Detalhada ===
        const memoryDetailedElement = document.getElementById('memory-detailed');
        if (memoryDetailedElement && system.memory && system.formatted) {
            // Verificar se os atributos estão disponíveis antes de exibir
            const hasDetailedInfo = system.memory.active > 0 || system.memory.inactive > 0;
            
            if (hasDetailedInfo) {
                memoryDetailedElement.innerHTML = `
                    <div class="memory-breakdown">
                        ${system.memory.active > 0 ? `
                        <div class="memory-item">
                            <span class="label">Ativa:</span>
                            <span class="value">${system.formatted.memory_active}</span>
                        </div>
                        ` : ''}
                        ${system.memory.inactive > 0 ? `
                        <div class="memory-item">
                            <span class="label">Inativa:</span>
                            <span class="value">${system.formatted.memory_inactive}</span>
                        </div>
                        ` : ''}
                        ${system.memory.buffers > 0 ? `
                        <div class="memory-item">
                            <span class="label">Buffers:</span>
                            <span class="value">${system.formatted.memory_buffers}</span>
                        </div>
                        ` : ''}
                        ${system.memory.cached > 0 ? `
                        <div class="memory-item">
                            <span class="label">Cache:</span>
                            <span class="value">${system.formatted.memory_cached}</span>
                        </div>
                        ` : ''}
                        ${system.memory.shared > 0 ? `
                        <div class="memory-item">
                            <span class="label">Compartilhada:</span>
                            <span class="value">${system.formatted.memory_shared}</span>
                        </div>
                        ` : ''}
                    </div>
                `;
            } else {
                memoryDetailedElement.innerHTML = `
                    <div class="memory-breakdown">
                        <div class="memory-item">
                            <span class="label">Disponível:</span>
                            <span class="value">${system.formatted.memory_available}</span>
                        </div>
                        <div class="memory-item">
                            <span class="label">Livre:</span>
                            <span class="value">${system.formatted.memory_free}</span>
                        </div>
                        <div class="memory-item">
                            <span class="label">Usada:</span>
                            <span class="value">${system.formatted.memory_used}</span>
                        </div>
                    </div>
                `;
            }
        }

        // === Disco ===
        const diskUsage = system.disks?.root?.usage_percent || 0;
        const diskElement = document.getElementById('disk-usage');
        const diskProgress = document.getElementById('disk-progress');
        const diskDetailsElement = document.getElementById('disk-details');
        
        if (diskElement && diskProgress) {
            diskElement.textContent = `${diskUsage.toFixed(1)}%`;
            const progressWidth = Math.max(diskUsage, 1);
            diskProgress.style.width = `${progressWidth}%`;
            diskProgress.className = `progress-fill ${this.getUsageLevelClass(diskUsage)}`;
        }
        
        if (diskDetailsElement && system.formatted) {
            diskDetailsElement.textContent = 
                `${system.formatted.disk_used} / ${system.formatted.disk_total}`;
        }   

        // === Estatísticas de I/O ===
        this.updateIoStats(system.disks?.io_counters || {}, system.network?.io_counters || {});

        // === Discos Múltiplos ===
        this.updateDiskUsage(system.disks?.all_disks || []);

        // === Rede ===
        const netElement = document.getElementById('net-io');
        if (netElement && system.formatted) {
            netElement.textContent = 
                `▲ ${system.formatted.network_sent} | ▼ ${system.formatted.network_recv}`;
        }

        // === Conexões de Rede ===
        const networkConnectionsElement = document.getElementById('network-connections');
        if (networkConnectionsElement && system.network?.connections) {
            const conn = system.network.connections;
            networkConnectionsElement.textContent = 
                `TCP: ${conn.tcp_connections || 0} | UDP: ${conn.udp_connections || 0}`;
        }

        // === Portas em Escuta ===
        const listeningPortsElement = document.getElementById('listening-ports');
        if (listeningPortsElement && system.network?.connections) {
            listeningPortsElement.textContent = system.network.connections.listening_ports || '0';
        }

        // === Processos ===
        const processCount = system.system?.process_count || 0;
        const processElement = document.getElementById('process-count');
        if (processElement) {
            processElement.textContent = processCount.toLocaleString('pt-BR');
        }

        // === Threads do Sistema ===
        const threadsElement = document.getElementById('system-threads');
        if (threadsElement && system.system) {
            threadsElement.textContent = system.system.thread_count?.toLocaleString('pt-BR') || '0';
        }

        // === Usuários Conectados ===
        const usersElement = document.getElementById('users-connected');
        if (usersElement && system.system) {
            usersElement.textContent = system.system.users_connected || 0;
        }

        // === Uptime ===
        const uptimeElement = document.getElementById('uptime');
        if (uptimeElement && system.formatted) {
            uptimeElement.textContent = system.formatted.uptime_human;
        }

        // === Top Processos ===
        this.updateTopProcesses(system.processes?.top_by_cpu || []);

        // === Temperatura CPU - CORRIGIDO ===
        const tempElement = document.getElementById('temperature');
        if (tempElement && system.sensors?.temperatures) {
            const temps = system.sensors.temperatures;
            let cpuTemp = "N/A";
            let foundTemp = false;
            
            // Buscar temperatura da CPU de forma mais robusta
            Object.entries(temps).forEach(([sensor, values]) => {
                if (foundTemp) return;
                
                values.forEach(temp => {
                    if (foundTemp) return;
                    
                    // Verificar se é temperatura da CPU
                    const label = temp.label?.toLowerCase() || '';
                    const sensorName = sensor.toLowerCase();
                    
                    if (label.includes("cpu") || label.includes("core") || label.includes("package") ||
                        sensorName.includes("core") || sensorName.includes("cpu") || sensorName.includes("package")) {
                        
                        if (temp.current && temp.current > 0) {
                            cpuTemp = `${temp.current}°C`;
                            foundTemp = true;
                            
                            // Verificar se está em temperatura crítica
                            if (temp.high && temp.current > temp.high * 0.9) {
                                tempElement.className = 'metric-value critical';
                            } else if (temp.high && temp.current > temp.high * 0.7) {
                                tempElement.className = 'metric-value warning';
                            } else {
                                tempElement.className = 'metric-value';
                            }
                        }
                    }
                });
            });
            
            // Se não encontrou temperatura específica, tentar pegar a primeira disponível
            if (!foundTemp) {
                Object.entries(temps).forEach(([sensor, values]) => {
                    if (foundTemp) return;
                    
                    values.forEach(temp => {
                        if (foundTemp) return;
                        
                        if (temp.current && temp.current > 0) {
                            cpuTemp = `${temp.current}°C`;
                            foundTemp = true;
                            tempElement.className = 'metric-value';
                        }
                    });
                });
            }
            
            tempElement.textContent = cpuTemp;
        } else if (tempElement) {
            tempElement.textContent = "N/A";
            tempElement.className = 'metric-value';
        }

        // === Bateria ===
        const batteryElement = document.getElementById('battery');
        if (batteryElement && system.sensors?.battery) {
            const battery = system.sensors.battery;
            if (battery.percent !== undefined) {
                let batteryText = `${Math.round(battery.percent)}%`;
                let batteryClass = 'metric-value';
                
                if (battery.percent < 20) {
                    batteryClass += ' critical';
                } else if (battery.percent < 50) {
                    batteryClass += ' warning';
                }
                
                if (battery.power_plugged) {
                    batteryText += " carregando";
                } else {
                    batteryText += " ";
                }
                
                batteryElement.textContent = batteryText;
                batteryElement.className = batteryClass;
            } else {
                batteryElement.textContent = "N/A";
            }
        }

        // === Informações de GPU ===
        this.updateGpuInfo(system.gpu || {});

        // === Informações do Sistema ===
        this.updateSystemInfo(system);

        // === Uso de CPU por Core ===
        this.updateCpuCoresChart(system.cpu?.usage_per_core || []);

        // === Discos Múltiplos ===
        this.updateDiskUsage(system.disks?.all_disks || []);
    }

    // MANTER APENAS AS FUNÇÕES DE SISTEMA
    static updateCpuCoresChart(coresUsage) {
        const container = document.getElementById('cpu-cores-chart');
        if (!container) return;

        if (coresUsage.length === 0) {
            container.innerHTML = '<div class="no-data">Nenhum dado de CPU disponível</div>';
            return;
        }

        container.innerHTML = coresUsage.map(core => {
            const usage = core.usage || 0;
            const progressWidth = Math.max(usage, 1); // Mínimo 1% para ser visível
            return `
            <div class="core-item">
                <div class="core-label">Core ${core.core}</div>
                <div class="core-progress">
                    <div class="core-progress-fill" style="width: ${progressWidth}%"></div>
                </div>
                <div class="core-usage">${usage.toFixed(1)}%</div>
            </div>
            `;
        }).join('');
    }

    static updateTopProcesses(processes) {
        const container = document.getElementById('top-processes');
        if (!container) return;

        if (!processes || processes.length === 0) {
            container.innerHTML = `
                <div class="no-data">
                    <i class="fas fa-info-circle"></i>
                    <span>Nenhum processo encontrado</span>
                </div>
            `;
            return;
        }

        container.innerHTML = processes.slice(0, 5).map((proc, index) => {
            const cpuPercent = proc.cpu_percent || 0;
            const memoryPercent = proc.memory_percent || 0;
            const memoryUsage = proc.memory_info ? this.formatBytes(proc.memory_info.rss || 0) : '0 B';
            
            // Limitar nome do processo se for muito longo
            const processName = proc.name && proc.name.length > 20 
                ? proc.name.substring(0, 20) + '...' 
                : proc.name || 'Unknown';
            
            return `
            <div class="process-item ${index % 2 === 0 ? 'even' : 'odd'}">
                <div class="process-rank">${index + 1}</div>
                <div class="process-main">
                    <div class="process-name" title="${proc.name || 'Unknown'}">
                        ${processName}
                    </div>
                    <div class="process-pid">PID: ${proc.pid || 'N/A'}</div>
                </div>
                <div class="process-stats">
                    <div class="process-cpu">
                        <span class="label">CPU:</span>
                        <span class="value ${this.getUsageLevelClass(cpuPercent)}">${cpuPercent.toFixed(1)}%</span>
                    </div>
                    <div class="process-memory">
                        <span class="label">RAM:</span>
                        <span class="value ${this.getUsageLevelClass(memoryPercent)}">${memoryPercent.toFixed(1)}%</span>
                    </div>
                    <div class="process-memory-usage">
                        <small>${memoryUsage}</small>
                    </div>
                </div>
            </div>
            `;
        }).join('');

        // Adicionar estilo se não existir
        if (!document.querySelector('#process-styles')) {
            const style = document.createElement('style');
            style.id = 'process-styles';
            style.textContent = `
                .processes-container {
                    display: flex;
                    flex-direction: column;
                    gap: 8px;
                    margin-top: 10px;
                }
                
                .process-item {
                    display: flex;
                    align-items: center;
                    gap: 12px;
                    padding: 8px 12px;
                    border-radius: 8px;
                    background: var(--bg-secondary);
                    transition: background 0.2s ease;
                }
                
                .process-item:hover {
                    background: var(--bg-hover);
                }
                
                .process-item.even {
                    background: var(--bg-secondary);
                }
                
                .process-item.odd {
                    background: var(--bg-card);
                }
                
                .process-rank {
                    font-weight: bold;
                    color: var(--accent-primary);
                    min-width: 20px;
                    text-align: center;
                }
                
                .process-main {
                    flex: 1;
                    min-width: 0;
                }
                
                .process-name {
                    font-weight: 600;
                    color: var(--text-primary);
                    font-size: 0.9rem;
                    white-space: nowrap;
                    overflow: hidden;
                    text-overflow: ellipsis;
                }
                
                .process-pid {
                    font-size: 0.75rem;
                    color: var(--text-muted);
                }
                
                .process-stats {
                    display: flex;
                    flex-direction: column;
                    align-items: flex-end;
                    gap: 2px;
                    min-width: 80px;
                }
                
                .process-cpu, .process-memory {
                    display: flex;
                    justify-content: space-between;
                    width: 100%;
                    gap: 8px;
                }
                
                .process-cpu .label, .process-memory .label {
                    font-size: 0.75rem;
                    color: var(--text-secondary);
                }
                
                .process-cpu .value, .process-memory .value {
                    font-size: 0.75rem;
                    font-weight: 600;
                }
                
                .process-memory-usage {
                    font-size: 0.7rem;
                    color: var(--text-muted);
                }
                
                .no-data {
                    text-align: center;
                    color: var(--text-muted);
                    padding: 20px;
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    gap: 8px;
                }
                
                .no-data i {
                    font-size: 2rem;
                    opacity: 0.5;
                }
            `;
            document.head.appendChild(style);
        }
    }

    static updateGpuInfo(gpuInfo) {
        const container = document.getElementById('gpu-info');
        if (!container) return;

        if (!gpuInfo.gpu_available || !gpuInfo.gpus || gpuInfo.gpus.length === 0) {
            container.innerHTML = `
                <div class="no-data">
                    <i class="fas fa-video-slash"></i>
                    <span>GPU não detectada</span>
                    <small>ou drivers não disponíveis</small>
                </div>
            `;
            return;
        }

        container.innerHTML = gpuInfo.gpus.map((gpu, index) => {
            const gpuUsage = gpu.load || 0;
            const memoryUsage = gpu.memory_used || 0;
            const memoryTotal = gpu.memory_total || 1;
            const memoryPercent = (memoryUsage / memoryTotal) * 100;
            const temperature = gpu.temperature || 'N/A';
            
            return `
            <div class="gpu-item">
                <div class="gpu-header">
                    <div class="gpu-name">${gpu.name || `GPU ${gpu.id}`}</div>
                    <div class="gpu-usage ${this.getUsageLevelClass(gpuUsage)}">${gpuUsage.toFixed(1)}%</div>
                </div>
                
                <div class="gpu-progress">
                    <div class="progress-bar small">
                        <div class="progress-fill ${this.getUsageLevelClass(gpuUsage)}" 
                            style="width: ${Math.max(gpuUsage, 1)}%"></div>
                    </div>
                </div>
                
                <div class="gpu-stats">
                    <div class="gpu-stat">
                        <span class="label">Memória:</span>
                        <span class="value ${this.getUsageLevelClass(memoryPercent)}">
                            ${memoryPercent.toFixed(1)}%
                        </span>
                    </div>
                    <div class="gpu-stat">
                        <span class="label">Uso:</span>
                        <span class="value">${this.formatBytes(memoryUsage * 1024 * 1024)} / ${this.formatBytes(memoryTotal * 1024 * 1024)}</span>
                    </div>
                    <div class="gpu-stat">
                        <span class="label">Temperatura:</span>
                        <span class="value ${typeof temperature === 'number' && temperature > 80 ? 'critical' : 'normal'}">
                            ${temperature}°C
                        </span>
                    </div>
                </div>
            </div>
            `;
        }).join('');

        // Adicionar estilo se não existir
        if (!document.querySelector('#gpu-styles')) {
            const style = document.createElement('style');
            style.id = 'gpu-styles';
            style.textContent = `
                .gpu-container {
                    display: flex;
                    flex-direction: column;
                    gap: 16px;
                    margin-top: 10px;
                }
                
                .gpu-item {
                    padding: 12px;
                    background: var(--bg-secondary);
                    border-radius: 8px;
                    border-left: 4px solid var(--accent-primary);
                }
                
                .gpu-header {
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    margin-bottom: 8px;
                }
                
                .gpu-name {
                    font-weight: 600;
                    color: var(--text-primary);
                    font-size: 0.9rem;
                    flex: 1;
                }
                
                .gpu-usage {
                    font-weight: bold;
                    font-size: 0.9rem;
                    padding: 2px 8px;
                    border-radius: 4px;
                    background: var(--bg-primary);
                }
                
                .gpu-progress {
                    margin: 8px 0;
                }
                
                .gpu-stats {
                    display: flex;
                    flex-direction: column;
                    gap: 4px;
                }
                
                .gpu-stat {
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    font-size: 0.8rem;
                }
                
                .gpu-stat .label {
                    color: var(--text-secondary);
                }
                
                .gpu-stat .value {
                    font-weight: 600;
                    color: var(--text-primary);
                }
            `;
            document.head.appendChild(style);
        }
    }

    static updateDiskUsage(disks) {
        const container = document.getElementById('disk-usage-detailed');
        if (!container) return;

        if (!disks || disks.length === 0) {
            container.innerHTML = `
                <div class="no-data">
                    <i class="fas fa-hdd"></i>
                    <span>Nenhum disco encontrado</span>
                </div>
            `;
            return;
        }

        // Ordenar discos por ponto de montagem
        const sortedDisks = disks.sort((a, b) => a.mountpoint.localeCompare(b.mountpoint));

        container.innerHTML = sortedDisks.map(disk => {
            const usage = disk.percent || 0;
            const progressWidth = Math.max(usage, 1);
            const freeSpace = disk.free || 0;
            const usedSpace = disk.used || 0;
            const totalSpace = disk.total || 1;
            
            // Determinar ícone baseado no ponto de montagem
            let icon = 'hdd';
            if (disk.mountpoint === '/') icon = 'server';
            else if (disk.mountpoint.includes('home')) icon = 'home';
            else if (disk.mountpoint.includes('boot')) icon = 'download';
            else if (disk.mountpoint.includes('var')) icon = 'database';
            
            return `
            <div class="disk-item">
                <div class="disk-header">
                    <div class="disk-info">
                        <i class="fas fa-${icon}"></i>
                        <div class="disk-mount-point">
                            <div class="mountpoint">${disk.mountpoint}</div>
                            <div class="disk-device">${disk.device || 'Unknown'} (${disk.fstype || 'Unknown'})</div>
                        </div>
                    </div>
                    <div class="disk-usage ${this.getUsageLevelClass(usage)}">${usage.toFixed(1)}%</div>
                </div>
                
                <div class="progress-bar small">
                    <div class="progress-fill ${this.getUsageLevelClass(usage)}" 
                        style="width: ${progressWidth}%"></div>
                </div>
                
                <div class="disk-details">
                    <div class="disk-space">
                        <span class="used">${this.formatBytes(usedSpace)} usado</span>
                        <span class="free">${this.formatBytes(freeSpace)} livre</span>
                        <span class="total">${this.formatBytes(totalSpace)} total</span>
                    </div>
                </div>
            </div>
            `;
        }).join('');

        // Adicionar estilo se não existir
        if (!document.querySelector('#disk-styles')) {
            const style = document.createElement('style');
            style.id = 'disk-styles';
            style.textContent = `
                .disks-container {
                    display: flex;
                    flex-direction: column;
                    gap: 12px;
                    margin-top: 10px;
                }
                
                .disk-item {
                    padding: 12px;
                    background: var(--bg-secondary);
                    border-radius: 8px;
                    border-left: 4px solid var(--accent-primary);
                }
                
                .disk-header {
                    display: flex;
                    justify-content: space-between;
                    align-items: flex-start;
                    margin-bottom: 8px;
                }
                
                .disk-info {
                    display: flex;
                    align-items: flex-start;
                    gap: 10px;
                    flex: 1;
                }
                
                .disk-info i {
                    color: var(--accent-primary);
                    margin-top: 2px;
                }
                
                .disk-mount-point {
                    flex: 1;
                }
                
                .mountpoint {
                    font-weight: 600;
                    color: var(--text-primary);
                    font-size: 0.9rem;
                }
                
                .disk-device {
                    font-size: 0.75rem;
                    color: var(--text-muted);
                    margin-top: 2px;
                }
                
                .disk-usage {
                    font-weight: bold;
                    font-size: 0.9rem;
                    padding: 2px 8px;
                    border-radius: 4px;
                    background: var(--bg-primary);
                }
                
                .disk-details {
                    margin-top: 6px;
                }
                
                .disk-space {
                    display: flex;
                    justify-content: space-between;
                    font-size: 0.75rem;
                    color: var(--text-secondary);
                    flex-wrap: wrap;
                    gap: 8px;
                }
                
                .disk-space .used {
                    color: var(--accent-primary);
                    font-weight: 600;
                }
                
                .disk-space .free {
                    color: var(--text-muted);
                }
                
                .disk-space .total {
                    color: var(--text-primary);
                    font-weight: 500;
                }
            `;
            document.head.appendChild(style);
        }
    }

    static updateIoStats(diskIo, netIo) {
        const diskIoElement = document.getElementById('disk-io-stats');
        const netIoElement = document.getElementById('net-io-detailed');
        
        if (diskIoElement) {
            const readBytes = diskIo.read_bytes || 0;
            const writeBytes = diskIo.write_bytes || 0;
            const readCount = diskIo.read_count || 0;
            const writeCount = diskIo.write_count || 0;
            
            diskIoElement.innerHTML = `
                <div class="io-stat">
                    <i class="fas fa-download"></i>
                    <div class="io-info">
                        <div class="io-label">Leitura</div>
                        <div class="io-value">${this.formatBytes(readBytes)}</div>
                        <div class="io-count">${readCount.toLocaleString('pt-BR')} ops</div>
                    </div>
                </div>
                <div class="io-stat">
                    <i class="fas fa-upload"></i>
                    <div class="io-info">
                        <div class="io-label">Escrita</div>
                        <div class="io-value">${this.formatBytes(writeBytes)}</div>
                        <div class="io-count">${writeCount.toLocaleString('pt-BR')} ops</div>
                    </div>
                </div>
            `;
        }
        
        if (netIoElement) {
            const packetsSent = netIo.packets_sent || 0;
            const packetsRecv = netIo.packets_recv || 0;
            const errorsIn = netIo.errin || 0;
            const errorsOut = netIo.errout || 0;
            const dropsIn = netIo.dropin || 0;
            const dropsOut = netIo.dropout || 0;
            
            netIoElement.innerHTML = `
                <div class="net-stat">
                    <div class="net-label">Pacotes</div>
                    <div class="net-values">
                        <span class="sent">▲ ${packetsSent.toLocaleString('pt-BR')}</span>
                        <span class="recv">▼ ${packetsRecv.toLocaleString('pt-BR')}</span>
                    </div>
                </div>
                <div class="net-stat">
                    <div class="net-label">Erros</div>
                    <div class="net-values">
                        <span class="sent ${errorsOut > 0 ? 'error' : ''}">▲ ${errorsOut}</span>
                        <span class="recv ${errorsIn > 0 ? 'error' : ''}">▼ ${errorsIn}</span>
                    </div>
                </div>
                <div class="net-stat">
                    <div class="net-label">Dropados</div>
                    <div class="net-values">
                        <span class="sent ${dropsOut > 0 ? 'error' : ''}">▲ ${dropsOut}</span>
                        <span class="recv ${dropsIn > 0 ? 'error' : ''}">▼ ${dropsIn}</span>
                    </div>
                </div>
            `;
        }

        // Adicionar estilos para IO stats
        if (!document.querySelector('#io-styles')) {
            const style = document.createElement('style');
            style.id = 'io-styles';
            style.textContent = `
                .io-stats, .net-stats {
                    display: flex;
                    flex-direction: column;
                    gap: 12px;
                    margin-top: 10px;
                }
                
                .io-stat, .net-stat {
                    display: flex;
                    align-items: center;
                    gap: 12px;
                    padding: 8px;
                    background: var(--bg-secondary);
                    border-radius: 6px;
                }
                
                .io-stat i {
                    color: var(--accent-primary);
                    font-size: 1.2rem;
                    width: 24px;
                    text-align: center;
                }
                
                .io-info {
                    flex: 1;
                }
                
                .io-label, .net-label {
                    font-size: 0.8rem;
                    color: var(--text-secondary);
                    font-weight: 500;
                }
                
                .io-value {
                    font-size: 0.9rem;
                    font-weight: 600;
                    color: var(--text-primary);
                }
                
                .io-count {
                    font-size: 0.7rem;
                    color: var(--text-muted);
                }
                
                .net-values {
                    display: flex;
                    gap: 12px;
                    margin-left: auto;
                }
                
                .net-values .sent, .net-values .recv {
                    font-size: 0.8rem;
                    font-weight: 500;
                }
                
                .net-values .sent {
                    color: var(--accent-primary);
                }
                
                .net-values .recv {
                    color: var(--accent-secondary);
                }
                
                .net-values .error {
                    color: #e84393 !important;
                    font-weight: bold;
                }
            `;
            document.head.appendChild(style);
        }
    }

    static formatBytes(bytes) {
        if (bytes === 0) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    static getUsageLevelClass(usage) {
        if (usage >= 90) return 'critical';
        if (usage >= 75) return 'warning';
        return 'normal';
    }

    // REMOVER TODAS AS FUNÇÕES RELACIONADAS A CLASSIFICAÇÕES
    // static updateTrends(), static loadChartsData(), static updateCharts(), 
    // static createClassificationChart(), static updateClassificationChart(),
    // static createConfidenceChart(), static updateConfidenceChart(),
    // static createActivityChart(), static updateActivityChart(),
    // static createDevicesChart(), static updateDevicesChart(),
    // static loadRecentClassifications(), static updateRecentClassificationsTable(),
    // static updatePagination()

    static async loadSystemAlerts() {
        try {
            const response = await fetch('/api/system/alerts');
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }
            
            const alerts = await response.json();
            this.updateAlerts(alerts);
            
        } catch (error) {
            console.error('Erro ao carregar alertas:', error);
        }
    }

    static updateAlerts(alerts) {
        const container = document.getElementById('alerts-container');
        const countElement = document.getElementById('alerts-count');
        
        if (!container || !countElement) return;
        
        countElement.textContent = alerts.length;
        
        if (alerts.length === 0) {
            container.innerHTML = `
                <div class="alert-item info">
                    <i class="fas fa-info-circle"></i>
                    <div class="alert-content">
                        <div class="alert-title">Sistema Operando Normalmente</div>
                        <div class="alert-message">Não há alertas ativos no momento</div>
                    </div>
                </div>
            `;
            return;
        }
        
        container.innerHTML = alerts.map(alert => `
            <div class="alert-item ${alert.level}">
                <i class="fas ${this.getAlertIcon(alert.level)}"></i>
                <div class="alert-content">
                    <div class="alert-title">${alert.title}</div>
                    <div class="alert-message">${alert.message}</div>
                    <div class="alert-time">${new Date(alert.timestamp).toLocaleString('pt-BR')}</div>
                </div>
            </div>
        `).join('');
    }

    static getAlertIcon(level) {
        const icons = {
            'info': 'fa-info-circle',
            'warning': 'fa-exclamation-triangle',
            'error': 'fa-exclamation-circle',
            'critical': 'fa-skull-crossbones'
        };
        return icons[level] || 'fa-info-circle';
    }

    static updateLastUpdateTime() {
        const element = document.getElementById('last-update');
        if (element) {
            element.textContent = `Última atualização: ${new Date().toLocaleString('pt-BR')}`;
        }
    }

    // REMOVER FUNÇÕES DE PAGINAÇÃO
    // static previousPage(), static nextPage(), static updateChartPeriod()

    // Método para limpar intervals quando necessário
    static destroy() {
        if (this.metricsInterval) {
            clearInterval(this.metricsInterval);
        }
        if (this.chartsInterval) {
            clearInterval(this.chartsInterval);
        }
    }
}

// REMOVER FUNÇÕES GLOBAIS RELACIONADAS A CLASSIFICAÇÕES
// function loadRecentClassifications(), function viewImage(), 
// function viewClassificationDetails(), function updateChartPeriod()

// Funções globais mantidas
function refreshAllData() {
    DashboardManager.loadAllData();
}

function openDashboardTab(evt, tabName) {
  // Esconder todas as abas
  document.querySelectorAll('.tab-content').forEach(tab => {
    tab.classList.remove('active');
  });
  
  // Remover active de todos os botões
  document.querySelectorAll('.tab-button').forEach(btn => {
    btn.classList.remove('active');
  });
  
  // Mostrar aba selecionada
  document.getElementById(tabName).classList.add('active');
  evt.currentTarget.classList.add('active');
  
  // Salvar aba selecionada no localStorage
  localStorage.setItem('selectedDashboardTab', tabName);
}

// Inicializar quando o DOM estiver carregado
document.addEventListener('DOMContentLoaded', () => {
    DashboardManager.init();
});

// Limpar recursos quando a página for descarregada
window.addEventListener('beforeunload', () => {
    DashboardManager.destroy();
});