import uuid
import logging
from datetime import datetime
from typing import Optional, Dict, List
from src.models.remote_connection import RemoteConnection, db
from src.services.freerdp_service import freerdp_service

logger = logging.getLogger(__name__)

class EnhancedRemoteAccessService:
    """Service amélioré pour gérer l'accès distant aux machines virtuelles avec support FreeRDP"""
    
    @staticmethod
    def create_connection(machine_id: int, connection_type: str, username: str, 
                         password: str, width: int = 1024, height: int = 768,
                         domain: str = None) -> Dict:
        """
        Crée une nouvelle connexion distante
        
        Args:
            machine_id: ID de la machine cible
            connection_type: Type de connexion ('vnc' ou 'rdp')
            username: Nom d'utilisateur
            password: Mot de passe
            width: Largeur de l'écran
            height: Hauteur de l'écran
            domain: Domaine (pour RDP uniquement)
        
        Returns:
            Dict contenant les informations de connexion
        """
        try:
            # Générer un ID de session unique
            session_id = str(uuid.uuid4())
            
            # Récupérer les informations de la machine
            from src.models.lab import Machine
            machine = Machine.query.get(machine_id)
            if not machine:
                return {"success": False, "error": "Machine not found"}
            
            # Déterminer le port par défaut selon le type
            default_port = 3389 if connection_type == 'rdp' else 5901
            
            if connection_type == 'rdp':
                # Utiliser le service FreeRDP pour les connexions RDP
                try:
                    rdp_session_id, local_port = freerdp_service.create_rdp_session(
                        host=machine.ip_address,
                        port=default_port,
                        username=username,
                        password=password,
                        domain=domain,
                        width=width,
                        height=height
                    )
                    
                    # Créer l'enregistrement en base de données
                    connection = RemoteConnection(
                        machine_id=machine_id,
                        connection_type=connection_type,
                        port=local_port,
                        username=username,
                        password=password,  # En production, chiffrer le mot de passe
                        session_id=session_id,
                        status='connecting'
                    )
                    
                    # Ajouter l'ID de session RDP comme métadonnée
                    connection.connection_metadata = f"rdp_session_id:{rdp_session_id}"
                    
                    db.session.add(connection)
                    db.session.commit()
                    
                    return {
                        "success": True,
                        "session_id": session_id,
                        "rdp_session_id": rdp_session_id,
                        "connection_type": connection_type,
                        "websocket_url": f"ws://localhost:{local_port}",
                        "local_port": local_port,
                        "machine_ip": machine.ip_address,
                        "status": "connecting"
                    }
                    
                except Exception as e:
                    logger.error(f"Failed to create RDP session: {e}")
                    return {"success": False, "error": f"RDP connection failed: {str(e)}"}
            
            else:  # VNC
                # Utiliser l'ancienne logique pour VNC
                connection = RemoteConnection(
                    machine_id=machine_id,
                    connection_type=connection_type,
                    port=default_port,
                    username=username,
                    password=password,
                    session_id=session_id,
                    status='connecting'
                )
                
                db.session.add(connection)
                db.session.commit()
                
                return {
                    "success": True,
                    "session_id": session_id,
                    "connection_type": connection_type,
                    "websocket_url": f"ws://localhost:8765/vnc/{machine.lab_id}/{machine_id}",
                    "machine_ip": machine.ip_address,
                    "vnc_port": default_port,
                    "status": "connecting"
                }
                
        except Exception as e:
            logger.error(f"Error creating connection: {e}")
            return {"success": False, "error": str(e)}
    
    @staticmethod
    def get_connection_info(machine_id: int) -> Dict:
        """Récupère les informations de connexion pour une machine"""
        try:
            from src.models.lab import Machine
            machine = Machine.query.get(machine_id)
            if not machine:
                return {"success": False, "error": "Machine not found"}
            
            # Vérifier les connexions actives
            active_connections = RemoteConnection.query.filter_by(
                machine_id=machine_id,
                status='connected'
            ).all()
            
            # Déterminer les types de connexion disponibles
            available_types = []
            
            # VNC toujours disponible si la machine a une IP
            if machine.ip_address:
                available_types.append('vnc')
            
            # RDP disponible si FreeRDP est installé
            try:
                freerdp_service._find_freerdp_executable()
                available_types.append('rdp')
            except RuntimeError:
                logger.warning("FreeRDP not available, RDP connections disabled")
            
            return {
                "success": True,
                "machine_id": machine_id,
                "machine_name": machine.name,
                "machine_ip": machine.ip_address,
                "lab_id": machine.lab_id,
                "status": machine.status,
                "available_types": available_types,
                "active_connections": len(active_connections)
            }
            
        except Exception as e:
            logger.error(f"Error getting connection info: {e}")
            return {"success": False, "error": str(e)}
    
    @staticmethod
    def get_connection_status(session_id: str) -> Dict:
        """Récupère le statut d'une connexion"""
        try:
            connection = RemoteConnection.query.filter_by(session_id=session_id).first()
            if not connection:
                return {"success": False, "error": "Connection not found"}
            
            # Pour les connexions RDP, vérifier le statut via FreeRDP
            if connection.connection_type == 'rdp' and connection.connection_metadata:
                rdp_session_id = connection.connection_metadata.split(':')[1] if ':' in connection.connection_metadata else None
                if rdp_session_id:
                    rdp_status = freerdp_service.get_session_status(rdp_session_id)
                    if rdp_status:
                        connection.status = rdp_status['status']
                        connection.last_activity = datetime.utcnow()
                        db.session.commit()
            
            return {
                "success": True,
                "session_id": session_id,
                "status": connection.status,
                "connection_type": connection.connection_type,
                "machine_id": connection.machine_id,
                "created_at": connection.created_at.isoformat(),
                "last_activity": connection.last_activity.isoformat() if connection.last_activity else None
            }
            
        except Exception as e:
            logger.error(f"Error getting connection status: {e}")
            return {"success": False, "error": str(e)}
    
    @staticmethod
    def update_connection_status(session_id: str, status: str) -> Dict:
        """Met à jour le statut d'une connexion"""
        try:
            connection = RemoteConnection.query.filter_by(session_id=session_id).first()
            if not connection:
                return {"success": False, "error": "Connection not found"}
            
            connection.status = status
            connection.last_activity = datetime.utcnow()
            db.session.commit()
            
            return {"success": True, "status": status}
            
        except Exception as e:
            logger.error(f"Error updating connection status: {e}")
            return {"success": False, "error": str(e)}
    
    @staticmethod
    def disconnect_session(session_id: str) -> Dict:
        """Déconnecte une session"""
        try:
            connection = RemoteConnection.query.filter_by(session_id=session_id).first()
            if not connection:
                return {"success": False, "error": "Connection not found"}
            
            # Pour les connexions RDP, terminer via FreeRDP
            if connection.connection_type == 'rdp' and connection.connection_metadata:
                rdp_session_id = connection.connection_metadata.split(':')[1] if ':' in connection.connection_metadata else None
                if rdp_session_id:
                    freerdp_service.terminate_session(rdp_session_id)
            
            # Marquer comme déconnecté
            connection.status = 'disconnected'
            connection.last_activity = datetime.utcnow()
            db.session.commit()
            
            return {"success": True, "message": "Session disconnected"}
            
        except Exception as e:
            logger.error(f"Error disconnecting session: {e}")
            return {"success": False, "error": str(e)}
    
    @staticmethod
    def list_connections(machine_id: int) -> Dict:
        """Liste les connexions pour une machine"""
        try:
            connections = RemoteConnection.query.filter_by(machine_id=machine_id).all()
            
            connection_list = []
            for conn in connections:
                connection_list.append({
                    "session_id": conn.session_id,
                    "connection_type": conn.connection_type,
                    "status": conn.status,
                    "username": conn.username,
                    "created_at": conn.created_at.isoformat(),
                    "last_activity": conn.last_activity.isoformat() if conn.last_activity else None
                })
            
            return {"success": True, "connections": connection_list}
            
        except Exception as e:
            logger.error(f"Error listing connections: {e}")
            return {"success": False, "error": str(e)}
    
    @staticmethod
    def cleanup_inactive_connections(timeout_minutes: int = 60) -> int:
        """Nettoie les connexions inactives"""
        try:
            from datetime import timedelta
            
            cutoff_time = datetime.utcnow() - timedelta(minutes=timeout_minutes)
            
            # Trouver les connexions inactives
            inactive_connections = RemoteConnection.query.filter(
                RemoteConnection.last_activity < cutoff_time,
                RemoteConnection.status.in_(['connecting', 'connected'])
            ).all()
            
            cleaned_count = 0
            for connection in inactive_connections:
                # Terminer les sessions RDP via FreeRDP
                if connection.connection_type == 'rdp' and connection.connection_metadata:
                    rdp_session_id = connection.connection_metadata.split(':')[1] if ':' in connection.connection_metadata else None
                    if rdp_session_id:
                        freerdp_service.terminate_session(rdp_session_id)
                
                connection.status = 'timeout'
                cleaned_count += 1
            
            # Nettoyer aussi les sessions FreeRDP orphelines
            freerdp_cleaned = freerdp_service.cleanup_inactive_sessions(timeout_minutes * 60)
            
            db.session.commit()
            
            logger.info(f"Cleaned up {cleaned_count} inactive connections and {freerdp_cleaned} FreeRDP sessions")
            return cleaned_count + freerdp_cleaned
            
        except Exception as e:
            logger.error(f"Error cleaning up connections: {e}")
            return 0
    
    @staticmethod
    def create_direct_access_url(machine_id: int, connection_type: str, 
                                username: str, password: str, domain: str = None) -> Dict:
        """
        Crée une URL d'accès direct pour ouvrir dans un nouvel onglet
        """
        try:
            # Créer une connexion temporaire
            connection_result = EnhancedRemoteAccessService.create_connection(
                machine_id, connection_type, username, password, domain=domain
            )
            
            if not connection_result.get("success"):
                return connection_result
            
            # Générer un token temporaire pour l'authentification
            import secrets
            access_token = secrets.token_urlsafe(32)
            
            # Stocker le token temporairement (en production, utiliser Redis ou une base de données)
            connection = RemoteConnection.query.filter_by(
                session_id=connection_result["session_id"]
            ).first()
            
            if connection:
                existing_metadata = connection.connection_metadata or ""
                connection.connection_metadata = f"{existing_metadata};access_token:{access_token}"
                db.session.commit()
            
            # Construire l'URL d'accès direct
            base_url = "http://localhost:5000"  # En production, utiliser l'URL réelle
            direct_url = f"{base_url}/remote-access/{connection_result['session_id']}?token={access_token}"
            
            return {
                "success": True,
                "direct_url": direct_url,
                "session_id": connection_result["session_id"],
                "access_token": access_token,
                "expires_in": 3600  # 1 heure
            }
            
        except Exception as e:
            logger.error(f"Error creating direct access URL: {e}")
            return {"success": False, "error": str(e)}
    
    @staticmethod
    def validate_access_token(session_id: str, token: str) -> bool:
        """Valide un token d'accès temporaire"""
        try:
            connection = RemoteConnection.query.filter_by(session_id=session_id).first()
            if not connection or not connection.connection_metadata:
                return False
            
            # Vérifier si le token est dans les métadonnées
            return f"access_token:{token}" in connection.connection_metadata
            
        except Exception as e:
            logger.error(f"Error validating access token: {e}")
            return False

