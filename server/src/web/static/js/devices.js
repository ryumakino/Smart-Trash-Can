// static/js/devices.js - Gerenciamento de dispositivos ESP32

export class ESP32DeviceManager {
    constructor() {
        this.devices = {};
        this.autoRefresh = true;
        this.refreshInterval = null;
    }

    async loadDevices() {
        try {
            const response = await fetch('/api/esp32_devices');
            const data = await response.json();
            
            if (data.error) {
                console.error('Erro ao carregar dispositivos:', data.error);
                return;
            }
            
            this.devices = data.devices;
            this.updateDevicesUI();
            this.updateServerStats(data.server_stats);
            
        } catch (error) {
            console.error('Erro ao carregar dispositivos:', error);
        }
    }

    updateDevicesUI() {
        const container = document.getElementById('esp32DevicesContainer');
        if (!container) return;

        const devices = Object.values(this.devices);
        
        if (devices.length === 0) {
            container.innerHTML = `
                <div class="no-devices">
                    <p>📡 Nenhum dispositivo ESP32 conectado</p>
                    <button class="btn" onclick="deviceManager.sendDiscovery()">
                        🔍 Procurar Dispositivos
                    </button>
                </div>
            `;
            return;
        }

        container.innerHTML = devices.map(device => this.createDeviceCard(device)).join('');
    }

    createDeviceCard(device) {
        const lastSeen = this.formatLastSeen(device.last_seen);
        const statusClass = this.getStatusClass(device.last_seen);
        
        return `
            <div class="device-card ${statusClass}">
                <div class="device-header">
                    <h3>${device.device_name || 'ESP32'}</h3>
                    <span class="device-status ${statusClass}"></span>
                </div>
                
                <div class="device-info">
                    <div class="info-row">
                        <label>ID:</label>
                        <span class="device-id">${device.device_id}</span>
                    </div>
                    <div class="info-row">
                        <label>IP:</label>
                        <span>${device.ip_address}</span>
                    </div>
                    <div class="info-row">
                        <label>Rede:</label>
                        <span class="network-badge ${device.network_mode?.toLowerCase()}">
                            ${device.network_mode || 'UNKNOWN'}
                        </span>
                    </div>
                    <div class="info-row">
                        <label>Última vez:</label>
                        <span>${lastSeen}</span>
                    </div>
                </div>

                <div class="device-actions">
                    <button class="btn btn-small" onclick="deviceManager.sendCommand('${device.device_id}', 'SYSTEM_COMMAND', {command: 'STATUS'})">
                        📊 Status
                    </button>
                    <button class="btn btn-small btn-success" onclick="deviceManager.showWasteMenu('${device.device_id}')">
                        🗑️ Enviar Resíduo
                    </button>
                    <button class="btn btn-small btn-warning" onclick="deviceManager.showConfigModal('${device.device_id}')">
                        ⚙️ Configurar
                    </button>
                </div>
            </div>
        `;
    }

    updateServerStats(stats) {
        const statsElem = document.getElementById('esp32ServerStats');
        if (!statsElem) return;

        statsElem.innerHTML = `
            <div class="server-stats">
                <div class="stat">
                    <span class="stat-value">${stats.esp32_connected || 0}</span>
                    <span class="stat-label">Dispositivos Conectados</span>
                </div>
                <div class="stat">
                    <span class="stat-value">${stats.messages_processed || 0}</span>
                    <span class="stat-label">Mensagens Processadas</span>
                </div>
                <div class="stat">
                    <span class="stat-value">${this.formatUptime(stats.uptime)}</span>
                    <span class="stat-label">Uptime Servidor</span>
                </div>
            </div>
        `;
    }

    getStatusClass(lastSeen) {
        const now = Date.now() / 1000;
        const diff = now - lastSeen;
        
        if (diff < 60) return 'status-online';
        if (diff < 300) return 'status-warning';
        return 'status-offline';
    }

    formatLastSeen(timestamp) {
        const now = Date.now() / 1000;
        const diff = now - timestamp;
        
        if (diff < 60) return 'Agora mesmo';
        if (diff < 3600) return `${Math.floor(diff / 60)} min atrás`;
        if (diff < 86400) return `${Math.floor(diff / 3600)} h atrás`;
        return `${Math.floor(diff / 86400)} dias atrás`;
    }

    formatUptime(seconds) {
        if (!seconds) return '0s';
        
        const hours = Math.floor(seconds / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);
        
        if (hours > 0) return `${hours}h ${minutes}m`;
        return `${minutes}m`;
    }

    async sendCommand(deviceId, commandType, commandData = {}) {
        try {
            const response = await fetch('/api/esp32/send_command', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    device_id: deviceId,
                    command_type: commandType,
                    command_data: commandData
                })
            });

            const result = await response.json();
            
            if (result.success) {
                this.showNotification(result.message, 'success');
                // Recarregar dispositivos após comando
                setTimeout(() => this.loadDevices(), 1000);
            } else {
                this.showNotification(result.error, 'error');
            }
            
        } catch (error) {
            console.error('Erro ao enviar comando:', error);
            this.showNotification('Erro ao enviar comando', 'error');
        }
    }

    async sendDiscovery() {
        await this.sendCommand('broadcast', 'DISCOVERY');
    }

    showWasteMenu(deviceId) {
        const wasteTypes = [
            { index: 0, name: "🔄 Repouso" },
            { index: 1, name: "🧪 Plástico" },
            { index: 2, name: "📄 Papel" },
            { index: 3, name: "🔩 Metal" },
            { index: 4, name: "🥃 Vidro" }
        ];

        const menu = wasteTypes.map(waste => `
            <button class="waste-btn" onclick="deviceManager.sendCommand('${deviceId}', 'WASTE_COMMAND', {waste_index: ${waste.index}, waste_name: '${waste.name}'})">
                ${waste.name}
            </button>
        `).join('');

        const modal = document.createElement('div');
        modal.className = 'modal';
        modal.innerHTML = `
            <div class="modal-content">
                <h3>🗑️ Selecionar Tipo de Resíduo</h3>
                <div class="waste-menu">
                    ${menu}
                </div>
                <button class="btn" onclick="this.closest('.modal').remove()">Cancelar</button>
            </div>
        `;

        document.body.appendChild(modal);
    }

    showConfigModal(deviceId) {
        const modal = document.createElement('div');
        modal.className = 'modal';
        modal.innerHTML = `
            <div class="modal-content">
                <h3>⚙️ Configurar ${deviceId}</h3>
                <form id="configForm">
                    <div class="form-group">
                        <label>Nome do Dispositivo:</label>
                        <input type="text" name="device_name" placeholder="Novo nome...">
                    </div>
                    <div class="form-group">
                        <label>Intervalo Heartbeat (segundos):</label>
                        <input type="number" name="heartbeat_interval" value="60" min="10" max="300">
                    </div>
                    <div class="form-group">
                        <label>Reinicializar após config:</label>
                        <input type="checkbox" name="restart_required">
                    </div>
                    <div class="form-actions">
                        <button type="button" class="btn" onclick="this.closest('.modal').remove()">Cancelar</button>
                        <button type="submit" class="btn btn-success">Salvar Configuração</button>
                    </div>
                </form>
            </div>
        `;

        const form = modal.querySelector('#configForm');
        form.onsubmit = (e) => {
            e.preventDefault();
            this.saveConfig(deviceId, new FormData(form));
            modal.remove();
        };

        document.body.appendChild(modal);
    }

    async saveConfig(deviceId, formData) {
        const config = {
            system: {
                DEVICE_NAME: formData.get('device_name') || undefined
            },
            communication: {
                HEARTBEAT_INTERVAL: parseInt(formData.get('heartbeat_interval')) || undefined
            }
        };

        // Remove undefined values
        Object.keys(config).forEach(key => {
            if (!config[key] || Object.keys(config[key]).length === 0) {
                delete config[key];
            }
        });

        try {
            const response = await fetch('/api/esp32/setup_config', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    device_id: deviceId,
                    config: config,
                    restart_required: formData.get('restart_required') === 'on'
                })
            });

            const result = await response.json();
            
            if (result.success) {
                this.showNotification('Configuração enviada com sucesso!', 'success');
                this.loadDevices();
            } else {
                this.showNotification(result.error, 'error');
            }
            
        } catch (error) {
            console.error('Erro ao salvar configuração:', error);
            this.showNotification('Erro ao salvar configuração', 'error');
        }
    }

    showNotification(message, type = 'info') {
        // Reutilize a função de notificação existente ou implemente uma simples
        const notification = document.createElement('div');
        notification.className = `notification ${type}`;
        notification.textContent = message;
        notification.style.cssText = `
            position: fixed; top: 20px; right: 20px;
            padding: 15px 20px; border-radius: 8px; color: white;
            z-index: 10000; background: ${type === 'success' ? '#27ae60' : type === 'error' ? '#e74c3c' : '#3498db'};
        `;
        
        document.body.appendChild(notification);
        setTimeout(() => notification.remove(), 4000);
    }

    startAutoRefresh() {
        if (this.autoRefresh) {
            this.refreshInterval = setInterval(() => this.loadDevices(), 5000);
        }
    }

    stopAutoRefresh() {
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
            this.refreshInterval = null;
        }
    }

    toggleAutoRefresh() {
        this.autoRefresh = !this.autoRefresh;
        if (this.autoRefresh) {
            this.startAutoRefresh();
        } else {
            this.stopAutoRefresh();
        }
    }
}

// Instância global
window.deviceManager = new ESP32DeviceManager();