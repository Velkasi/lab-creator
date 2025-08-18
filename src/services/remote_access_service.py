import uuid
import logging
from datetime import datetime
from typing import Optional, Dict, List
from src.models.lab import Machine, db
from src.models.remote_connection import RemoteConnection

logger = logging.getLogger(__name__)

class RemoteAccessService:
    """Service for managing remote desktop connections"""
    
    @staticmethod
    def create_connection(machine_id: int, connection_type: str, username: str = None, password: str = None) -> Optional[RemoteConnection]:
        """Create a new remote connection"""
        try:
            # Validate machine exists
            machine = Machine.query.get(machine_id)
            if not machine:
                logger.error(f"Machine {machine_id} not found")
                return None
            
            # Validate connection type
            if connection_type not in ['vnc', 'rdp']:
                logger.error(f"Invalid connection type: {connection_type}")
                return None
            
            # Determine port based on connection type
            port = 5901 if connection_type == 'vnc' else 3389
            
            # Generate unique session ID
            session_id = str(uuid.uuid4())
            
            # Create connection record
            connection = RemoteConnection(
                machine_id=machine_id,
                connection_type=connection_type,
                port=port,
                username=username,
                password=password,  # In production, this should be encrypted
                session_id=session_id,
                status='disconnected'
            )
            
            db.session.add(connection)
            db.session.commit()
            
            logger.info(f"Created {connection_type} connection {session_id} for machine {machine_id}")
            return connection
            
        except Exception as e:
            logger.error(f"Error creating connection: {e}")
            db.session.rollback()
            return None
    
    @staticmethod
    def get_connection(session_id: str) -> Optional[RemoteConnection]:
        """Get connection by session ID"""
        try:
            return RemoteConnection.query.filter_by(session_id=session_id).first()
        except Exception as e:
            logger.error(f"Error getting connection {session_id}: {e}")
            return None
    
    @staticmethod
    def update_connection_status(session_id: str, status: str) -> bool:
        """Update connection status"""
        try:
            connection = RemoteConnection.query.filter_by(session_id=session_id).first()
            if connection:
                connection.status = status
                connection.last_activity = datetime.utcnow()
                db.session.commit()
                return True
            return False
        except Exception as e:
            logger.error(f"Error updating connection status: {e}")
            db.session.rollback()
            return False
    
    @staticmethod
    def get_machine_connections(machine_id: int) -> List[RemoteConnection]:
        """Get all connections for a machine"""
        try:
            return RemoteConnection.query.filter_by(machine_id=machine_id).all()
        except Exception as e:
            logger.error(f"Error getting machine connections: {e}")
            return []
    
    @staticmethod
    def cleanup_inactive_connections(timeout_minutes: int = 30) -> int:
        """Clean up inactive connections"""
        try:
            from datetime import timedelta
            cutoff_time = datetime.utcnow() - timedelta(minutes=timeout_minutes)
            
            inactive_connections = RemoteConnection.query.filter(
                RemoteConnection.last_activity < cutoff_time,
                RemoteConnection.status != 'disconnected'
            ).all()
            
            count = 0
            for connection in inactive_connections:
                connection.status = 'disconnected'
                count += 1
            
            db.session.commit()
            logger.info(f"Cleaned up {count} inactive connections")
            return count
            
        except Exception as e:
            logger.error(f"Error cleaning up connections: {e}")
            db.session.rollback()
            return 0
    
    @staticmethod
    def delete_connection(session_id: str) -> bool:
        """Delete a connection"""
        try:
            connection = RemoteConnection.query.filter_by(session_id=session_id).first()
            if connection:
                db.session.delete(connection)
                db.session.commit()
                return True
            return False
        except Exception as e:
            logger.error(f"Error deleting connection: {e}")
            db.session.rollback()
            return False
    
    @staticmethod
    def get_connection_info(machine_id: int) -> Dict:
        """Get connection information for a machine"""
        try:
            machine = Machine.query.get(machine_id)
            if not machine:
                return {}
            
            # Determine available connection types based on OS
            available_types = []
            if machine.os.lower().startswith('windows'):
                available_types.append('rdp')
                available_types.append('vnc')  # If VNC server is installed
            else:
                available_types.append('vnc')
            
            return {
                'machine_id': machine_id,
                'machine_name': machine.name,
                'ip_address': machine.ip_address,
                'os': machine.os,
                'status': machine.status,
                'available_types': available_types,
                'active_connections': [conn.to_dict() for conn in machine.remote_connections if conn.status == 'connected']
            }
            
        except Exception as e:
            logger.error(f"Error getting connection info: {e}")
            return {}
    
    @staticmethod
    def validate_connection_credentials(machine_id: int, username: str, password: str) -> bool:
        """Validate connection credentials (placeholder implementation)"""
        # In a real implementation, this would validate against the actual machine
        # For now, we'll just check if the machine exists and is running
        try:
            machine = Machine.query.get(machine_id)
            return machine and machine.status == 'running'
        except Exception as e:
            logger.error(f"Error validating credentials: {e}")
            return False

