import subprocess
import threading
import socket
import json
import logging
import uuid
import time
from typing import Dict, Optional, Tuple
import os
import signal

logger = logging.getLogger(__name__)

class FreeRDPService:
    """Service pour gérer les connexions RDP via FreeRDP"""
    
    def __init__(self):
        self.active_sessions: Dict[str, dict] = {}
        self.freerdp_path = self._find_freerdp_executable()
        
    def _find_freerdp_executable(self) -> str:
        """Trouve l'exécutable FreeRDP sur le système"""
        possible_paths = [
            '/usr/bin/xfreerdp',
            '/usr/local/bin/xfreerdp',
            '/opt/freerdp/bin/xfreerdp',
            'xfreerdp'  # Dans le PATH
        ]
        
        for path in possible_paths:
            if os.path.exists(path) or self._command_exists(path):
                return path
                
        raise RuntimeError("FreeRDP executable not found. Please install FreeRDP.")
    
    def _command_exists(self, command: str) -> bool:
        """Vérifie si une commande existe dans le PATH"""
        try:
            subprocess.run(['which', command], capture_output=True, check=True)
            return True
        except subprocess.CalledProcessError:
            return False
    
    def create_rdp_session(self, host: str, port: int = 3389, username: str = None, 
                          password: str = None, domain: str = None, 
                          width: int = 1024, height: int = 768) -> Tuple[str, int]:
        """
        Crée une session RDP et retourne l'ID de session et le port local
        """
        session_id = str(uuid.uuid4())
        local_port = self._get_free_port()
        
        try:
            # Créer un socket pour la communication avec FreeRDP
            server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server_socket.bind(('localhost', local_port))
            server_socket.listen(1)
            
            # Construire la commande FreeRDP
            cmd = self._build_freerdp_command(
                host, port, username, password, domain, width, height, local_port
            )
            
            # Démarrer le processus FreeRDP
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                preexec_fn=os.setsid  # Créer un nouveau groupe de processus
            )
            
            # Stocker les informations de session
            self.active_sessions[session_id] = {
                'process': process,
                'socket': server_socket,
                'local_port': local_port,
                'host': host,
                'port': port,
                'username': username,
                'created_at': time.time(),
                'status': 'connecting'
            }
            
            # Démarrer un thread pour gérer la connexion
            thread = threading.Thread(
                target=self._handle_rdp_connection,
                args=(session_id, server_socket),
                daemon=True
            )
            thread.start()
            
            logger.info(f"Created RDP session {session_id} for {host}:{port} on local port {local_port}")
            return session_id, local_port
            
        except Exception as e:
            logger.error(f"Failed to create RDP session: {e}")
            if 'server_socket' in locals():
                server_socket.close()
            raise
    
    def _build_freerdp_command(self, host: str, port: int, username: str, 
                              password: str, domain: str, width: int, 
                              height: int, local_port: int) -> list:
        """Construit la commande FreeRDP"""
        cmd = [
            self.freerdp_path,
            f'/v:{host}:{port}',
            f'/size:{width}x{height}',
            '/bpp:32',
            '/compression',
            '/clipboard',
            '/audio-mode:0',  # Pas d'audio pour simplifier
            '/cert:ignore',   # Ignorer les erreurs de certificat
            f'/port:{local_port}',  # Port pour la communication
        ]
        
        if username:
            cmd.append(f'/u:{username}')
        if password:
            cmd.append(f'/p:{password}')
        if domain:
            cmd.append(f'/d:{domain}')
            
        return cmd
    
    def _handle_rdp_connection(self, session_id: str, server_socket: socket.socket):
        """Gère la connexion RDP dans un thread séparé"""
        try:
            # Attendre une connexion WebSocket
            client_socket, addr = server_socket.accept()
            logger.info(f"WebSocket connected to RDP session {session_id}")
            
            session = self.active_sessions.get(session_id)
            if not session:
                client_socket.close()
                return
                
            session['status'] = 'connected'
            session['client_socket'] = client_socket
            
            # Gérer le transfert de données bidirectionnel
            self._handle_data_transfer(session_id, client_socket, session['process'])
            
        except Exception as e:
            logger.error(f"Error handling RDP connection {session_id}: {e}")
        finally:
            self._cleanup_session(session_id)
    
    def _handle_data_transfer(self, session_id: str, client_socket: socket.socket, 
                             process: subprocess.Popen):
        """Gère le transfert de données entre WebSocket et FreeRDP"""
        try:
            # Cette partie nécessiterait une implémentation plus complexe
            # pour interfacer correctement avec FreeRDP
            # Pour l'instant, on simule une connexion
            
            while process.poll() is None:  # Tant que le processus est actif
                try:
                    # Lire les données du client WebSocket
                    data = client_socket.recv(4096)
                    if not data:
                        break
                        
                    # Ici, on devrait envoyer les données à FreeRDP
                    # et récupérer la réponse pour la renvoyer au client
                    
                    # Pour l'instant, on envoie juste un message de test
                    response = b"RDP data simulation"
                    client_socket.send(response)
                    
                except socket.timeout:
                    continue
                except Exception as e:
                    logger.error(f"Data transfer error for session {session_id}: {e}")
                    break
                    
        except Exception as e:
            logger.error(f"Error in data transfer for session {session_id}: {e}")
    
    def _get_free_port(self) -> int:
        """Trouve un port libre pour la communication"""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('', 0))
            s.listen(1)
            port = s.getsockname()[1]
        return port
    
    def get_session_status(self, session_id: str) -> Optional[dict]:
        """Retourne le statut d'une session"""
        session = self.active_sessions.get(session_id)
        if not session:
            return None
            
        return {
            'session_id': session_id,
            'status': session['status'],
            'host': session['host'],
            'port': session['port'],
            'username': session['username'],
            'created_at': session['created_at'],
            'local_port': session['local_port']
        }
    
    def terminate_session(self, session_id: str) -> bool:
        """Termine une session RDP"""
        session = self.active_sessions.get(session_id)
        if not session:
            return False
            
        try:
            # Terminer le processus FreeRDP
            if session['process'].poll() is None:
                os.killpg(os.getpgid(session['process'].pid), signal.SIGTERM)
                
            self._cleanup_session(session_id)
            logger.info(f"Terminated RDP session {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error terminating session {session_id}: {e}")
            return False
    
    def _cleanup_session(self, session_id: str):
        """Nettoie les ressources d'une session"""
        session = self.active_sessions.get(session_id)
        if not session:
            return
            
        try:
            # Fermer le socket client
            if 'client_socket' in session:
                session['client_socket'].close()
                
            # Fermer le socket serveur
            if 'socket' in session:
                session['socket'].close()
                
            # Terminer le processus si nécessaire
            if session['process'].poll() is None:
                try:
                    os.killpg(os.getpgid(session['process'].pid), signal.SIGTERM)
                except:
                    pass
                    
        except Exception as e:
            logger.error(f"Error cleaning up session {session_id}: {e}")
        finally:
            # Supprimer de la liste des sessions actives
            if session_id in self.active_sessions:
                del self.active_sessions[session_id]
    
    def list_active_sessions(self) -> list:
        """Liste toutes les sessions actives"""
        return [
            self.get_session_status(session_id) 
            for session_id in self.active_sessions.keys()
        ]
    
    def cleanup_inactive_sessions(self, timeout_seconds: int = 3600):
        """Nettoie les sessions inactives"""
        current_time = time.time()
        inactive_sessions = []
        
        for session_id, session in self.active_sessions.items():
            if current_time - session['created_at'] > timeout_seconds:
                if session['process'].poll() is not None:  # Processus terminé
                    inactive_sessions.append(session_id)
                    
        for session_id in inactive_sessions:
            self._cleanup_session(session_id)
            
        return len(inactive_sessions)

# Instance globale du service
freerdp_service = FreeRDPService()

