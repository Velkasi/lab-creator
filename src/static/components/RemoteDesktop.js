import React, { useState, useEffect, useRef } from 'react';
import VNCViewer from './VNCViewer';
import RDPViewer from './RDPViewer';

const RemoteDesktop = ({ machineId, onClose }) => {
    const [connectionInfo, setConnectionInfo] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [connectionType, setConnectionType] = useState('vnc');
    const [credentials, setCredentials] = useState({ username: '', password: '' });
    const [showCredentials, setShowCredentials] = useState(false);
    const [connection, setConnection] = useState(null);

    useEffect(() => {
        fetchConnectionInfo();
    }, [machineId]);

    const fetchConnectionInfo = async () => {
        try {
            setLoading(true);
            const response = await fetch(`/api/remote-access/info/${machineId}`);
            
            if (!response.ok) {
                throw new Error('Failed to fetch connection info');
            }
            
            const data = await response.json();
            setConnectionInfo(data);
            
            // Set default connection type
            if (data.available_types && data.available_types.length > 0) {
                setConnectionType(data.available_types[0]);
            }
            
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    const handleConnect = async () => {
        try {
            setLoading(true);
            setError(null);

            // Create connection
            const response = await fetch('/api/remote-access/connect', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    machine_id: machineId,
                    connection_type: connectionType,
                    username: credentials.username,
                    password: credentials.password,
                }),
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || 'Failed to create connection');
            }

            const connectionData = await response.json();
            setConnection(connectionData);
            setShowCredentials(false);

        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    const handleDisconnect = async () => {
        if (connection) {
            try {
                await fetch(`/api/remote-access/disconnect/${connection.session_id}`, {
                    method: 'POST',
                });
            } catch (err) {
                console.error('Error disconnecting:', err);
            }
            setConnection(null);
        }
    };

    const renderConnectionForm = () => (
        <div className="connection-form">
            <h3>Connexion à {connectionInfo.machine_name}</h3>
            
            <div className="form-group">
                <label>Type de connexion:</label>
                <select 
                    value={connectionType} 
                    onChange={(e) => setConnectionType(e.target.value)}
                    disabled={loading}
                >
                    {connectionInfo.available_types.map(type => (
                        <option key={type} value={type}>
                            {type.toUpperCase()}
                        </option>
                    ))}
                </select>
            </div>

            {showCredentials && (
                <>
                    <div className="form-group">
                        <label>Nom d'utilisateur:</label>
                        <input
                            type="text"
                            value={credentials.username}
                            onChange={(e) => setCredentials({...credentials, username: e.target.value})}
                            disabled={loading}
                        />
                    </div>
                    
                    <div className="form-group">
                        <label>Mot de passe:</label>
                        <input
                            type="password"
                            value={credentials.password}
                            onChange={(e) => setCredentials({...credentials, password: e.target.value})}
                            disabled={loading}
                        />
                    </div>
                </>
            )}

            <div className="form-actions">
                {!showCredentials ? (
                    <button 
                        onClick={() => setShowCredentials(true)}
                        disabled={loading}
                        className="btn btn-primary"
                    >
                        Configurer les identifiants
                    </button>
                ) : (
                    <>
                        <button 
                            onClick={handleConnect}
                            disabled={loading || !credentials.username}
                            className="btn btn-success"
                        >
                            {loading ? 'Connexion...' : 'Se connecter'}
                        </button>
                        <button 
                            onClick={() => setShowCredentials(false)}
                            disabled={loading}
                            className="btn btn-secondary"
                        >
                            Annuler
                        </button>
                    </>
                )}
            </div>
        </div>
    );

    const renderViewer = () => {
        if (!connection) return null;

        if (connectionType === 'vnc') {
            return (
                <VNCViewer
                    connection={connection}
                    onDisconnect={handleDisconnect}
                />
            );
        } else if (connectionType === 'rdp') {
            return (
                <RDPViewer
                    connection={connection}
                    onDisconnect={handleDisconnect}
                />
            );
        }

        return <div>Type de connexion non supporté</div>;
    };

    if (loading && !connection) {
        return (
            <div className="remote-desktop-modal">
                <div className="modal-content">
                    <div className="modal-header">
                        <h2>Accès distant</h2>
                        <button onClick={onClose} className="close-btn">&times;</button>
                    </div>
                    <div className="modal-body">
                        <div className="loading">Chargement...</div>
                    </div>
                </div>
            </div>
        );
    }

    if (error) {
        return (
            <div className="remote-desktop-modal">
                <div className="modal-content">
                    <div className="modal-header">
                        <h2>Erreur</h2>
                        <button onClick={onClose} className="close-btn">&times;</button>
                    </div>
                    <div className="modal-body">
                        <div className="error">
                            <p>Erreur: {error}</p>
                            <button onClick={fetchConnectionInfo} className="btn btn-primary">
                                Réessayer
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        );
    }

    return (
        <div className="remote-desktop-modal">
            <div className="modal-content">
                <div className="modal-header">
                    <h2>Accès distant - {connectionInfo?.machine_name}</h2>
                    <button onClick={onClose} className="close-btn">&times;</button>
                </div>
                <div className="modal-body">
                    {connection ? renderViewer() : renderConnectionForm()}
                </div>
            </div>
        </div>
    );
};

export default RemoteDesktop;

