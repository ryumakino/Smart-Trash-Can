import { loadData, classifyNow } from "./api.js";
import { initializeCharts, updateCharts } from "./charts.js";
import { showNotification, showLoading, hideLoading, showError, showSystemInfo, closeModal } from "./ui.js";
import { ESP32DeviceManager } from './devices.js';

let isAutoRefresh = true;
let autoRefreshInterval = null;

// -------------------------------
// Inicialização
// -------------------------------
document.addEventListener('DOMContentLoaded', () => {
    initializeCharts();
    refresh();
    startAutoRefresh();

    // Inicializar gerenciador de dispositivos
    window.deviceManager = new ESP32DeviceManager();
    deviceManager.loadDevices();
    deviceManager.startAutoRefresh();

    document.getElementById("autoRefreshBtn").addEventListener("click", toggleAutoRefresh);
    window.showSystemInfo = showSystemInfo;
    window.closeModal = closeModal;
    window.classifyNow = () => classifyNow(showNotification, () => refresh());
});

// -------------------------------
// Funções
// -------------------------------
function refresh() {
    loadData(updateSystemStatus, updateClassificationsList, updateCharts, showLoading, hideLoading, showError);
}

function startAutoRefresh() {
    if (isAutoRefresh) {
        autoRefreshInterval = setInterval(refresh, 10000);
    }
}

function stopAutoRefresh() {
    if (autoRefreshInterval) {
        clearInterval(autoRefreshInterval);
        autoRefreshInterval = null;
    }
}

function toggleAutoRefresh() {
    isAutoRefresh = !isAutoRefresh;
    const btn = document.getElementById("autoRefreshBtn");
    btn.innerHTML = isAutoRefresh ? "🔄 Auto-Atualizar: Ligado" : "⏸️ Auto-Atualizar: Pausado";
    if (isAutoRefresh) startAutoRefresh(); else stopAutoRefresh();
}

// -------------------------------
// Update UI
// -------------------------------
function updateSystemStatus(status, stats, systemInfo) {
    // exemplo simplificado: apenas conexão
    const statusElem = document.getElementById("connectionStatus");
    let statusText = status.status === "operational" ? "✅ Operacional" : status.status === "degraded" ? "⚠️ Degradado" : "❌ Offline";
    statusElem.innerHTML = `<span>${statusText}</span>`;
}

function updateClassificationsList(classifications) {
    const container = document.getElementById("classificationsList");
    if (!classifications.length) {
        container.innerHTML = "<p style='text-align:center; color:#7f8c8d;'>Nenhuma classificação realizada ainda.</p>";
        return;
    }
    container.innerHTML = classifications.map(item => `
        <div class="classification">
            <div>
                <strong>${item.system_class}</strong><br>
                <small>${new Date(item.timestamp).toLocaleString()}</small>
            </div>
            <span class="confidence-badge">${(item.confidence * 100).toFixed(1)}%</span>
        </div>
    `).join("");
}
