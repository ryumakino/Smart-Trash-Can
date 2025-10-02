// -------------------------------
// UI Functions
// -------------------------------

export function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.innerHTML = message;
    notification.style.cssText = `
        position: fixed; top: 20px; right: 20px;
        padding: 15px 20px; border-radius: 8px;
        color: white; font-weight: bold; z-index: 10000;
        max-width: 300px; box-shadow: 0 5px 15px rgba(0,0,0,0.3);
        animation: slideIn 0.3s ease;
    `;
    notification.style.background = type === 'success' ? '#27ae60' : type === 'error' ? '#e74c3c' : '#3498db';
    document.body.appendChild(notification);

    setTimeout(() => {
        notification.style.animation = 'slideOut 0.3s ease';
        setTimeout(() => notification.remove(), 300);
    }, 4000);
}

export function showLoading() { console.log("Carregando..."); }
export function hideLoading() { console.log("Carregado!"); }
export function showError(msg) { showNotification(msg, "error"); }

export function switchTab(tabName) {
    document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
    document.getElementById(tabName).classList.add('active');
    event.target.classList.add('active');
}

export function closeModal() {
    document.getElementById('systemInfoModal').style.display = 'none';
}
export function showSystemInfo() {
    document.getElementById('systemInfoModal').style.display = 'block';
}
