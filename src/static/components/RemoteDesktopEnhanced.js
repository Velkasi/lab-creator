/**
 * Composant RemoteDesktop amélioré avec support multi-écrans et nouvel onglet
 */
class RemoteDesktopEnhanced {
    constructor(containerId, options = {}) {
        this.container = document.getElementById(containerId);
        this.options = {
            showMultiScreenOption: true,
            allowNewTab: true,
            defaultConnectionType: 'vnc',
            ...options
        };
        
        this.multiScreenManager = new MultiScreenManager();
        this.currentConnection = null;
        this.isConnected = false;
        
        this.init();
    }

    async init() {
        await this.multiScreenManager.detectScreens();
        this.render();
        this.attachEventListeners();
    }

    render() {
        this.container.innerHTML = `
            <div class="remote-desktop-enhanced">
                <div class="connection-header">
                    <h2>Accès Distant Amélioré</h2>
                    <div class="connection-status" id="connectionStatus">
                        <span class="status-indicator disconnected"></span>
                        <span class="status-text">Déconnecté</span>
                    </div>
                </div>

                <div class="connection-form" id="connectionForm">
                    <div class="form-group">
                        <label for="machineSelect">Machine:</label>
                        <select id="machineSelect" class="form-control">
                            <option value="">Sélectionner une machine...</option>
                        </select>
                    </div>

                    <div class="form-group">
                        <label for="connectionType">Type de connexion:</label>
                        <div class="connection-type-selector">
                            <label class="radio-option">
                                <input type="radio" name="connectionType" value="vnc" checked>
                                <span class="radio-label">
                                    <i class="fas fa-desktop"></i>
                                    VNC
                                </span>
                            </label>
                            <label class="radio-option">
                                <input type="radio" name="connectionType" value="rdp">
                                <span class="radio-label">
                                    <i class="fab fa-windows"></i>
                                    RDP
                                </span>
                            </label>
                        </div>
                    </div>

                    <div class="form-row">
                        <div class="form-group">
                            <label for="username">Nom d'utilisateur:</label>
                            <input type="text" id="username" class="form-control" placeholder="Entrez le nom d'utilisateur">
                        </div>
                        <div class="form-group">
                            <label for="password">Mot de passe:</label>
                            <input type="password" id="password" class="form-control" placeholder="Entrez le mot de passe">
                        </div>
                    </div>

                    <div class="form-group rdp-only" id="domainGroup" style="display: none;">
                        <label for="domain">Domaine (optionnel):</label>
                        <input type="text" id="domain" class="form-control" placeholder="Domaine Windows">
                    </div>

                    <div class="advanced-options">
                        <h4>Options Avancées</h4>
                        
                        <div class="form-group">
                            <label>Mode d'ouverture:</label>
                            <div class="opening-mode-selector">
                                <label class="radio-option">
                                    <input type="radio" name="openingMode" value="current" checked>
                                    <span class="radio-label">
                                        <i class="fas fa-window-maximize"></i>
                                        Onglet actuel
                                    </span>
                                </label>
                                <label class="radio-option">
                                    <input type="radio" name="openingMode" value="new-tab">
                                    <span class="radio-label">
                                        <i class="fas fa-external-link-alt"></i>
                                        Nouvel onglet
                                    </span>
                                </label>
                                ${this.multiScreenManager.screens.length > 1 ? `
                                <label class="radio-option">
                                    <input type="radio" name="openingMode" value="multi-screen">
                                    <span class="radio-label">
                                        <i class="fas fa-th-large"></i>
                                        Multi-écrans
                                    </span>
                                </label>
                                ` : ''}
                            </div>
                        </div>

                        <div class="form-row">
                            <div class="form-group">
                                <label for="screenWidth">Largeur:</label>
                                <select id="screenWidth" class="form-control">
                                    <option value="1024">1024</option>
                                    <option value="1280">1280</option>
                                    <option value="1366">1366</option>
                                    <option value="1920" selected>1920</option>
                                    <option value="auto">Automatique</option>
                                </select>
                            </div>
                            <div class="form-group">
                                <label for="screenHeight">Hauteur:</label>
                                <select id="screenHeight" class="form-control">
                                    <option value="768">768</option>
                                    <option value="720">720</option>
                                    <option value="1024">1024</option>
                                    <option value="1080" selected>1080</option>
                                    <option value="auto">Automatique</option>
                                </select>
                            </div>
                        </div>

                        <div class="form-group">
                            <label class="checkbox-option">
                                <input type="checkbox" id="fullscreen">
                                <span class="checkbox-label">Plein écran automatique</span>
                            </label>
                        </div>
                    </div>

                    <div class="connection-actions">
                        <button id="connectBtn" class="btn btn-primary btn-lg">
                            <i class="fas fa-plug"></i>
                            Se connecter
                        </button>
                        <button id="disconnectBtn" class="btn btn-danger btn-lg" style="display: none;">
                            <i class="fas fa-times"></i>
                            Déconnecter
                        </button>
                    </div>
                </div>

                <div class="connection-viewer" id="connectionViewer" style="display: none;">
                    <div class="viewer-toolbar">
                        <div class="toolbar-left">
                            <span class="connection-info" id="connectionInfo"></span>
                        </div>
                        <div class="toolbar-right">
                            <button id="fullscreenBtn" class="btn btn-sm btn-outline-light">
                                <i class="fas fa-expand"></i>
                            </button>
                            <button id="newTabBtn" class="btn btn-sm btn-outline-light">
                                <i class="fas fa-external-link-alt"></i>
                            </button>
                            <button id="disconnectViewerBtn" class="btn btn-sm btn-outline-danger">
                                <i class="fas fa-times"></i>
                            </button>
                        </div>
                    </div>
                    <div class="viewer-content" id="viewerContent">
                        <!-- Le contenu VNC/RDP sera injecté ici -->
                    </div>
                </div>

                <div class="active-sessions" id="activeSessions" style="display: none;">
                    <h4>Sessions Actives</h4>
                    <div class="sessions-list" id="sessionsList">
                        <!-- Les sessions actives seront listées ici -->
                    </div>
                </div>
            </div>
        `;
    }

    attachEventListeners() {
        // Gestionnaire de changement de type de connexion
        const connectionTypeInputs = this.container.querySelectorAll('input[name="connectionType"]');
        connectionTypeInputs.forEach(input => {
            input.addEventListener('change', (e) => {
                this.onConnectionTypeChange(e.target.value);
            });
        });

        // Gestionnaire de mode d'ouverture
        const openingModeInputs = this.container.querySelectorAll('input[name="openingMode"]');
        openingModeInputs.forEach(input => {
            input.addEventListener('change', (e) => {
                this.onOpeningModeChange(e.target.value);
            });
        });

        // Bouton de connexion
        const connectBtn = this.container.querySelector('#connectBtn');
        connectBtn.addEventListener('click', () => this.connect());

        // Bouton de déconnexion
        const disconnectBtn = this.container.querySelector('#disconnectBtn');
        disconnectBtn.addEventListener('click', () => this.disconnect());

        // Boutons de la barre d'outils
        const fullscreenBtn = this.container.querySelector('#fullscreenBtn');
        fullscreenBtn?.addEventListener('click', () => this.toggleFullscreen());

        const newTabBtn = this.container.querySelector('#newTabBtn');
        newTabBtn?.addEventListener('click', () => this.openInNewTab());

        const disconnectViewerBtn = this.container.querySelector('#disconnectViewerBtn');
        disconnectViewerBtn?.addEventListener('click', () => this.disconnect());

        // Écouter les événements de fermeture de session
        window.addEventListener('sessionClosed', (e) => {
            this.onSessionClosed(e.detail.sessionId);
        });

        // Charger les machines disponibles
        this.loadAvailableMachines();
    }

    onConnectionTypeChange(type) {
        const domainGroup = this.container.querySelector('#domainGroup');
        if (type === 'rdp') {
            domainGroup.style.display = 'block';
        } else {
            domainGroup.style.display = 'none';
        }
    }

    onOpeningModeChange(mode) {
        // Ajuster l'interface selon le mode sélectionné
        console.log('Mode d\'ouverture changé:', mode);
    }

    async loadAvailableMachines() {
        try {
            const response = await fetch('/api/labs');
            const labs = await response.json();
            
            const machineSelect = this.container.querySelector('#machineSelect');
            machineSelect.innerHTML = '<option value="">Sélectionner une machine...</option>';
            
            labs.forEach(lab => {
                if (lab.machines) {
                    lab.machines.forEach(machine => {
                        if (machine.status === 'running') {
                            const option = document.createElement('option');
                            option.value = machine.id;
                            option.textContent = `${lab.name} - ${machine.name} (${machine.ip_address})`;
                            machineSelect.appendChild(option);
                        }
                    });
                }
            });
        } catch (error) {
            console.error('Erreur lors du chargement des machines:', error);
        }
    }

    async connect() {
        const formData = this.getFormData();
        if (!this.validateFormData(formData)) {
            return;
        }

        this.setConnectionStatus('connecting', 'Connexion en cours...');

        try {
            // Créer la connexion
            const response = await fetch('/api/remote-access/connect', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(formData)
            });

            const result = await response.json();
            
            if (!result.success) {
                throw new Error(result.error || 'Erreur de connexion');
            }

            this.currentConnection = result;

            // Gérer selon le mode d'ouverture
            await this.handleConnectionMode(result, formData.openingMode);

        } catch (error) {
            console.error('Erreur de connexion:', error);
            this.setConnectionStatus('error', `Erreur: ${error.message}`);
        }
    }

    async handleConnectionMode(connectionData, mode) {
        switch (mode) {
            case 'new-tab':
                await this.openInNewTab(connectionData);
                break;
            case 'multi-screen':
                await this.openMultiScreen(connectionData);
                break;
            default:
                await this.openInCurrentTab(connectionData);
        }
    }

    async openInCurrentTab(connectionData) {
        // Afficher le viewer dans l'onglet actuel
        this.showConnectionViewer(connectionData);
        this.setConnectionStatus('connected', `Connecté à ${connectionData.machine_ip}`);
    }

    async openInNewTab(connectionData) {
        try {
            // Créer une URL d'accès direct
            const directAccessResponse = await fetch('/api/remote-access/create-direct-url', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    session_id: connectionData.session_id,
                    connection_type: connectionData.connection_type
                })
            });

            const directAccess = await directAccessResponse.json();
            
            if (directAccess.success) {
                // Ouvrir dans un nouvel onglet
                const newWindow = window.open(directAccess.direct_url, '_blank');
                
                if (newWindow) {
                    this.setConnectionStatus('connected', 'Session ouverte dans un nouvel onglet');
                    this.showActiveSession(connectionData, 'Nouvel onglet');
                } else {
                    throw new Error('Impossible d\'ouvrir un nouvel onglet (popup bloqué?)');
                }
            } else {
                throw new Error(directAccess.error || 'Erreur lors de la création de l\'URL d\'accès');
            }
        } catch (error) {
            console.error('Erreur ouverture nouvel onglet:', error);
            // Fallback vers l'onglet actuel
            await this.openInCurrentTab(connectionData);
        }
    }

    async openMultiScreen(connectionData) {
        try {
            // Afficher le sélecteur d'écran
            const screenSelector = this.multiScreenManager.createScreenSelector(async (selectedScreens) => {
                // Supprimer le sélecteur
                document.body.removeChild(screenSelector);
                
                if (!selectedScreens) {
                    // Annulé par l'utilisateur
                    this.setConnectionStatus('disconnected', 'Connexion annulée');
                    return;
                }

                // Ouvrir sur les écrans sélectionnés
                await this.multiScreenManager.openSessionOnMultipleScreens(connectionData, selectedScreens);
                this.setConnectionStatus('connected', `Sessions ouvertes sur ${selectedScreens.length} écran(s)`);
                this.showActiveSession(connectionData, `${selectedScreens.length} écran(s)`);
            });

            document.body.appendChild(screenSelector);
        } catch (error) {
            console.error('Erreur multi-écrans:', error);
            // Fallback vers l'onglet actuel
            await this.openInCurrentTab(connectionData);
        }
    }

    showConnectionViewer(connectionData) {
        const connectionForm = this.container.querySelector('#connectionForm');
        const connectionViewer = this.container.querySelector('#connectionViewer');
        const viewerContent = this.container.querySelector('#viewerContent');
        const connectionInfo = this.container.querySelector('#connectionInfo');

        connectionForm.style.display = 'none';
        connectionViewer.style.display = 'block';

        connectionInfo.textContent = `${connectionData.connection_type.toUpperCase()} - ${connectionData.machine_ip}`;

        // Charger le viewer approprié
        if (connectionData.connection_type === 'vnc') {
            this.loadVNCViewer(viewerContent, connectionData);
        } else {
            this.loadRDPViewer(viewerContent, connectionData);
        }
    }

    showActiveSession(connectionData, location) {
        const activeSessions = this.container.querySelector('#activeSessions');
        const sessionsList = this.container.querySelector('#sessionsList');

        activeSessions.style.display = 'block';

        const sessionItem = document.createElement('div');
        sessionItem.className = 'session-item';
        sessionItem.innerHTML = `
            <div class="session-info">
                <strong>${connectionData.connection_type.toUpperCase()}</strong>
                <span>${connectionData.machine_ip}</span>
                <small>${location}</small>
            </div>
            <button class="btn btn-sm btn-outline-danger close-session-btn" data-session-id="${connectionData.session_id}">
                <i class="fas fa-times"></i>
            </button>
        `;

        sessionItem.querySelector('.close-session-btn').addEventListener('click', () => {
            this.closeSession(connectionData.session_id);
            sessionItem.remove();
        });

        sessionsList.appendChild(sessionItem);
    }

    loadVNCViewer(container, connectionData) {
        // Utiliser le composant VNCViewer existant
        container.innerHTML = '<div id="vncViewer"></div>';
        
        if (window.VNCViewer) {
            new window.VNCViewer('vncViewer', {
                websocketUrl: connectionData.websocket_url,
                password: connectionData.password || ''
            });
        }
    }

    loadRDPViewer(container, connectionData) {
        // Utiliser le composant RDPViewer existant
        container.innerHTML = '<div id="rdpViewer"></div>';
        
        if (window.RDPViewer) {
            new window.RDPViewer('rdpViewer', {
                websocketUrl: connectionData.websocket_url,
                username: connectionData.username || '',
                password: connectionData.password || ''
            });
        }
    }

    getFormData() {
        return {
            machine_id: parseInt(this.container.querySelector('#machineSelect').value),
            connection_type: this.container.querySelector('input[name="connectionType"]:checked').value,
            username: this.container.querySelector('#username').value,
            password: this.container.querySelector('#password').value,
            domain: this.container.querySelector('#domain').value,
            width: this.container.querySelector('#screenWidth').value === 'auto' ? 
                   window.screen.width : parseInt(this.container.querySelector('#screenWidth').value),
            height: this.container.querySelector('#screenHeight').value === 'auto' ? 
                    window.screen.height : parseInt(this.container.querySelector('#screenHeight').value),
            fullscreen: this.container.querySelector('#fullscreen').checked,
            openingMode: this.container.querySelector('input[name="openingMode"]:checked').value
        };
    }

    validateFormData(data) {
        if (!data.machine_id) {
            alert('Veuillez sélectionner une machine');
            return false;
        }
        if (!data.username) {
            alert('Veuillez entrer un nom d\'utilisateur');
            return false;
        }
        if (!data.password) {
            alert('Veuillez entrer un mot de passe');
            return false;
        }
        return true;
    }

    setConnectionStatus(status, message) {
        const statusIndicator = this.container.querySelector('.status-indicator');
        const statusText = this.container.querySelector('.status-text');
        
        statusIndicator.className = `status-indicator ${status}`;
        statusText.textContent = message;
    }

    async disconnect() {
        if (this.currentConnection) {
            try {
                await fetch(`/api/remote-access/disconnect/${this.currentConnection.session_id}`, {
                    method: 'POST'
                });
            } catch (error) {
                console.error('Erreur lors de la déconnexion:', error);
            }
        }

        // Fermer toutes les sessions multi-écrans
        this.multiScreenManager.closeAllSessions();

        // Réinitialiser l'interface
        this.resetInterface();
    }

    async closeSession(sessionId) {
        try {
            await fetch(`/api/remote-access/disconnect/${sessionId}`, {
                method: 'POST'
            });
            
            this.multiScreenManager.closeSession(sessionId);
        } catch (error) {
            console.error('Erreur lors de la fermeture de session:', error);
        }
    }

    resetInterface() {
        const connectionForm = this.container.querySelector('#connectionForm');
        const connectionViewer = this.container.querySelector('#connectionViewer');
        const activeSessions = this.container.querySelector('#activeSessions');

        connectionForm.style.display = 'block';
        connectionViewer.style.display = 'none';
        activeSessions.style.display = 'none';

        this.setConnectionStatus('disconnected', 'Déconnecté');
        this.currentConnection = null;
        this.isConnected = false;
    }

    onSessionClosed(sessionId) {
        // Gérer la fermeture d'une session externe
        const sessionItem = this.container.querySelector(`[data-session-id="${sessionId}"]`)?.closest('.session-item');
        if (sessionItem) {
            sessionItem.remove();
        }
    }

    toggleFullscreen() {
        const viewerContent = this.container.querySelector('#viewerContent');
        if (document.fullscreenElement) {
            document.exitFullscreen();
        } else {
            viewerContent.requestFullscreen();
        }
    }
}

// Exporter la classe
window.RemoteDesktopEnhanced = RemoteDesktopEnhanced;

