from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import json

db = SQLAlchemy()

class Lab(db.Model):
    __tablename__ = 'labs'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    provider = db.Column(db.String(50), nullable=False)  # 'vps', 'local'
    provider_config = db.Column(db.Text)  # JSON config for provider
    status = db.Column(db.String(20), default='stopped')  # stopped, running, deploying, error
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relations
    machines = db.relationship('Machine', backref='lab', lazy=True, cascade='all, delete-orphan')
    snapshots = db.relationship('Snapshot', backref='lab', lazy=True, cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'provider': self.provider,
            'provider_config': json.loads(self.provider_config) if self.provider_config else {},
            'status': self.status,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'machines': [machine.to_dict() for machine in self.machines],
            'snapshots': [snapshot.to_dict() for snapshot in self.snapshots]
        }

class Machine(db.Model):
    __tablename__ = 'machines'
    
    id = db.Column(db.Integer, primary_key=True)
    lab_id = db.Column(db.Integer, db.ForeignKey('labs.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    os = db.Column(db.String(50), nullable=False)
    cpu = db.Column(db.Integer, default=2)
    ram = db.Column(db.Integer, default=4)  # GB
    storage = db.Column(db.Integer, default=20)  # GB
    ip_address = db.Column(db.String(15))
    status = db.Column(db.String(20), default='stopped')
    role = db.Column(db.String(50))  # master, worker, database, web, etc.
    software_config = db.Column(db.Text)  # JSON list of software to install
    custom_playbooks = db.Column(db.Text)  # JSON list of custom playbook IDs
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'lab_id': self.lab_id,
            'name': self.name,
            'os': self.os,
            'cpu': self.cpu,
            'ram': self.ram,
            'storage': self.storage,
            'ip_address': self.ip_address,
            'status': self.status,
            'role': self.role,
            'software_config': json.loads(self.software_config) if self.software_config else [],
            'custom_playbooks': json.loads(self.custom_playbooks) if self.custom_playbooks else [],
            'created_at': self.created_at.isoformat()
        }

class Snapshot(db.Model):
    __tablename__ = 'snapshots'
    
    id = db.Column(db.Integer, primary_key=True)
    lab_id = db.Column(db.Integer, db.ForeignKey('labs.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    snapshot_data = db.Column(db.Text)  # JSON with snapshot metadata
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'lab_id': self.lab_id,
            'name': self.name,
            'description': self.description,
            'snapshot_data': json.loads(self.snapshot_data) if self.snapshot_data else {},
            'created_at': self.created_at.isoformat()
        }

class CustomPlaybook(db.Model):
    __tablename__ = 'custom_playbooks'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    content = db.Column(db.Text, nullable=False)  # YAML content
    tags = db.Column(db.String(200))  # Comma-separated tags
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'content': self.content,
            'tags': self.tags.split(',') if self.tags else [],
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

class DeploymentLog(db.Model):
    __tablename__ = 'deployment_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    lab_id = db.Column(db.Integer, db.ForeignKey('labs.id'), nullable=False)
    operation = db.Column(db.String(50), nullable=False)  # deploy, destroy, start, stop
    status = db.Column(db.String(20), nullable=False)  # running, success, error
    logs = db.Column(db.Text)
    started_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime)
    
    def to_dict(self):
        return {
            'id': self.id,
            'lab_id': self.lab_id,
            'operation': self.operation,
            'status': self.status,
            'logs': self.logs,
            'started_at': self.started_at.isoformat(),
            'completed_at': self.completed_at.isoformat() if self.completed_at else None
        }

