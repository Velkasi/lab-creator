from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import json
from src.models.lab import db

class RemoteConnection(db.Model):
    __tablename__ = 'remote_connections'
    
    id = db.Column(db.Integer, primary_key=True)
    machine_id = db.Column(db.Integer, db.ForeignKey('machines.id'), nullable=False)
    connection_type = db.Column(db.String(10), nullable=False)  # 'vnc' or 'rdp'
    port = db.Column(db.Integer, nullable=False)
    username = db.Column(db.String(100))
    password = db.Column(db.String(255))  # Should be encrypted in production
    session_id = db.Column(db.String(100), unique=True)
    status = db.Column(db.String(20), default='disconnected')  # connected, disconnected, error
    connection_metadata = db.Column(db.Text)  # Champ pour stocker des métadonnées supplémentaires (renommé)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_activity = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relation
    machine = db.relationship('Machine', backref='remote_connections')
    
    def to_dict(self):
        return {
            'id': self.id,
            'machine_id': self.machine_id,
            'connection_type': self.connection_type,
            'port': self.port,
            'username': self.username,
            'session_id': self.session_id,
            'status': self.status,
            'created_at': self.created_at.isoformat(),
            'last_activity': self.last_activity.isoformat()
        }

