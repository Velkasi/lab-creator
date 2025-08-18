import React, { useState, useEffect } from 'react';

const RDPViewer = ({ connection, onDisconnect }) => {
    const [status, setStatus] = useState('not_implemented');

    useEffect(() => {
        // Update connection status
        updateConnectionStatus('error');
    }, [connection]);

    const updateConnectionStatus = async (status) => {
        try {
            await fetch(`/api/remote-access/status/${connection.session_id}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ status }),
            });
        } catch (err) {
            console.error('Error updating connection status:', err);
        }
    };

    return (
        <div className="rdp-viewer">
            <div className="rdp-controls">
                <div className="status-indicator">
                    <span className="status-dot error"></span>
                    <span className="status-text">Non implémenté</span>
                </div>
                
                <div className="control-buttons">
                    <button 
                        onClick={onDisconnect}
                        className="btn btn-sm btn-danger"
                        title="Fermer"
                    >
                        Fermer
                    </button>
                </div>
            </div>
            
            <div className="rdp-content">
                <div className="not-implemented-message">
                    <h4>Support RDP en cours de développement</h4>
                    <p>
                        Le support RDP n'est pas encore implémenté dans cette version.
                        Seules les connexions VNC sont actuellement supportées.
                    </p>
                    <div className="implementation-notes">
                        <h5>Implémentation future:</h5>
                        <ul>
                            <li>Intégration avec FreeRDP ou équivalent</li>
                            <li>Proxy WebSocket pour RDP</li>
                            <li>Interface HTML5 pour RDP</li>
                            <li>Support des fonctionnalités avancées RDP</li>
                        </ul>
                    </div>
                    <p>
                        <strong>Recommandation:</strong> Utilisez VNC pour l'accès distant 
                        ou installez un serveur VNC sur vos machines Windows.
                    </p>
                </div>
            </div>
        </div>
    );
};

export default RDPViewer;

