// devices.js - Gerenciamento de Dispositivos com MQTT

class DevicesManager {
    static init() {
        this.updateSummary();
        this.setupEventListeners();
        this.startAutoRefresh();
        this.checkMQTTStatus();
    }

    static setupEventListeners() {
        // Event listener para comando personalizado
        document.getElementById('customCommandType')?.addEventListener('change', function(e) {
            const payloadGroup = document.getElementById('customPayloadGroup');
            if (e.target.value === 'custom' || e.target.value === 'MOVE_SERVO' || e.target.value === 'WASTE_TYPE') {
                payloadGroup.style.display = 'block';
            } else {
                payloadGroup.style.display = 'none';
            }
        });

        // Event listener para dispositivo do servo
        document.getElementById('servoControlDevice')?.addEventListener('change', function(e) {
            // Atualizar também o dispositivo do comando personalizado
            document.getElementById('customCommandDevice').value = e.target.value;
        });
    }

    static updateSummary() {
        const totalDevices = document.querySelectorAll('.device-row').length;
        const onlineDevices = document.querySelectorAll('.status-badge.online').length;
        const offlineDevices = totalDevices - onlineDevices;
        
        let totalClassifications = 0;
        document.querySelectorAll('.classification-count').forEach(el => {
            totalClassifications += parseInt(el.textContent) || 0;
        });

        document.getElementById('total-devices').textContent = totalDevices;
        document.getElementById('online-devices').textContent = onlineDevices;
        document.getElementById('offline-devices').textContent = offlineDevices;
        document.getElementById('total-classifications').textContent = totalClassifications;
    }

    static async checkMQTTStatus() {
        try {
            const response = await fetch('/api/mqtt/status');
            if (response.ok) {
                const status = await response.json();
                this.updateMQTTStatusUI(status);
            }
        } catch (error) {
            console.error('Erro ao verificar status MQTT:', error);
            this.updateMQTTStatusUI({ connected: false });
        }
    }

    static updateMQTTStatusUI(status) {
        const statusElement = document.getElementById('mqttStatus');
        const brokerElement = document.getElementById('mqttBroker');
        const messagesElement = document.getElementById('mqttMessages');
        const devicesCountElement = document.getElementById('mqttDevicesCount');

        if (status.connected) {
            statusElement.className = 'status-indicator connected';
            statusElement.innerHTML = '<i class="fas fa-circle"></i> <span>MQTT Conectado</span>';
        } else {
            statusElement.className = 'status-indicator disconnected';
            statusElement.innerHTML = '<i class="fas fa-circle"></i> <span>MQTT Desconectado</span>';
        }

        brokerElement.textContent = status.broker || 'broker.hivemq.com:1883';
        messagesElement.textContent = `${status.message_count || 0} mensagens`;
        devicesCountElement.textContent = `${status.devices_count || 0} dispositivos`;
    }

    static startAutoRefresh() {
        // Atualizar status a cada 10 segundos
        setInterval(() => {
            this.refreshDevicesStatus();
            this.checkMQTTStatus();
        }, 10000);
    }

    static async refreshDevicesStatus() {
        try {
            const response = await fetch('/api/devices');
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }
            
            const devices = await response.json();
            this.updateDevicesUI(devices);
            
        } catch (error) {
            console.error('Erro ao atualizar status:', error);
        }
    }

    static updateDevicesUI(devices) {
        // Para cada dispositivo na resposta, atualizar a UI
        Object.entries(devices).forEach(([deviceId, device]) => {
            const row = document.querySelector(`[data-device-id="${deviceId}"]`);
            
            if (!row) {
                // Se não existe, precisaríamos adicionar à tabela
                // Por simplicidade, vamos recarregar a página
                window.location.reload();
                return;
            }

            // Atualizar status
            const statusBadge = row.querySelector('.status-badge');
            statusBadge.className = `status-badge ${device.status}`;
            statusBadge.innerHTML = `<i class="fas fa-circle"></i> ${device.status === 'online' ? 'Online' : 'Offline'}`;

            // Atualizar último sinal
            const lastSeen = row.querySelector('.last-seen');
            if (device.last_seen) {
                lastSeen.textContent = new Date(device.last_seen).toLocaleString('pt-BR');
                lastSeen.title = new Date(device.last_seen).toLocaleString('pt-BR');
            }

            // Atualizar classificações
            const classificationCount = row.querySelector('.classification-count');
            classificationCount.textContent = device.classifications_count || 0;

            // Atualizar último movimento
            const lastMovement = row.querySelector('.last-movement');
            if (device.last_movement) {
                lastMovement.textContent = new Date(device.last_movement).toLocaleString('pt-BR');
                lastMovement.title = new Date(device.last_movement).toLocaleString('pt-BR');
            } else {
                lastMovement.textContent = '—';
            }

            // Atualizar firmware
            const firmwareVersion = row.querySelector('.firmware-version');
            firmwareVersion.textContent = device.firmware_version || '1.0.0';

            // Atualizar nome se necessário
            const deviceName = row.querySelector('.device-name');
            if (device.device_name && deviceName.textContent !== device.device_name) {
                deviceName.textContent = device.device_name;
            }
        });
        
        this.updateSummary();
    }
}

// Funções MQTT
async function requestDeviceInfo(deviceId) {
    try {
        LoadingManager.show();
        
        const response = await fetch(`/api/devices/${deviceId}/request-info`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            }
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }

        const result = await response.json();
        
        if (result.success) {
            NotificationSystem.show(result.message, 'success');
            
            // Aguardar um pouco e então mostrar informações
            setTimeout(() => {
                showDeviceInfo(deviceId);
            }, 2000);
            
        } else {
            throw new Error(result.error || 'Erro ao solicitar informações');
        }
        
    } catch (error) {
        console.error('Erro ao solicitar informações:', error);
        NotificationSystem.show('Erro ao solicitar informações: ' + error.message, 'error');
    } finally {
        LoadingManager.hide();
    }
}

async function showDeviceInfo(deviceId) {
    try {
        const response = await fetch(`/api/devices/${deviceId}`);
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        
        const device = await response.json();
        
        const modal = document.getElementById('deviceInfoModal');
        const content = document.getElementById('deviceInfoContent');
        
        content.innerHTML = `
            <div class="device-info-details">
                <div class="info-section">
                    <h4>Informações Básicas</h4>
                    <div class="info-grid">
                        <div class="info-item">
                            <label>ID:</label>
                            <span><code>${device.device_id}</code></span>
                        </div>
                        <div class="info-item">
                            <label>Nome:</label>
                            <span>${device.device_name}</span>
                        </div>
                        <div class="info-item">
                            <label>Tipo:</label>
                            <span>${device.device_type}</span>
                        </div>
                        <div class="info-item">
                            <label>Firmware:</label>
                            <span>${device.firmware_version}</span>
                        </div>
                        <div class="info-item">
                            <label>Status:</label>
                            <span class="status-badge ${device.status}">${device.status}</span>
                        </div>
                        <div class="info-item">
                            <label>Último Sinal:</label>
                            <span>${device.last_seen ? new Date(device.last_seen).toLocaleString('pt-BR') : 'Nunca'}</span>
                        </div>
                    </div>
                </div>

                ${device.hardware_info && Object.keys(device.hardware_info).length > 0 ? `
                <div class="info-section">
                    <h4>Hardware</h4>
                    <pre class="config-json">${JSON.stringify(device.hardware_info, null, 2)}</pre>
                </div>
                ` : ''}

                ${device.system_info && Object.keys(device.system_info).length > 0 ? `
                <div class="info-section">
                    <h4>Sistema</h4>
                    <pre class="config-json">${JSON.stringify(device.system_info, null, 2)}</pre>
                </div>
                ` : ''}

                ${device.config && Object.keys(device.config).length > 0 ? `
                <div class="info-section">
                    <h4>Configuração</h4>
                    <pre class="config-json">${JSON.stringify(device.config, null, 2)}</pre>
                </div>
                ` : ''}

                <div class="info-section">
                    <h4>Estatísticas</h4>
                    <div class="info-grid">
                        <div class="info-item">
                            <label>Classificações:</label>
                            <span>${device.classifications_count || 0}</span>
                        </div>
                        <div class="info-item">
                            <label>Último Movimento:</label>
                            <span>${device.last_movement ? new Date(device.last_movement).toLocaleString('pt-BR') : '—'}</span>
                        </div>
                        <div class="info-item">
                            <label>Primeiro Registro:</label>
                            <span>${device.first_seen ? new Date(device.first_seen).toLocaleString('pt-BR') : '—'}</span>
                        </div>
                    </div>
                </div>
            </div>

            <div class="modal-actions">
                <button class="btn" onclick="requestDeviceInfo('${device.device_id}')">
                    <i class="fas fa-sync"></i>
                    Atualizar Informações
                </button>
                <button class="btn btn-outline" onclick="closeModal('deviceInfoModal')">
                    Fechar
                </button>
            </div>
        `;
        
        modal.style.display = 'flex';
        
    } catch (error) {
        console.error('Erro ao carregar informações:', error);
        NotificationSystem.show('Erro ao carregar informações do dispositivo', 'error');
    }
}

async function sendMQTTCommand(deviceId, command, payload = null) {
    try {
        LoadingManager.show();
        
        const requestBody = { command };
        if (payload) {
            requestBody.payload = payload;
        }

        const response = await fetch(`/api/devices/${deviceId}/send-command`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(requestBody)
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }

        const result = await response.json();
        
        if (result.success) {
            NotificationSystem.show(result.message, 'success');
        } else {
            throw new Error(result.error || 'Erro ao enviar comando');
        }
        
    } catch (error) {
        console.error('Erro ao enviar comando MQTT:', error);
        NotificationSystem.show('Erro ao enviar comando: ' + error.message, 'error');
    } finally {
        LoadingManager.hide();
    }
}

async function broadcastMQTTCommand(command, payload = null) {
    if (!confirm(`Enviar comando ${command} para todos os dispositivos?`)) return;

    try {
        LoadingManager.show();
        
        const requestBody = { command };
        if (payload) {
            requestBody.payload = payload;
        }

        const response = await fetch('/api/devices/broadcast', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(requestBody)
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }

        const result = await response.json();
        
        if (result.success) {
            NotificationSystem.show(result.message, 'success');
            
            // Mostrar resultados detalhados
            const successful = result.results.filter(r => r.success).length;
            const failed = result.results.filter(r => !r.success).length;
            
            if (failed > 0) {
                NotificationSystem.show(`${successful} sucesso, ${failed} falhas`, 'warning', 5000);
            }
        } else {
            throw new Error(result.error || 'Erro no broadcast');
        }
        
    } catch (error) {
        console.error('Erro no broadcast MQTT:', error);
        NotificationSystem.show('Erro no broadcast: ' + error.message, 'error');
    } finally {
        LoadingManager.hide();
    }
}

// Funções de controle do servo
function openMQTTControl() {
    const modal = document.getElementById('mqttControlModal');
    modal.style.display = 'flex';
}

function updateServoValue(value) {
    document.getElementById('servoValue').textContent = value + '°';
}

async function moveServoToAngle() {
    const angle = parseInt(document.getElementById('servoAngle').value);
    const deviceId = document.getElementById('servoControlDevice').value;
    
    await sendMQTTCommand(deviceId, 'MOVE_SERVO', { angle });
}

async function moveServoToWasteType(index) {
    const wasteTypes = ['Repouso', 'Plástico', 'Papel', 'Metal', 'Vidro'];
    const deviceId = document.getElementById('servoControlDevice').value;
    
    await sendMQTTCommand(deviceId, 'WASTE_TYPE', { index });
    NotificationSystem.show(`Movendo para: ${wasteTypes[index]}`, 'info');
}

async function sendCustomMQTTCommand() {
    const deviceId = document.getElementById('customCommandDevice').value;
    const commandType = document.getElementById('customCommandType').value;
    const payloadInput = document.getElementById('customCommandPayload').value;
    
    let payload = null;
    if (payloadInput && (commandType === 'custom' || commandType === 'MOVE_SERVO' || commandType === 'WASTE_TYPE')) {
        try {
            payload = JSON.parse(payloadInput);
        } catch (e) {
            NotificationSystem.show('Payload JSON inválido', 'error');
            return;
        }
    }
    
    if (deviceId === 'broadcast') {
        await broadcastMQTTCommand(commandType, payload);
    } else {
        await sendMQTTCommand(deviceId, commandType, payload);
    }
}

function openServoControl(deviceId) {
    document.getElementById('servoControlDevice').value = deviceId;
    document.getElementById('customCommandDevice').value = deviceId;
    document.getElementById('customCommandType').value = 'MOVE_SERVO';
    document.getElementById('customPayloadGroup').style.display = 'block';
    document.getElementById('customCommandPayload').value = '{"angle": 90}';
    openMQTTControl();
}

// Funções auxiliares
async function refreshDevices() {
    try {
        LoadingManager.show();
        window.location.reload();
    } catch (error) {
        console.error('Erro ao atualizar dispositivos:', error);
        NotificationSystem.show('Erro ao atualizar lista de dispositivos', 'error');
    } finally {
        LoadingManager.hide();
    }
}

function closeModal(modalId) {
    const modal = document.getElementById(modalId);
    modal.style.display = 'none';
}

// Fechar modal ao clicar fora
window.addEventListener('click', (event) => {
    const modals = document.querySelectorAll('.modal');
    modals.forEach(modal => {
        if (event.target === modal) {
            modal.style.display = 'none';
        }
    });
});

// Inicializar quando o DOM estiver carregado
document.addEventListener('DOMContentLoaded', () => {
    DevicesManager.init();
});

// Gerenciadores globais
const LoadingManager = {
    show: function() {
        // Implementar overlay de loading se necessário
        document.body.style.cursor = 'wait';
    },
    hide: function() {
        document.body.style.cursor = 'default';
    }
};

const NotificationSystem = {
    show: function(message, type = 'info', duration = 3000) {
        // Criar notificação
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.innerHTML = `
            <div class="notification-content">
                <i class="fas fa-${this.getIcon(type)}"></i>
                <span>${message}</span>
            </div>
        `;
        
        // Estilos básicos
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: ${this.getColor(type)};
            color: white;
            padding: 1rem;
            border-radius: 4px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            z-index: 10000;
            max-width: 400px;
        `;
        
        document.body.appendChild(notification);
        
        // Remover após duração
        setTimeout(() => {
            if (notification.parentNode) {
                notification.parentNode.removeChild(notification);
            }
        }, duration);
    },
    
    getIcon: function(type) {
        const icons = {
            'success': 'check-circle',
            'error': 'exclamation-circle',
            'warning': 'exclamation-triangle',
            'info': 'info-circle'
        };
        return icons[type] || 'info-circle';
    },
    
    getColor: function(type) {
        const colors = {
            'success': '#28a745',
            'error': '#dc3545',
            'warning': '#ffc107',
            'info': '#17a2b8'
        };
        return colors[type] || '#17a2b8';
    }
};