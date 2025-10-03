// -------------------------------
// Charts Functions
// -------------------------------

let charts = {};

export function initializeCharts() {
    charts.classDistribution = new Chart(
        document.getElementById('classDistributionChart'),
        getClassDistributionConfig()
    );
    
    charts.hourlyActivity = new Chart(
        document.getElementById('hourlyActivityChart'),
        getHourlyActivityConfig()
    );
    
    charts.confidenceDistribution = new Chart(
        document.getElementById('confidenceDistributionChart'),
        getConfidenceDistributionConfig()
    );
}

export function updateCharts(stats, classifications) {
    // Distribuição por classe
    if (stats.by_class && charts.classDistribution) {
        charts.classDistribution.data.labels = stats.by_class.map(item => item.class);
        charts.classDistribution.data.datasets[0].data = stats.by_class.map(item => item.count);
        charts.classDistribution.update();
    }

    // Atividade horária
    if (stats.hourly_data && charts.hourlyActivity) {
        const hourlyData = stats.hourly_data.slice().reverse();
        charts.hourlyActivity.data.labels = hourlyData.map(item => 
            new Date(item.hour).toLocaleTimeString('pt-BR', { hour: '2-digit' })
        );
        charts.hourlyActivity.data.datasets[0].data = hourlyData.map(item => item.count);
        charts.hourlyActivity.update();
    }

    // Distribuição de confiança
    if (classifications.length && charts.confidenceDistribution) {
        const confidenceRanges = [0, 0, 0, 0, 0];
        classifications.forEach(item => {
            const confidence = item.confidence;
            if (confidence <= 0.2) confidenceRanges[0]++;
            else if (confidence <= 0.4) confidenceRanges[1]++;
            else if (confidence <= 0.6) confidenceRanges[2]++;
            else if (confidence <= 0.8) confidenceRanges[3]++;
            else confidenceRanges[4]++;
        });
        charts.confidenceDistribution.data.datasets[0].data = confidenceRanges;
        charts.confidenceDistribution.update();
    }
}

// -------------------------------
// Configs
// -------------------------------
function getClassDistributionConfig() {
    return {
        type: 'doughnut',
        data: { labels: [], datasets: [{ data: [], backgroundColor: ['#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF', '#FF9F40'] }] },
        options: { responsive: true, maintainAspectRatio: false }
    };
}

function getHourlyActivityConfig() {
    return {
        type: 'line',
        data: { labels: [], datasets: [{ label: 'Classificações por Hora', data: [], borderColor: '#36A2EB', fill: true, tension: 0.4 }] },
        options: { responsive: true, maintainAspectRatio: false }
    };
}

function getConfidenceDistributionConfig() {
    return {
        type: 'bar',
        data: { labels: ['0-20%', '20-40%', '40-60%', '60-80%', '80-100%'], datasets: [{ data: [0,0,0,0,0], backgroundColor: ['#e74c3c','#f39c12','#f1c40f','#2ecc71','#27ae60'] }] },
        options: { responsive: true, maintainAspectRatio: false }
    };
}
