from flask import Blueprint, request, jsonify
from src.services.remote_access_service import RemoteAccessService
from src.models.lab import Machine
import logging

logger = logging.getLogger(__name__)

remote_access_bp = Blueprint('remote_access', __name__)

@remote_access_bp.route('/remote-access/info/<int:machine_id>', methods=['GET'])
def get_connection_info(machine_id):
    """Get connection information for a machine"""
    try:
        info = RemoteAccessService.get_connection_info(machine_id)
        if not info:
            return jsonify({'error': 'Machine not found'}), 404
        
        return jsonify(info), 200
        
    except Exception as e:
        logger.error(f"Error getting connection info: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@remote_access_bp.route('/remote-access/connect', methods=['POST'])
def create_connection():
    """Create a new remote connection"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['machine_id', 'connection_type']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        machine_id = data['machine_id']
        connection_type = data['connection_type']
        username = data.get('username')
        password = data.get('password')
        
        # Validate connection type
        if connection_type not in ['vnc', 'rdp']:
            return jsonify({'error': 'Invalid connection type. Must be vnc or rdp'}), 400
        
        # Create connection
        connection = RemoteAccessService.create_connection(
            machine_id=machine_id,
            connection_type=connection_type,
            username=username,
            password=password
        )
        
        if not connection:
            return jsonify({'error': 'Failed to create connection'}), 500
        
        # Return connection details
        response_data = connection.to_dict()
        response_data['websocket_url'] = f"ws://localhost:8765/{connection_type}/{connection.machine.lab_id}/{machine_id}"
        
        return jsonify(response_data), 201
        
    except Exception as e:
        logger.error(f"Error creating connection: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@remote_access_bp.route('/remote-access/status/<session_id>', methods=['GET'])
def get_connection_status(session_id):
    """Get connection status"""
    try:
        connection = RemoteAccessService.get_connection(session_id)
        if not connection:
            return jsonify({'error': 'Connection not found'}), 404
        
        return jsonify(connection.to_dict()), 200
        
    except Exception as e:
        logger.error(f"Error getting connection status: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@remote_access_bp.route('/remote-access/status/<session_id>', methods=['PUT'])
def update_connection_status(session_id):
    """Update connection status"""
    try:
        data = request.get_json()
        
        if 'status' not in data:
            return jsonify({'error': 'Missing status field'}), 400
        
        status = data['status']
        if status not in ['connected', 'disconnected', 'error']:
            return jsonify({'error': 'Invalid status'}), 400
        
        success = RemoteAccessService.update_connection_status(session_id, status)
        if not success:
            return jsonify({'error': 'Connection not found'}), 404
        
        return jsonify({'message': 'Status updated successfully'}), 200
        
    except Exception as e:
        logger.error(f"Error updating connection status: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@remote_access_bp.route('/remote-access/disconnect/<session_id>', methods=['POST'])
def disconnect_connection(session_id):
    """Disconnect a remote connection"""
    try:
        success = RemoteAccessService.update_connection_status(session_id, 'disconnected')
        if not success:
            return jsonify({'error': 'Connection not found'}), 404
        
        return jsonify({'message': 'Connection disconnected successfully'}), 200
        
    except Exception as e:
        logger.error(f"Error disconnecting connection: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@remote_access_bp.route('/remote-access/connections/<int:machine_id>', methods=['GET'])
def get_machine_connections(machine_id):
    """Get all connections for a machine"""
    try:
        connections = RemoteAccessService.get_machine_connections(machine_id)
        return jsonify([conn.to_dict() for conn in connections]), 200
        
    except Exception as e:
        logger.error(f"Error getting machine connections: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@remote_access_bp.route('/remote-access/cleanup', methods=['POST'])
def cleanup_connections():
    """Clean up inactive connections"""
    try:
        data = request.get_json() or {}
        timeout_minutes = data.get('timeout_minutes', 30)
        
        count = RemoteAccessService.cleanup_inactive_connections(timeout_minutes)
        return jsonify({'message': f'Cleaned up {count} inactive connections'}), 200
        
    except Exception as e:
        logger.error(f"Error cleaning up connections: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@remote_access_bp.route('/remote-access/validate-credentials', methods=['POST'])
def validate_credentials():
    """Validate connection credentials"""
    try:
        data = request.get_json()
        
        required_fields = ['machine_id', 'username', 'password']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        machine_id = data['machine_id']
        username = data['username']
        password = data['password']
        
        is_valid = RemoteAccessService.validate_connection_credentials(
            machine_id, username, password
        )
        
        return jsonify({'valid': is_valid}), 200
        
    except Exception as e:
        logger.error(f"Error validating credentials: {e}")
        return jsonify({'error': 'Internal server error'}), 500

