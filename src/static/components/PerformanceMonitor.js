/**
 * Composant de monitoring des performances
 */
class PerformanceMonitor {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
        this.metrics = null;
        this.history = null;
        this.recommendations = null;
        this.updateInterval = null;
        this.charts = {};
        
        this.init();
    }

    async init() {
        await this.loadData();
        this.render();
        this.attachEventListeners();
        this.startAutoUpdate();
    }

    async loadData() {
        try {
            // Charger les métriques actuelles
            const metricsResponse = await fetch('/api/performance/metrics');
            const metricsResult = await metricsResponse.json();
            if (metricsResult.success) {
                this.metrics = metricsResult.metrics;
            }

            // Charger l'historique
            const historyResponse = await fetch('/api/performance/history?duration=60');
            const historyResult = await historyResponse.json();
            if (historyResult.success) {
                this.history = historyResult.history;
            }

            // Charger les recommandations
            const recommendationsResponse = await fetch('/api/performance/recommendations');
            const recommendationsResult = await recommendationsResponse.json();
            if (recommendationsResult.success) {
                this.recommendations = recommendationsResult.recommendations;
            }
        } catch (error) {
            console.error('Erreur lors du chargement des données:', error);
        }
    }

    render() {
        this.container.innerHTML = `
            <div class="performance-monitor">
                <div class="performance-header">
                    <h2>Monitoring des Performances</h2>
                    <div class="performance-controls">
                        <button id="refreshBtn" class="btn btn-outline-primary">
                            <i class="fas fa-sync"></i>
                            Actualiser
                        </button>
                        <button id="exportBtn" class="btn btn-outline-secondary">
                            <i class="fas fa-download"></i>
                            Exporter
                        </button>
                        <div class="auto-update-toggle">
                            <label class="switch">
                                <input type="checkbox" id="autoUpdateToggle" checked>
                                <span class="slider"></span>
                            </label>
                            <span>Mise à jour auto</span>
                        </div>
                    </div>
                </div>

                <div class="performance-content">
                    ${this.renderHealthStatus()}
                    ${this.renderSystemMetrics()}
                    ${this.renderApplicationMetrics()}
                    ${this.renderPerformanceCharts()}
                    ${this.renderRecommendations()}
                    ${this.renderOptimizationRules()}
                </div>
            </div>
        `;

        // Initialiser les graphiques après le rendu
        setTimeout(() => {
            this.initializeCharts();
        }, 100);
    }

    renderHealthStatus() {
        if (!this.metrics) {
            return '<div class="performance-section loading">Chargement...</div>';
        }

        const cpuStatus = this.getStatusClass(this.metrics.system.cpu_usage_current, 70, 85);
        const memoryStatus = this.getStatusClass(this.metrics.system.memory_usage_current, 70, 85);
        const connectionsRatio = this.metrics.application.active_connections / this.metrics.application.max_connections;
        const connectionStatus = this.getStatusClass(connectionsRatio * 100, 70, 85);

        return `
            <div class="performance-section">
                <h3>État de Santé du Système</h3>
                <div class="health-grid">
                    <div class="health-item ${cpuStatus}">
                        <div class="health-icon">
                            <i class="fas fa-microchip"></i>
                        </div>
                        <div class="health-info">
                            <div class="health-label">CPU</div>
                            <div class="health-value">${this.metrics.system.cpu_usage_current.toFixed(1)}%</div>
                        </div>
                    </div>
                    <div class="health-item ${memoryStatus}">
                        <div class="health-icon">
                            <i class="fas fa-memory"></i>
                        </div>
                        <div class="health-info">
                            <div class="health-label">Mémoire</div>
                            <div class="health-value">${this.metrics.system.memory_usage_current.toFixed(1)}%</div>
                        </div>
                    </div>
                    <div class="health-item ${connectionStatus}">
                        <div class="health-icon">
                            <i class="fas fa-network-wired"></i>
                        </div>
                        <div class="health-info">
                            <div class="health-label">Connexions</div>
                            <div class="health-value">${this.metrics.application.active_connections}/${this.metrics.application.max_connections}</div>
                        </div>
                    </div>
                    <div class="health-item ${this.metrics.application.avg_response_time > 1 ? 'warning' : 'good'}">
                        <div class="health-icon">
                            <i class="fas fa-clock"></i>
                        </div>
                        <div class="health-info">
                            <div class="health-label">Temps de Réponse</div>
                            <div class="health-value">${this.metrics.application.avg_response_time.toFixed(3)}s</div>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    renderSystemMetrics() {
        if (!this.metrics) return '';

        return `
            <div class="performance-section">
                <h3>Métriques Système</h3>
                <div class="metrics-grid">
                    <div class="metric-card">
                        <h4>CPU</h4>
                        <div class="metric-current">${this.metrics.system.cpu_usage_current.toFixed(1)}%</div>
                        <div class="metric-average">Moyenne: ${this.metrics.system.cpu_usage_avg.toFixed(1)}%</div>
                        <div class="metric-progress">
                            <div class="progress-bar" style="width: ${this.metrics.system.cpu_usage_current}%"></div>
                        </div>
                    </div>
                    <div class="metric-card">
                        <h4>Mémoire</h4>
                        <div class="metric-current">${this.metrics.system.memory_usage_current.toFixed(1)}%</div>
                        <div class="metric-average">Moyenne: ${this.metrics.system.memory_usage_avg.toFixed(1)}%</div>
                        <div class="metric-progress">
                            <div class="progress-bar" style="width: ${this.metrics.system.memory_usage_current}%"></div>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    renderApplicationMetrics() {
        if (!this.metrics) return '';

        return `
            <div class="performance-section">
                <h3>Métriques Application</h3>
                <div class="metrics-grid">
                    <div class="metric-card">
                        <h4>Connexions Actives</h4>
                        <div class="metric-current">${this.metrics.application.active_connections}</div>
                        <div class="metric-average">Limite: ${this.metrics.application.max_connections}</div>
                        <div class="metric-progress">
                            <div class="progress-bar" style="width: ${(this.metrics.application.active_connections / this.metrics.application.max_connections) * 100}%"></div>
                        </div>
                    </div>
                    <div class="metric-card">
                        <h4>Cache</h4>
                        <div class="metric-current">${this.metrics.application.cache_size}</div>
                        <div class="metric-average">entrées</div>
                        <button class="btn btn-sm btn-outline-danger clear-cache-btn">
                            <i class="fas fa-trash"></i>
                            Vider
                        </button>
                    </div>
                    <div class="metric-card">
                        <h4>Temps de Réponse Moyen</h4>
                        <div class="metric-current">${this.metrics.application.avg_response_time.toFixed(3)}s</div>
                        <div class="metric-average">${this.metrics.application.avg_response_time < 0.5 ? 'Excellent' : this.metrics.application.avg_response_time < 1 ? 'Bon' : 'À améliorer'}</div>
                    </div>
                </div>
            </div>
        `;
    }

    renderPerformanceCharts() {
        return `
            <div class="performance-section">
                <h3>Graphiques de Performance</h3>
                <div class="charts-container">
                    <div class="chart-wrapper">
                        <h4>Utilisation CPU/Mémoire</h4>
                        <canvas id="systemChart" width="400" height="200"></canvas>
                    </div>
                    <div class="chart-wrapper">
                        <h4>Connexions Actives</h4>
                        <canvas id="connectionsChart" width="400" height="200"></canvas>
                    </div>
                </div>
            </div>
        `;
    }

    renderRecommendations() {
        if (!this.recommendations || this.recommendations.length === 0) {
            return `
                <div class="performance-section">
                    <h3>Recommandations</h3>
                    <div class="no-recommendations">
                        <i class="fas fa-check-circle"></i>
                        <p>Aucune recommandation d'optimisation pour le moment.</p>
                    </div>
                </div>
            `;
        }

        const recommendationsHtml = this.recommendations.map(rec => `
            <div class="recommendation-item ${rec.severity}">
                <div class="recommendation-header">
                    <div class="recommendation-icon">
                        <i class="fas fa-${rec.severity === 'high' ? 'exclamation-triangle' : rec.severity === 'medium' ? 'exclamation-circle' : 'info-circle'}"></i>
                    </div>
                    <div class="recommendation-title">
                        <h5>${rec.message}</h5>
                        <span class="recommendation-type">${rec.type}</span>
                    </div>
                    <div class="recommendation-severity">
                        ${rec.severity}
                    </div>
                </div>
                <div class="recommendation-suggestions">
                    <ul>
                        ${rec.suggestions.map(suggestion => `<li>${suggestion}</li>`).join('')}
                    </ul>
                </div>
            </div>
        `).join('');

        return `
            <div class="performance-section">
                <h3>Recommandations d'Optimisation (${this.recommendations.length})</h3>
                <div class="recommendations-list">
                    ${recommendationsHtml}
                </div>
            </div>
        `;
    }

    renderOptimizationRules() {
        if (!this.metrics) return '';

        const rules = this.metrics.optimization_rules;

        return `
            <div class="performance-section">
                <h3>Règles d'Optimisation</h3>
                <div class="optimization-rules">
                    <div class="rules-grid">
                        <div class="rule-item">
                            <label>Connexions Max:</label>
                            <input type="number" id="maxConnections" value="${rules.max_concurrent_connections}" min="1" max="1000">
                        </div>
                        <div class="rule-item">
                            <label>Timeout Connexion (s):</label>
                            <input type="number" id="connectionTimeout" value="${rules.connection_timeout}" min="30" max="3600">
                        </div>
                        <div class="rule-item">
                            <label>TTL Cache (s):</label>
                            <input type="number" id="cacheTtl" value="${rules.cache_ttl_default}" min="60" max="3600">
                        </div>
                        <div class="rule-item">
                            <label>Seuil Mémoire (%):</label>
                            <input type="number" id="memoryThreshold" value="${rules.memory_threshold}" min="50" max="95">
                        </div>
                        <div class="rule-item">
                            <label>Seuil CPU (%):</label>
                            <input type="number" id="cpuThreshold" value="${rules.cpu_threshold}" min="50" max="95">
                        </div>
                        <div class="rule-item">
                            <label>Intervalle Nettoyage (s):</label>
                            <input type="number" id="cleanupInterval" value="${rules.cleanup_interval}" min="30" max="300">
                        </div>
                    </div>
                    <div class="rules-actions">
                        <button id="updateRulesBtn" class="btn btn-primary">
                            <i class="fas fa-save"></i>
                            Mettre à Jour les Règles
                        </button>
                        <button id="resetRulesBtn" class="btn btn-outline-secondary">
                            <i class="fas fa-undo"></i>
                            Réinitialiser
                        </button>
                    </div>
                </div>
            </div>
        `;
    }

    initializeCharts() {
        if (!this.history) return;

        // Graphique CPU/Mémoire
        this.initSystemChart();
        
        // Graphique des connexions
        this.initConnectionsChart();
    }

    initSystemChart() {
        const canvas = document.getElementById('systemChart');
        if (!canvas) return;

        const ctx = canvas.getContext('2d');
        
        // Préparer les données
        const cpuData = this.history.cpu_usage || [];
        const memoryData = this.history.memory_usage || [];
        
        const labels = cpuData.map(item => new Date(item.timestamp * 1000).toLocaleTimeString());
        const cpuValues = cpuData.map(item => item.value);
        const memoryValues = memoryData.map(item => item.value);

        // Graphique simple avec Canvas
        this.drawLineChart(ctx, {
            labels: labels.slice(-20), // Dernières 20 valeurs
            datasets: [
                {
                    label: 'CPU %',
                    data: cpuValues.slice(-20),
                    color: '#ff6b6b'
                },
                {
                    label: 'Mémoire %',
                    data: memoryValues.slice(-20),
                    color: '#4ecdc4'
                }
            ]
        });
    }

    initConnectionsChart() {
        const canvas = document.getElementById('connectionsChart');
        if (!canvas) return;

        const ctx = canvas.getContext('2d');
        
        const connectionsData = this.history.active_connections || [];
        const labels = connectionsData.map(item => new Date(item.timestamp * 1000).toLocaleTimeString());
        const values = connectionsData.map(item => item.value);

        this.drawLineChart(ctx, {
            labels: labels.slice(-20),
            datasets: [
                {
                    label: 'Connexions Actives',
                    data: values.slice(-20),
                    color: '#45b7d1'
                }
            ]
        });
    }

    drawLineChart(ctx, data) {
        const canvas = ctx.canvas;
        const width = canvas.width;
        const height = canvas.height;
        const padding = 40;

        // Effacer le canvas
        ctx.clearRect(0, 0, width, height);

        if (!data.datasets || data.datasets.length === 0) return;

        // Calculer les échelles
        const allValues = data.datasets.flatMap(dataset => dataset.data);
        const maxValue = Math.max(...allValues, 100);
        const minValue = Math.min(...allValues, 0);

        const xStep = (width - 2 * padding) / (data.labels.length - 1);
        const yScale = (height - 2 * padding) / (maxValue - minValue);

        // Dessiner les axes
        ctx.strokeStyle = '#ddd';
        ctx.lineWidth = 1;
        
        // Axe Y
        ctx.beginPath();
        ctx.moveTo(padding, padding);
        ctx.lineTo(padding, height - padding);
        ctx.stroke();
        
        // Axe X
        ctx.beginPath();
        ctx.moveTo(padding, height - padding);
        ctx.lineTo(width - padding, height - padding);
        ctx.stroke();

        // Dessiner les datasets
        data.datasets.forEach((dataset, index) => {
            ctx.strokeStyle = dataset.color;
            ctx.lineWidth = 2;
            ctx.beginPath();

            dataset.data.forEach((value, i) => {
                const x = padding + i * xStep;
                const y = height - padding - (value - minValue) * yScale;

                if (i === 0) {
                    ctx.moveTo(x, y);
                } else {
                    ctx.lineTo(x, y);
                }
            });

            ctx.stroke();
        });

        // Légende
        ctx.font = '12px Arial';
        data.datasets.forEach((dataset, index) => {
            ctx.fillStyle = dataset.color;
            ctx.fillText(dataset.label, width - 100, 20 + index * 20);
        });
    }

    attachEventListeners() {
        // Actualisation manuelle
        const refreshBtn = this.container.querySelector('#refreshBtn');
        refreshBtn?.addEventListener('click', () => {
            this.refresh();
        });

        // Export des données
        const exportBtn = this.container.querySelector('#exportBtn');
        exportBtn?.addEventListener('click', () => {
            this.exportData();
        });

        // Toggle mise à jour automatique
        const autoUpdateToggle = this.container.querySelector('#autoUpdateToggle');
        autoUpdateToggle?.addEventListener('change', (e) => {
            if (e.target.checked) {
                this.startAutoUpdate();
            } else {
                this.stopAutoUpdate();
            }
        });

        // Vider le cache
        const clearCacheBtn = this.container.querySelector('.clear-cache-btn');
        clearCacheBtn?.addEventListener('click', () => {
            this.clearCache();
        });

        // Mettre à jour les règles
        const updateRulesBtn = this.container.querySelector('#updateRulesBtn');
        updateRulesBtn?.addEventListener('click', () => {
            this.updateOptimizationRules();
        });

        // Réinitialiser les règles
        const resetRulesBtn = this.container.querySelector('#resetRulesBtn');
        resetRulesBtn?.addEventListener('click', () => {
            this.resetOptimizationRules();
        });
    }

    async refresh() {
        this.showLoading();
        await this.loadData();
        this.render();
        this.attachEventListeners();
        this.hideLoading();
    }

    startAutoUpdate() {
        if (this.updateInterval) return;
        
        this.updateInterval = setInterval(() => {
            this.refresh();
        }, 30000); // Mise à jour toutes les 30 secondes
    }

    stopAutoUpdate() {
        if (this.updateInterval) {
            clearInterval(this.updateInterval);
            this.updateInterval = null;
        }
    }

    async clearCache() {
        try {
            const response = await fetch('/api/performance/cache/clear', {
                method: 'POST'
            });
            const result = await response.json();
            
            if (result.success) {
                this.showNotification('Cache vidé avec succès', 'success');
                this.refresh();
            } else {
                this.showNotification(`Erreur: ${result.error}`, 'error');
            }
        } catch (error) {
            this.showNotification(`Erreur: ${error.message}`, 'error');
        }
    }

    async updateOptimizationRules() {
        try {
            const rules = {
                max_concurrent_connections: parseInt(this.container.querySelector('#maxConnections').value),
                connection_timeout: parseInt(this.container.querySelector('#connectionTimeout').value),
                cache_ttl_default: parseInt(this.container.querySelector('#cacheTtl').value),
                memory_threshold: parseInt(this.container.querySelector('#memoryThreshold').value),
                cpu_threshold: parseInt(this.container.querySelector('#cpuThreshold').value),
                cleanup_interval: parseInt(this.container.querySelector('#cleanupInterval').value)
            };

            const response = await fetch('/api/performance/optimization-rules', {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(rules)
            });

            const result = await response.json();
            
            if (result.success) {
                this.showNotification('Règles mises à jour avec succès', 'success');
                this.refresh();
            } else {
                this.showNotification(`Erreur: ${result.error}`, 'error');
            }
        } catch (error) {
            this.showNotification(`Erreur: ${error.message}`, 'error');
        }
    }

    resetOptimizationRules() {
        // Valeurs par défaut
        const defaults = {
            maxConnections: 50,
            connectionTimeout: 300,
            cacheTtl: 300,
            memoryThreshold: 80,
            cpuThreshold: 85,
            cleanupInterval: 60
        };

        Object.entries(defaults).forEach(([key, value]) => {
            const input = this.container.querySelector(`#${key}`);
            if (input) input.value = value;
        });
    }

    exportData() {
        const exportData = {
            timestamp: new Date().toISOString(),
            metrics: this.metrics,
            history: this.history,
            recommendations: this.recommendations
        };

        const blob = new Blob([JSON.stringify(exportData, null, 2)], {
            type: 'application/json'
        });
        
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `performance-report-${new Date().toISOString().split('T')[0]}.json`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);

        this.showNotification('Rapport exporté avec succès', 'success');
    }

    getStatusClass(value, warningThreshold, criticalThreshold) {
        if (value >= criticalThreshold) return 'critical';
        if (value >= warningThreshold) return 'warning';
        return 'good';
    }

    showLoading() {
        // Implémenter l'affichage de chargement
        console.log('Loading...');
    }

    hideLoading() {
        // Implémenter la suppression du chargement
        console.log('Loading hidden');
    }

    showNotification(message, type = 'info') {
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.innerHTML = `
            <i class="fas fa-${type === 'success' ? 'check' : type === 'error' ? 'times' : 'info'}"></i>
            ${message}
        `;
        
        document.body.appendChild(notification);
        
        setTimeout(() => {
            notification.remove();
        }, 5000);
    }

    destroy() {
        this.stopAutoUpdate();
    }
}

// Styles CSS pour le monitoring des performances
const performanceMonitorStyles = `
.performance-monitor {
    max-width: 1400px;
    margin: 0 auto;
    padding: 20px;
}

.performance-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 30px;
    padding-bottom: 15px;
    border-bottom: 2px solid #e0e0e0;
}

.performance-controls {
    display: flex;
    align-items: center;
    gap: 15px;
}

.auto-update-toggle {
    display: flex;
    align-items: center;
    gap: 8px;
}

.switch {
    position: relative;
    display: inline-block;
    width: 50px;
    height: 24px;
}

.switch input {
    opacity: 0;
    width: 0;
    height: 0;
}

.slider {
    position: absolute;
    cursor: pointer;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background-color: #ccc;
    transition: .4s;
    border-radius: 24px;
}

.slider:before {
    position: absolute;
    content: "";
    height: 18px;
    width: 18px;
    left: 3px;
    bottom: 3px;
    background-color: white;
    transition: .4s;
    border-radius: 50%;
}

input:checked + .slider {
    background-color: #007bff;
}

input:checked + .slider:before {
    transform: translateX(26px);
}

.performance-section {
    background: white;
    border-radius: 8px;
    padding: 25px;
    margin-bottom: 25px;
    box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
}

.health-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 20px;
    margin-top: 15px;
}

.health-item {
    display: flex;
    align-items: center;
    padding: 20px;
    border-radius: 8px;
    border-left: 4px solid;
}

.health-item.good {
    background: #f8fff8;
    border-left-color: #28a745;
}

.health-item.warning {
    background: #fffbf0;
    border-left-color: #ffc107;
}

.health-item.critical {
    background: #fff5f5;
    border-left-color: #dc3545;
}

.health-icon {
    font-size: 24px;
    margin-right: 15px;
    color: inherit;
}

.health-info {
    flex: 1;
}

.health-label {
    font-size: 14px;
    color: #666;
    margin-bottom: 5px;
}

.health-value {
    font-size: 20px;
    font-weight: bold;
}

.metrics-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
    gap: 20px;
    margin-top: 15px;
}

.metric-card {
    background: #f8f9fa;
    padding: 20px;
    border-radius: 8px;
    border: 1px solid #e0e0e0;
}

.metric-card h4 {
    margin: 0 0 10px 0;
    color: #333;
}

.metric-current {
    font-size: 24px;
    font-weight: bold;
    color: #007bff;
    margin-bottom: 5px;
}

.metric-average {
    font-size: 14px;
    color: #666;
    margin-bottom: 10px;
}

.metric-progress {
    width: 100%;
    height: 8px;
    background: #e0e0e0;
    border-radius: 4px;
    overflow: hidden;
}

.progress-bar {
    height: 100%;
    background: linear-gradient(90deg, #28a745, #ffc107, #dc3545);
    transition: width 0.3s ease;
}

.charts-container {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
    gap: 30px;
    margin-top: 20px;
}

.chart-wrapper {
    background: #f8f9fa;
    padding: 20px;
    border-radius: 8px;
    border: 1px solid #e0e0e0;
}

.chart-wrapper h4 {
    margin: 0 0 15px 0;
    text-align: center;
}

.recommendations-list {
    margin-top: 15px;
}

.recommendation-item {
    border: 1px solid #e0e0e0;
    border-radius: 8px;
    margin-bottom: 15px;
    overflow: hidden;
}

.recommendation-item.high {
    border-left: 4px solid #dc3545;
}

.recommendation-item.medium {
    border-left: 4px solid #ffc107;
}

.recommendation-item.low {
    border-left: 4px solid #17a2b8;
}

.recommendation-header {
    display: flex;
    align-items: center;
    padding: 15px 20px;
    background: #f8f9fa;
}

.recommendation-icon {
    font-size: 20px;
    margin-right: 15px;
}

.recommendation-title {
    flex: 1;
}

.recommendation-title h5 {
    margin: 0 0 5px 0;
}

.recommendation-type {
    font-size: 12px;
    color: #666;
    text-transform: uppercase;
}

.recommendation-severity {
    padding: 4px 8px;
    border-radius: 4px;
    font-size: 12px;
    font-weight: bold;
    text-transform: uppercase;
}

.recommendation-item.high .recommendation-severity {
    background: #dc3545;
    color: white;
}

.recommendation-item.medium .recommendation-severity {
    background: #ffc107;
    color: #000;
}

.recommendation-item.low .recommendation-severity {
    background: #17a2b8;
    color: white;
}

.recommendation-suggestions {
    padding: 15px 20px;
}

.recommendation-suggestions ul {
    margin: 0;
    padding-left: 20px;
}

.recommendation-suggestions li {
    margin-bottom: 5px;
}

.no-recommendations {
    text-align: center;
    padding: 40px;
    color: #666;
}

.no-recommendations i {
    font-size: 48px;
    color: #28a745;
    margin-bottom: 15px;
}

.optimization-rules {
    margin-top: 15px;
}

.rules-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
    gap: 20px;
    margin-bottom: 20px;
}

.rule-item {
    display: flex;
    flex-direction: column;
}

.rule-item label {
    font-weight: bold;
    margin-bottom: 5px;
    color: #333;
}

.rule-item input {
    padding: 8px 12px;
    border: 1px solid #ddd;
    border-radius: 4px;
    font-size: 14px;
}

.rules-actions {
    display: flex;
    gap: 10px;
}

.notification {
    position: fixed;
    top: 20px;
    right: 20px;
    padding: 15px 20px;
    border-radius: 4px;
    color: white;
    z-index: 10001;
    animation: slideIn 0.3s ease;
    display: flex;
    align-items: center;
    gap: 10px;
}

.notification-success { background: #28a745; }
.notification-error { background: #dc3545; }
.notification-info { background: #17a2b8; }

@keyframes slideIn {
    from {
        transform: translateX(100%);
        opacity: 0;
    }
    to {
        transform: translateX(0);
        opacity: 1;
    }
}
`;

// Injecter les styles
if (!document.getElementById('performance-monitor-styles')) {
    const styleSheet = document.createElement('style');
    styleSheet.id = 'performance-monitor-styles';
    styleSheet.textContent = performanceMonitorStyles;
    document.head.appendChild(styleSheet);
}

// Exporter la classe
window.PerformanceMonitor = PerformanceMonitor;

