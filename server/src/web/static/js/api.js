// -------------------------------
// API Functions
// -------------------------------

export async function loadData(updateSystemStatus, updateClassificationsList, updateCharts, showLoading, hideLoading, showError) {
    try {
        showLoading();
        const [stats, classifications, status, systemInfo] = await Promise.all([
            fetch('/api/statistics').then(r => r.json()),
            fetch('/api/classifications').then(r => r.json()),
            fetch('/api/system/status').then(r => r.json()),
            fetch('/api/system_info').then(r => r.json())
        ]);

        updateSystemStatus(status, stats, systemInfo);
        updateClassificationsList(classifications);
        updateCharts(stats, classifications);

        hideLoading();
    } catch (error) {
        console.error('Erro ao carregar dados:', error);
        showError('Erro ao conectar com o servidor');
    }
}

export async function classifyNow(showNotification, loadData) {
    const button = event.target;
    const originalText = button.innerHTML;

    try {
        button.innerHTML = '⏳ Processando...';
        button.disabled = true;

        const response = await fetch('/api/classify_now');
        const result = await response.json();

        if (result.success) {
            showNotification(
                `✅ Classificação realizada!<br>
                <strong>${result.result.system_class}</strong> 
                (${(result.result.confidence * 100).toFixed(1)}% confiança)`,
                'success'
            );
            loadData(); // Recarregar dados
        } else {
            showNotification(
                `❌ Falha na classificação: ${result.error}`,
                'error'
            );
        }
    } catch (error) {
        console.error('Erro na classificação:', error);
        showNotification('❌ Erro de conexão com o servidor', 'error');
    } finally {
        button.innerHTML = originalText;
        button.disabled = false;
    }
}
