import React, { useEffect, useRef, useState } from 'react';

const VNCViewer = ({ connection, onDisconnect }) => {
    const canvasRef = useRef(null);
    const rfbRef = useRef(null);
    const [status, setStatus] = useState('connecting');
    const [error, setError] = useState(null);

    useEffect(() => {
        initializeVNC();
        return () => {
            if (rfbRef.current) {
                rfbRef.current.disconnect();
            }
        };
    }, [connection]);

    const initializeVNC = async () => {
        try {
            // Dynamically import noVNC
            const { default: RFB } = await import('/novnc/core/rfb.js');
            
            const canvas = canvasRef.current;
            if (!canvas) return;

            // Parse WebSocket URL
            const wsUrl = connection.websocket_url.replace('ws://', 'ws://').replace('localhost', window.location.hostname);
            
            // Create RFB connection
            const rfb = new RFB(canvas, wsUrl, {
                credentials: {
                    username: connection.username,
                    password: connection.password
                }
            });

            // Set up event handlers
            rfb.addEventListener('connect', () => {
                setStatus('connected');
                setError(null);
                updateConnectionStatus('connected');
            });

            rfb.addEventListener('disconnect', (e) => {
                setStatus('disconnected');
                if (e.detail.clean) {
                    console.log('VNC disconnected cleanly');
                } else {
                    setError('Connexion interrompue de manière inattendue');
                }
                updateConnectionStatus('disconnected');
            });

            rfb.addEventListener('credentialsrequired', () => {
                setError('Identifiants requis');
                setStatus('error');
            });

            rfb.addEventListener('securityfailure', (e) => {
                setError(`Échec de sécurité: ${e.detail.reason}`);
                setStatus('error');
            });

            // Configure RFB options
            rfb.scaleViewport = true;
            rfb.resizeSession = true;
            rfb.showDotCursor = true;

            rfbRef.current = rfb;

        } catch (err) {
            console.error('Error initializing VNC:', err);
            setError(`Erreur d'initialisation: ${err.message}`);
            setStatus('error');
        }
    };

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

    const handleDisconnect = () => {
        if (rfbRef.current) {
            rfbRef.current.disconnect();
        }
        onDisconnect();
    };

    const handleFullscreen = () => {
        const canvas = canvasRef.current;
        if (canvas) {
            if (canvas.requestFullscreen) {
                canvas.requestFullscreen();
            } else if (canvas.webkitRequestFullscreen) {
                canvas.webkitRequestFullscreen();
            } else if (canvas.mozRequestFullScreen) {
                canvas.mozRequestFullScreen();
            }
        }
    };

    const sendCtrlAltDel = () => {
        if (rfbRef.current) {
            rfbRef.current.sendCtrlAltDel();
        }
    };

    const renderControls = () => (
        <div className="vnc-controls">
            <div className="status-indicator">
                <span className={`status-dot ${status}`}></span>
                <span className="status-text">
                    {status === 'connecting' && 'Connexion...'}
                    {status === 'connected' && 'Connecté'}
                    {status === 'disconnected' && 'Déconnecté'}
                    {status === 'error' && 'Erreur'}
                </span>
            </div>
            
            <div className="control-buttons">
                <button 
                    onClick={sendCtrlAltDel}
                    disabled={status !== 'connected'}
                    className="btn btn-sm"
                    title="Envoyer Ctrl+Alt+Del"
                >
                    Ctrl+Alt+Del
                </button>
                
                <button 
                    onClick={handleFullscreen}
                    disabled={status !== 'connected'}
                    className="btn btn-sm"
                    title="Plein écran"
                >
                    Plein écran
                </button>
                
                <button 
                    onClick={handleDisconnect}
                    className="btn btn-sm btn-danger"
                    title="Déconnecter"
                >
                    Déconnecter
                </button>
            </div>
        </div>
    );

    if (error) {
        return (
            <div className="vnc-viewer error">
                <div className="error-message">
                    <h4>Erreur de connexion VNC</h4>
                    <p>{error}</p>
                    <button onClick={onDisconnect} className="btn btn-primary">
                        Fermer
                    </button>
                </div>
            </div>
        );
    }

    return (
        <div className="vnc-viewer">
            {renderControls()}
            <div className="vnc-canvas-container">
                <canvas
                    ref={canvasRef}
                    className="vnc-canvas"
                    style={{
                        width: '100%',
                        height: '600px',
                        border: '1px solid #ccc',
                        backgroundColor: '#000'
                    }}
                />
                {status === 'connecting' && (
                    <div className="connecting-overlay">
                        <div className="spinner"></div>
                        <p>Connexion au serveur VNC...</p>
                    </div>
                )}
            </div>
        </div>
    );
};

export default VNCViewer;

