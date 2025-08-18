/**
 * Composant de gestion SSL/TLS
 */
class SSLManager {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
        this.sslStatus = null;
        
        this.init();
    }

    async init() {
        await this.loadSSLStatus();
        this.render();
        this.attachEventListeners();
    }

    async loadSSLStatus() {
        try {
            const response = await fetch('/api/ssl/status');
            const result = await response.json();
            
            if (result.success) {
                this.sslStatus = result;
            } else {
                console.error('Erreur lors du chargement du statut SSL:', result.error);
            }
        } catch (error) {
            console.error('Erreur lors du chargement du statut SSL:', error);
        }
    }

    render() {
        this.container.innerHTML = `
            <div class="ssl-manager">
                <div class="ssl-header">
                    <h2>Gestion SSL/TLS</h2>
                    <div class="ssl-status-badge" id="sslStatusBadge">
                        ${this.getStatusBadge()}
                    </div>
                </div>

                <div class="ssl-content">
                    ${this.renderCurrentStatus()}
                    ${this.renderSSLSetup()}
                    ${this.renderCaddyManagement()}
                    ${this.renderCertificates()}
                </div>
            </div>
        `;
    }

    getStatusBadge() {
        if (!this.sslStatus) {
            return '<span class="badge badge-secondary">Chargement...</span>';
        }

        if (this.sslStatus.ssl_enabled) {
            return '<span class="badge badge-success"><i class="fas fa-lock"></i> SSL Activé</span>';
        } else if (this.sslStatus.caddy_installed) {
            return '<span class="badge badge-warning"><i class="fas fa-exclamation-triangle"></i> SSL Disponible</span>';
        } else {
            return '<span class="badge badge-danger"><i class="fas fa-unlock"></i> SSL Non Configuré</span>';
        }
    }

    renderCurrentStatus() {
        if (!this.sslStatus) {
            return '<div class="ssl-section loading">Chargement du statut...</div>';
        }

        return `
            <div class="ssl-section">
                <h3>Statut Actuel</h3>
                <div class="status-grid">
                    <div class="status-item">
                        <div class="status-label">Caddy Installé</div>
                        <div class="status-value ${this.sslStatus.caddy_installed ? 'success' : 'danger'}">
                            <i class="fas fa-${this.sslStatus.caddy_installed ? 'check' : 'times'}"></i>
                            ${this.sslStatus.caddy_installed ? 'Oui' : 'Non'}
                        </div>
                    </div>
                    <div class="status-item">
                        <div class="status-label">Service Actif</div>
                        <div class="status-value ${this.sslStatus.caddy_active ? 'success' : 'danger'}">
                            <i class="fas fa-${this.sslStatus.caddy_active ? 'play' : 'stop'}"></i>
                            ${this.sslStatus.caddy_active ? 'Actif' : 'Inactif'}
                        </div>
                    </div>
                    <div class="status-item">
                        <div class="status-label">SSL Activé</div>
                        <div class="status-value ${this.sslStatus.ssl_enabled ? 'success' : 'warning'}">
                            <i class="fas fa-${this.sslStatus.ssl_enabled ? 'lock' : 'unlock'}"></i>
                            ${this.sslStatus.ssl_enabled ? 'Activé' : 'Désactivé'}
                        </div>
                    </div>
                    <div class="status-item">
                        <div class="status-label">Certificats</div>
                        <div class="status-value info">
                            <i class="fas fa-certificate"></i>
                            ${this.sslStatus.certificates || 0}
                        </div>
                    </div>
                </div>
            </div>
        `;
    }

    renderSSLSetup() {
        return `
            <div class="ssl-section">
                <h3>Configuration SSL/TLS</h3>
                <form id="sslSetupForm" class="ssl-setup-form">
                    <div class="form-group">
                        <label for="domain">Domaine:</label>
                        <input type="text" id="domain" class="form-control" 
                               placeholder="localhost ou votre-domaine.com" value="localhost">
                        <small class="form-text text-muted">
                            Utilisez "localhost" pour le développement local avec certificat auto-signé
                        </small>
                    </div>

                    <div class="form-group" id="emailGroup">
                        <label for="email">Email (Let's Encrypt):</label>
                        <input type="email" id="email" class="form-control" 
                               placeholder="admin@votre-domaine.com">
                        <small class="form-text text-muted">
                            Requis pour les certificats Let's Encrypt (domaines publics uniquement)
                        </small>
                    </div>

                    <div class="advanced-options">
                        <h4>Options Avancées</h4>
                        
                        <div class="form-row">
                            <div class="form-group col-md-6">
                                <label for="flaskPort">Port Flask:</label>
                                <input type="number" id="flaskPort" class="form-control" value="5000">
                            </div>
                            <div class="form-group col-md-6">
                                <label for="websocketPort">Port WebSocket:</label>
                                <input type="number" id="websocketPort" class="form-control" value="8765">
                            </div>
                        </div>

                        <div class="form-group">
                            <label for="staticDir">Répertoire Statique:</label>
                            <input type="text" id="staticDir" class="form-control" 
                                   value="/home/ubuntu/src/static">
                        </div>

                        <div class="form-group">
                            <label class="checkbox-option">
                                <input type="checkbox" id="staging">
                                <span class="checkbox-label">
                                    Utiliser Let's Encrypt Staging (pour les tests)
                                </span>
                            </label>
                        </div>
                    </div>

                    <div class="form-actions">
                        <button type="button" id="previewConfig" class="btn btn-outline-primary">
                            <i class="fas fa-eye"></i>
                            Prévisualiser la Configuration
                        </button>
                        <button type="submit" class="btn btn-primary">
                            <i class="fas fa-cog"></i>
                            Configurer SSL/TLS
                        </button>
                    </div>
                </form>
            </div>
        `;
    }

    renderCaddyManagement() {
        if (!this.sslStatus || !this.sslStatus.caddy_installed) {
            return `
                <div class="ssl-section">
                    <h3>Installation Caddy</h3>
                    <p>Caddy n'est pas installé. Cliquez sur le bouton ci-dessous pour l'installer.</p>
                    <button id="installCaddy" class="btn btn-primary">
                        <i class="fas fa-download"></i>
                        Installer Caddy
                    </button>
                </div>
            `;
        }

        return `
            <div class="ssl-section">
                <h3>Gestion du Service Caddy</h3>
                <div class="caddy-controls">
                    <button id="restartCaddy" class="btn btn-warning">
                        <i class="fas fa-redo"></i>
                        Redémarrer Caddy
                    </button>
                    <button id="reloadCaddy" class="btn btn-info">
                        <i class="fas fa-sync"></i>
                        Recharger la Configuration
                    </button>
                    <button id="viewCaddyStatus" class="btn btn-outline-secondary">
                        <i class="fas fa-info-circle"></i>
                        Voir le Statut Détaillé
                    </button>
                    <button id="createSetupScript" class="btn btn-outline-primary">
                        <i class="fas fa-file-code"></i>
                        Créer Script d'Installation
                    </button>
                </div>
            </div>
        `;
    }

    renderCertificates() {
        if (!this.sslStatus || !this.sslStatus.certificate_details || this.sslStatus.certificate_details.length === 0) {
            return `
                <div class="ssl-section">
                    <h3>Certificats SSL</h3>
                    <p class="text-muted">Aucun certificat SSL trouvé.</p>
                </div>
            `;
        }

        const certificatesHtml = this.sslStatus.certificate_details.map(cert => `
            <div class="certificate-item">
                <div class="certificate-info">
                    <h5>${cert.domain}</h5>
                    <small class="text-muted">${cert.path}</small>
                </div>
                <div class="certificate-actions">
                    <button class="btn btn-sm btn-outline-info view-cert-btn" data-cert-path="${cert.path}">
                        <i class="fas fa-eye"></i>
                        Voir Détails
                    </button>
                </div>
            </div>
        `).join('');

        return `
            <div class="ssl-section">
                <h3>Certificats SSL (${this.sslStatus.certificates})</h3>
                <div class="certificates-list">
                    ${certificatesHtml}
                </div>
                <button id="refreshCertificates" class="btn btn-outline-secondary">
                    <i class="fas fa-sync"></i>
                    Actualiser la Liste
                </button>
            </div>
        `;
    }

    attachEventListeners() {
        // Gestion du changement de domaine
        const domainInput = this.container.querySelector('#domain');
        domainInput?.addEventListener('input', (e) => {
            this.onDomainChange(e.target.value);
        });

        // Configuration SSL
        const sslForm = this.container.querySelector('#sslSetupForm');
        sslForm?.addEventListener('submit', (e) => {
            e.preventDefault();
            this.setupSSL();
        });

        // Prévisualisation de la configuration
        const previewBtn = this.container.querySelector('#previewConfig');
        previewBtn?.addEventListener('click', () => {
            this.previewConfiguration();
        });

        // Installation Caddy
        const installBtn = this.container.querySelector('#installCaddy');
        installBtn?.addEventListener('click', () => {
            this.installCaddy();
        });

        // Gestion Caddy
        const restartBtn = this.container.querySelector('#restartCaddy');
        restartBtn?.addEventListener('click', () => {
            this.restartCaddy();
        });

        const reloadBtn = this.container.querySelector('#reloadCaddy');
        reloadBtn?.addEventListener('click', () => {
            this.reloadCaddy();
        });

        const statusBtn = this.container.querySelector('#viewCaddyStatus');
        statusBtn?.addEventListener('click', () => {
            this.viewCaddyStatus();
        });

        const scriptBtn = this.container.querySelector('#createSetupScript');
        scriptBtn?.addEventListener('click', () => {
            this.createSetupScript();
        });

        // Actualisation des certificats
        const refreshBtn = this.container.querySelector('#refreshCertificates');
        refreshBtn?.addEventListener('click', () => {
            this.refreshCertificates();
        });

        // Voir les détails des certificats
        const viewCertBtns = this.container.querySelectorAll('.view-cert-btn');
        viewCertBtns.forEach(btn => {
            btn.addEventListener('click', (e) => {
                this.viewCertificateDetails(e.target.dataset.certPath);
            });
        });
    }

    onDomainChange(domain) {
        const emailGroup = this.container.querySelector('#emailGroup');
        const emailInput = this.container.querySelector('#email');
        
        if (domain.startsWith('localhost')) {
            emailGroup.style.display = 'none';
            emailInput.required = false;
        } else {
            emailGroup.style.display = 'block';
            emailInput.required = true;
        }
    }

    async setupSSL() {
        const formData = this.getFormData();
        
        if (!this.validateFormData(formData)) {
            return;
        }

        this.showLoading('Configuration SSL/TLS en cours...');

        try {
            const response = await fetch('/api/ssl/setup', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(formData)
            });

            const result = await response.json();

            if (result.success) {
                this.showNotification('SSL/TLS configuré avec succès!', 'success');
                this.showSSLSetupResult(result);
                await this.loadSSLStatus();
                this.render();
            } else {
                this.showNotification(`Erreur: ${result.error}`, 'error');
            }
        } catch (error) {
            this.showNotification(`Erreur de configuration: ${error.message}`, 'error');
        } finally {
            this.hideLoading();
        }
    }

    async previewConfiguration() {
        const formData = this.getFormData();

        try {
            const response = await fetch('/api/ssl/generate-caddyfile', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(formData)
            });

            const result = await response.json();

            if (result.success) {
                this.showConfigPreview(result.caddyfile);
            } else {
                this.showNotification(`Erreur: ${result.error}`, 'error');
            }
        } catch (error) {
            this.showNotification(`Erreur: ${error.message}`, 'error');
        }
    }

    async installCaddy() {
        this.showLoading('Installation de Caddy en cours...');

        try {
            const response = await fetch('/api/ssl/install-caddy', {
                method: 'POST'
            });

            const result = await response.json();

            if (result.success) {
                this.showNotification('Caddy installé avec succès!', 'success');
                await this.loadSSLStatus();
                this.render();
            } else {
                this.showNotification(`Erreur d'installation: ${result.error}`, 'error');
            }
        } catch (error) {
            this.showNotification(`Erreur: ${error.message}`, 'error');
        } finally {
            this.hideLoading();
        }
    }

    async restartCaddy() {
        this.showLoading('Redémarrage de Caddy...');

        try {
            const response = await fetch('/api/ssl/caddy/restart', {
                method: 'POST'
            });

            const result = await response.json();

            if (result.success) {
                this.showNotification('Caddy redémarré avec succès!', 'success');
                await this.loadSSLStatus();
                this.updateStatusBadge();
            } else {
                this.showNotification(`Erreur: ${result.error}`, 'error');
            }
        } catch (error) {
            this.showNotification(`Erreur: ${error.message}`, 'error');
        } finally {
            this.hideLoading();
        }
    }

    async reloadCaddy() {
        this.showLoading('Rechargement de la configuration...');

        try {
            const response = await fetch('/api/ssl/caddy/reload', {
                method: 'POST'
            });

            const result = await response.json();

            if (result.success) {
                this.showNotification('Configuration rechargée avec succès!', 'success');
            } else {
                this.showNotification(`Erreur: ${result.error}`, 'error');
            }
        } catch (error) {
            this.showNotification(`Erreur: ${error.message}`, 'error');
        } finally {
            this.hideLoading();
        }
    }

    async viewCaddyStatus() {
        try {
            const response = await fetch('/api/ssl/caddy/status');
            const result = await response.json();

            if (result.success) {
                this.showCaddyStatusModal(result.caddy_status);
            } else {
                this.showNotification(`Erreur: ${result.error}`, 'error');
            }
        } catch (error) {
            this.showNotification(`Erreur: ${error.message}`, 'error');
        }
    }

    async createSetupScript() {
        try {
            const response = await fetch('/api/ssl/create-setup-script', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    output_path: '/home/ubuntu/setup_ssl.sh'
                })
            });

            const result = await response.json();

            if (result.success) {
                this.showNotification('Script créé avec succès!', 'success');
                this.showScriptInfo(result.script_path);
            } else {
                this.showNotification(`Erreur: ${result.error}`, 'error');
            }
        } catch (error) {
            this.showNotification(`Erreur: ${error.message}`, 'error');
        }
    }

    async refreshCertificates() {
        await this.loadSSLStatus();
        this.render();
        this.showNotification('Liste des certificats actualisée', 'info');
    }

    getFormData() {
        return {
            domain: this.container.querySelector('#domain').value,
            email: this.container.querySelector('#email').value,
            flask_port: parseInt(this.container.querySelector('#flaskPort').value),
            websocket_port: parseInt(this.container.querySelector('#websocketPort').value),
            static_dir: this.container.querySelector('#staticDir').value,
            staging: this.container.querySelector('#staging').checked
        };
    }

    validateFormData(data) {
        if (!data.domain) {
            this.showNotification('Veuillez entrer un domaine', 'error');
            return false;
        }

        if (!data.domain.startsWith('localhost') && !data.email) {
            this.showNotification('Email requis pour les certificats Let\'s Encrypt', 'error');
            return false;
        }

        return true;
    }

    updateStatusBadge() {
        const badge = this.container.querySelector('#sslStatusBadge');
        if (badge) {
            badge.innerHTML = this.getStatusBadge();
        }
    }

    showSSLSetupResult(result) {
        const modal = this.createModal('Configuration SSL Terminée', `
            <div class="ssl-setup-result">
                <div class="alert alert-success">
                    <i class="fas fa-check-circle"></i>
                    SSL/TLS configuré avec succès pour <strong>${result.domain}</strong>
                </div>
                <p>Votre application est maintenant accessible via:</p>
                <div class="https-url">
                    <a href="${result.https_url}" target="_blank" class="btn btn-primary">
                        <i class="fas fa-external-link-alt"></i>
                        ${result.https_url}
                    </a>
                </div>
                <div class="ssl-info">
                    <h5>Informations importantes:</h5>
                    <ul>
                        <li>Les connexions HTTP sont automatiquement redirigées vers HTTPS</li>
                        <li>Les certificats sont renouvelés automatiquement</li>
                        <li>Les logs Caddy sont disponibles dans /var/log/caddy/</li>
                    </ul>
                </div>
            </div>
        `);
        
        document.body.appendChild(modal);
    }

    showConfigPreview(caddyfile) {
        const modal = this.createModal('Prévisualisation de la Configuration Caddy', `
            <div class="config-preview">
                <p>Voici la configuration Caddy qui sera générée:</p>
                <pre class="caddyfile-preview"><code>${caddyfile}</code></pre>
                <div class="preview-actions">
                    <button class="btn btn-secondary" onclick="this.closest('.modal').remove()">
                        Fermer
                    </button>
                    <button class="btn btn-primary" onclick="navigator.clipboard.writeText('${caddyfile.replace(/'/g, "\\'")}'); this.textContent='Copié!'">
                        Copier dans le Presse-papiers
                    </button>
                </div>
            </div>
        `);
        
        document.body.appendChild(modal);
    }

    showCaddyStatusModal(status) {
        const modal = this.createModal('Statut Détaillé de Caddy', `
            <div class="caddy-status-detail">
                <div class="status-summary">
                    <div class="status-item">
                        <strong>Actif:</strong> ${status.active ? 'Oui' : 'Non'}
                    </div>
                    <div class="status-item">
                        <strong>Activé au démarrage:</strong> ${status.enabled ? 'Oui' : 'Non'}
                    </div>
                </div>
                <h5>Sortie du Statut:</h5>
                <pre class="status-output">${status.status_output}</pre>
            </div>
        `);
        
        document.body.appendChild(modal);
    }

    showScriptInfo(scriptPath) {
        const modal = this.createModal('Script d\'Installation Créé', `
            <div class="script-info">
                <div class="alert alert-success">
                    <i class="fas fa-file-code"></i>
                    Script créé avec succès: <code>${scriptPath}</code>
                </div>
                <h5>Utilisation:</h5>
                <pre class="script-usage">
# Rendre le script exécutable
chmod +x ${scriptPath}

# Exécuter pour localhost (développement)
./${scriptPath.split('/').pop()}

# Exécuter pour un domaine public
./${scriptPath.split('/').pop()} votre-domaine.com admin@votre-domaine.com
                </pre>
                <p>Ce script automatise l'installation et la configuration complète de SSL/TLS.</p>
            </div>
        `);
        
        document.body.appendChild(modal);
    }

    createModal(title, content) {
        const modal = document.createElement('div');
        modal.className = 'modal ssl-modal';
        modal.innerHTML = `
            <div class="modal-content">
                <div class="modal-header">
                    <h3>${title}</h3>
                    <button class="modal-close" onclick="this.closest('.modal').remove()">
                        <i class="fas fa-times"></i>
                    </button>
                </div>
                <div class="modal-body">
                    ${content}
                </div>
            </div>
        `;
        
        return modal;
    }

    showLoading(message) {
        // Implémenter l'affichage de chargement
        console.log('Loading:', message);
    }

    hideLoading() {
        // Implémenter la suppression du chargement
        console.log('Loading hidden');
    }

    showNotification(message, type = 'info') {
        // Implémenter les notifications
        console.log(`${type}: ${message}`);
        
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
}

// Styles CSS pour le gestionnaire SSL
const sslManagerStyles = `
.ssl-manager {
    max-width: 1200px;
    margin: 0 auto;
    padding: 20px;
}

.ssl-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 30px;
    padding-bottom: 15px;
    border-bottom: 2px solid #e0e0e0;
}

.ssl-status-badge .badge {
    font-size: 14px;
    padding: 8px 12px;
}

.ssl-section {
    background: white;
    border-radius: 8px;
    padding: 25px;
    margin-bottom: 25px;
    box-shadow: 0 2px 10px rgba(0, 0, 0, 0.1);
}

.status-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 20px;
    margin-top: 15px;
}

.status-item {
    text-align: center;
    padding: 15px;
    border-radius: 6px;
    background: #f8f9fa;
}

.status-label {
    font-weight: bold;
    margin-bottom: 8px;
    color: #666;
}

.status-value {
    font-size: 18px;
}

.status-value.success { color: #28a745; }
.status-value.danger { color: #dc3545; }
.status-value.warning { color: #ffc107; }
.status-value.info { color: #17a2b8; }

.ssl-setup-form .form-group {
    margin-bottom: 20px;
}

.advanced-options {
    margin-top: 25px;
    padding-top: 20px;
    border-top: 1px solid #e0e0e0;
}

.caddy-controls {
    display: flex;
    gap: 10px;
    flex-wrap: wrap;
}

.certificates-list {
    margin: 15px 0;
}

.certificate-item {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 15px;
    border: 1px solid #e0e0e0;
    border-radius: 6px;
    margin-bottom: 10px;
}

.modal.ssl-modal {
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background: rgba(0, 0, 0, 0.5);
    display: flex;
    justify-content: center;
    align-items: center;
    z-index: 10000;
}

.modal-content {
    background: white;
    border-radius: 8px;
    max-width: 800px;
    max-height: 90vh;
    overflow-y: auto;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
}

.modal-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 20px;
    border-bottom: 1px solid #e0e0e0;
}

.modal-body {
    padding: 20px;
}

.modal-close {
    background: none;
    border: none;
    font-size: 18px;
    cursor: pointer;
    color: #666;
}

.caddyfile-preview, .status-output, .script-usage {
    background: #f8f9fa;
    padding: 15px;
    border-radius: 4px;
    overflow-x: auto;
    font-family: 'Courier New', monospace;
    font-size: 12px;
    line-height: 1.4;
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
if (!document.getElementById('ssl-manager-styles')) {
    const styleSheet = document.createElement('style');
    styleSheet.id = 'ssl-manager-styles';
    styleSheet.textContent = sslManagerStyles;
    document.head.appendChild(styleSheet);
}

// Exporter la classe
window.SSLManager = SSLManager;

