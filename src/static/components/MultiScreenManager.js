/**
 * Gestionnaire pour le support multi-écrans
 */
class MultiScreenManager {
    constructor() {
        this.screens = [];
        this.activeConnections = new Map();
        this.isSupported = this.checkMultiScreenSupport();
    }

    /**
     * Vérifie si le support multi-écrans est disponible
     */
    checkMultiScreenSupport() {
        return 'getScreenDetails' in window || 'screen' in window;
    }

    /**
     * Détecte les écrans disponibles
     */
    async detectScreens() {
        try {
            if ('getScreenDetails' in window) {
                // API moderne Screen Details (Chrome 100+)
                const screenDetails = await window.getScreenDetails();
                this.screens = screenDetails.screens.map((screen, index) => ({
                    id: `screen_${index}`,
                    label: screen.label || `Écran ${index + 1}`,
                    width: screen.width,
                    height: screen.height,
                    availWidth: screen.availWidth,
                    availHeight: screen.availHeight,
                    left: screen.left,
                    top: screen.top,
                    isPrimary: screen.isPrimary,
                    isInternal: screen.isInternal,
                    devicePixelRatio: screen.devicePixelRatio
                }));
            } else {
                // Fallback pour les navigateurs plus anciens
                this.screens = [{
                    id: 'screen_0',
                    label: 'Écran Principal',
                    width: window.screen.width,
                    height: window.screen.height,
                    availWidth: window.screen.availWidth,
                    availHeight: window.screen.availHeight,
                    left: 0,
                    top: 0,
                    isPrimary: true,
                    isInternal: true,
                    devicePixelRatio: window.devicePixelRatio || 1
                }];
            }

            console.log('Écrans détectés:', this.screens);
            return this.screens;
        } catch (error) {
            console.error('Erreur lors de la détection des écrans:', error);
            return this.screens;
        }
    }

    /**
     * Crée l'interface de sélection d'écran
     */
    createScreenSelector(onScreenSelect) {
        const container = document.createElement('div');
        container.className = 'screen-selector';
        container.innerHTML = `
            <div class="screen-selector-header">
                <h3>Sélectionner un écran</h3>
                <p>Choisissez l'écran sur lequel ouvrir la session distante</p>
            </div>
            <div class="screen-list" id="screenList">
                <!-- Les écrans seront ajoutés ici -->
            </div>
            <div class="screen-selector-actions">
                <button id="cancelScreenSelection" class="btn btn-secondary">Annuler</button>
                <button id="openOnAllScreens" class="btn btn-primary">Ouvrir sur tous les écrans</button>
            </div>
        `;

        const screenList = container.querySelector('#screenList');
        
        this.screens.forEach((screen, index) => {
            const screenItem = document.createElement('div');
            screenItem.className = 'screen-item';
            screenItem.innerHTML = `
                <div class="screen-preview">
                    <div class="screen-icon">
                        <i class="fas fa-desktop"></i>
                    </div>
                    <div class="screen-info">
                        <h4>${screen.label}</h4>
                        <p>${screen.width} × ${screen.height}</p>
                        ${screen.isPrimary ? '<span class="primary-badge">Principal</span>' : ''}
                    </div>
                </div>
                <button class="btn btn-outline-primary select-screen-btn" data-screen-id="${screen.id}">
                    Sélectionner
                </button>
            `;
            screenList.appendChild(screenItem);
        });

        // Gestionnaires d'événements
        container.addEventListener('click', (e) => {
            if (e.target.classList.contains('select-screen-btn')) {
                const screenId = e.target.dataset.screenId;
                const selectedScreen = this.screens.find(s => s.id === screenId);
                onScreenSelect([selectedScreen]);
            } else if (e.target.id === 'openOnAllScreens') {
                onScreenSelect(this.screens);
            } else if (e.target.id === 'cancelScreenSelection') {
                onScreenSelect(null);
            }
        });

        return container;
    }

    /**
     * Ouvre une session sur un écran spécifique
     */
    async openSessionOnScreen(sessionData, screen, isNewTab = true) {
        try {
            const url = this.buildSessionUrl(sessionData);
            
            if (isNewTab) {
                // Calculer la position et la taille de la fenêtre
                const windowFeatures = this.calculateWindowFeatures(screen);
                
                // Ouvrir dans un nouvel onglet/fenêtre
                const newWindow = window.open(url, `remote_session_${sessionData.session_id}`, windowFeatures);
                
                if (newWindow) {
                    // Stocker la référence de la fenêtre
                    this.activeConnections.set(sessionData.session_id, {
                        window: newWindow,
                        screen: screen,
                        sessionData: sessionData
                    });

                    // Surveiller la fermeture de la fenêtre
                    const checkClosed = setInterval(() => {
                        if (newWindow.closed) {
                            clearInterval(checkClosed);
                            this.activeConnections.delete(sessionData.session_id);
                            this.notifySessionClosed(sessionData.session_id);
                        }
                    }, 1000);

                    return newWindow;
                } else {
                    throw new Error('Impossible d\'ouvrir la nouvelle fenêtre (popup bloqué?)');
                }
            } else {
                // Rediriger dans l'onglet actuel
                window.location.href = url;
                return window;
            }
        } catch (error) {
            console.error('Erreur lors de l\'ouverture de la session:', error);
            throw error;
        }
    }

    /**
     * Construit l'URL de session avec les paramètres nécessaires
     */
    buildSessionUrl(sessionData) {
        const baseUrl = window.location.origin;
        const params = new URLSearchParams({
            session_id: sessionData.session_id,
            connection_type: sessionData.connection_type,
            machine_id: sessionData.machine_id,
            fullscreen: 'true',
            standalone: 'true'
        });

        if (sessionData.access_token) {
            params.append('token', sessionData.access_token);
        }

        return `${baseUrl}/remote-session?${params.toString()}`;
    }

    /**
     * Calcule les caractéristiques de fenêtre pour un écran
     */
    calculateWindowFeatures(screen) {
        const features = [
            `width=${screen.availWidth}`,
            `height=${screen.availHeight}`,
            `left=${screen.left}`,
            `top=${screen.top}`,
            'toolbar=no',
            'menubar=no',
            'scrollbars=no',
            'resizable=yes',
            'location=no',
            'directories=no',
            'status=no'
        ];

        return features.join(',');
    }

    /**
     * Ouvre des sessions sur plusieurs écrans
     */
    async openSessionOnMultipleScreens(sessionData, screens) {
        const promises = screens.map(async (screen, index) => {
            // Pour les écrans supplémentaires, créer des sessions dérivées
            const derivedSessionData = {
                ...sessionData,
                session_id: `${sessionData.session_id}_screen_${index}`,
                screen_index: index
            };

            return this.openSessionOnScreen(derivedSessionData, screen, true);
        });

        try {
            const windows = await Promise.all(promises);
            console.log(`Sessions ouvertes sur ${windows.length} écrans`);
            return windows;
        } catch (error) {
            console.error('Erreur lors de l\'ouverture multi-écrans:', error);
            throw error;
        }
    }

    /**
     * Ferme toutes les sessions actives
     */
    closeAllSessions() {
        this.activeConnections.forEach((connection, sessionId) => {
            if (connection.window && !connection.window.closed) {
                connection.window.close();
            }
        });
        this.activeConnections.clear();
    }

    /**
     * Ferme une session spécifique
     */
    closeSession(sessionId) {
        const connection = this.activeConnections.get(sessionId);
        if (connection && connection.window && !connection.window.closed) {
            connection.window.close();
        }
        this.activeConnections.delete(sessionId);
    }

    /**
     * Notifie la fermeture d'une session
     */
    notifySessionClosed(sessionId) {
        // Émettre un événement personnalisé
        const event = new CustomEvent('sessionClosed', {
            detail: { sessionId }
        });
        window.dispatchEvent(event);

        // Appeler l'API pour nettoyer la session côté serveur
        this.cleanupServerSession(sessionId);
    }

    /**
     * Nettoie la session côté serveur
     */
    async cleanupServerSession(sessionId) {
        try {
            await fetch(`/api/remote-access/disconnect/${sessionId}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
        } catch (error) {
            console.error('Erreur lors du nettoyage de la session:', error);
        }
    }

    /**
     * Obtient les informations sur les sessions actives
     */
    getActiveSessions() {
        const sessions = [];
        this.activeConnections.forEach((connection, sessionId) => {
            sessions.push({
                sessionId,
                screen: connection.screen,
                isOpen: !connection.window.closed,
                sessionData: connection.sessionData
            });
        });
        return sessions;
    }

    /**
     * Vérifie si une session est active
     */
    isSessionActive(sessionId) {
        const connection = this.activeConnections.get(sessionId);
        return connection && connection.window && !connection.window.closed;
    }
}

// Styles CSS pour le sélecteur d'écran
const multiScreenStyles = `
.screen-selector {
    position: fixed;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    background: white;
    border-radius: 8px;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
    z-index: 10000;
    min-width: 400px;
    max-width: 600px;
}

.screen-selector-header {
    padding: 20px;
    border-bottom: 1px solid #e0e0e0;
    text-align: center;
}

.screen-selector-header h3 {
    margin: 0 0 8px 0;
    color: #333;
}

.screen-selector-header p {
    margin: 0;
    color: #666;
    font-size: 14px;
}

.screen-list {
    padding: 20px;
    max-height: 400px;
    overflow-y: auto;
}

.screen-item {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 15px;
    border: 1px solid #e0e0e0;
    border-radius: 6px;
    margin-bottom: 10px;
    transition: all 0.2s ease;
}

.screen-item:hover {
    border-color: #007bff;
    background-color: #f8f9fa;
}

.screen-preview {
    display: flex;
    align-items: center;
}

.screen-icon {
    margin-right: 15px;
    font-size: 24px;
    color: #007bff;
}

.screen-info h4 {
    margin: 0 0 4px 0;
    font-size: 16px;
    color: #333;
}

.screen-info p {
    margin: 0;
    font-size: 14px;
    color: #666;
}

.primary-badge {
    display: inline-block;
    background: #28a745;
    color: white;
    padding: 2px 8px;
    border-radius: 12px;
    font-size: 12px;
    margin-top: 4px;
}

.screen-selector-actions {
    padding: 20px;
    border-top: 1px solid #e0e0e0;
    display: flex;
    justify-content: space-between;
}

.btn {
    padding: 8px 16px;
    border: none;
    border-radius: 4px;
    cursor: pointer;
    font-size: 14px;
    transition: all 0.2s ease;
}

.btn-primary {
    background: #007bff;
    color: white;
}

.btn-primary:hover {
    background: #0056b3;
}

.btn-secondary {
    background: #6c757d;
    color: white;
}

.btn-secondary:hover {
    background: #545b62;
}

.btn-outline-primary {
    background: transparent;
    color: #007bff;
    border: 1px solid #007bff;
}

.btn-outline-primary:hover {
    background: #007bff;
    color: white;
}
`;

// Injecter les styles
if (!document.getElementById('multi-screen-styles')) {
    const styleSheet = document.createElement('style');
    styleSheet.id = 'multi-screen-styles';
    styleSheet.textContent = multiScreenStyles;
    document.head.appendChild(styleSheet);
}

// Exporter la classe
window.MultiScreenManager = MultiScreenManager;

