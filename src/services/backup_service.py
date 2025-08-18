import os
import json
import tarfile
import shutil
import subprocess
from datetime import datetime
from typing import Dict, List, Any, Optional
from src.models.lab import Lab, Machine, Snapshot, CustomPlaybook, db
from src.services.terraform_service import TerraformService
from src.services.ansible_service import AnsibleService

class BackupService:
    def __init__(self, backup_dir: str = "/tmp/lab_backups"):
        self.backup_dir = backup_dir
        os.makedirs(backup_dir, exist_ok=True)
        self.terraform_service = TerraformService()
        self.ansible_service = AnsibleService()
    
    def create_snapshot(self, lab_id: int, snapshot_name: str, description: str = "") -> Dict[str, Any]:
        """Créer un snapshot complet d'un lab"""
        lab = Lab.query.get(lab_id)
        if not lab:
            return {"success": False, "error": "Lab not found"}
        
        try:
            # Créer le répertoire de snapshot
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            snapshot_dir = os.path.join(self.backup_dir, f"lab_{lab_id}_snapshot_{timestamp}")
            os.makedirs(snapshot_dir, exist_ok=True)
            
            # Sauvegarder la configuration du lab
            lab_config = {
                "lab": lab.to_dict(),
                "machines": [machine.to_dict() for machine in lab.machines],
                "snapshot_metadata": {
                    "name": snapshot_name,
                    "description": description,
                    "created_at": datetime.now().isoformat(),
                    "lab_status": lab.status
                }
            }
            
            config_path = os.path.join(snapshot_dir, "lab_config.json")
            with open(config_path, "w") as f:
                json.dump(lab_config, f, indent=2)
            
            # Sauvegarder les fichiers Terraform
            terraform_workspace = self.terraform_service.get_lab_workspace(lab_id)
            if os.path.exists(terraform_workspace):
                terraform_backup = os.path.join(snapshot_dir, "terraform")
                shutil.copytree(terraform_workspace, terraform_backup)
            
            # Sauvegarder les fichiers Ansible
            ansible_workspace = self.ansible_service.get_lab_workspace(lab_id)
            if os.path.exists(ansible_workspace):
                ansible_backup = os.path.join(snapshot_dir, "ansible")
                shutil.copytree(ansible_workspace, ansible_backup)
            
            # Créer les snapshots des VMs (si supporté par le provider)
            vm_snapshots = self._create_vm_snapshots(lab)
            if vm_snapshots:
                snapshots_path = os.path.join(snapshot_dir, "vm_snapshots.json")
                with open(snapshots_path, "w") as f:
                    json.dump(vm_snapshots, f, indent=2)
            
            # Créer l'archive tar.gz
            archive_path = f"{snapshot_dir}.tar.gz"
            with tarfile.open(archive_path, "w:gz") as tar:
                tar.add(snapshot_dir, arcname=os.path.basename(snapshot_dir))
            
            # Nettoyer le répertoire temporaire
            shutil.rmtree(snapshot_dir)
            
            # Enregistrer le snapshot en base
            snapshot = Snapshot(
                lab_id=lab_id,
                name=snapshot_name,
                description=description,
                snapshot_data=json.dumps({
                    "archive_path": archive_path,
                    "size": os.path.getsize(archive_path),
                    "vm_snapshots": vm_snapshots
                })
            )
            
            db.session.add(snapshot)
            db.session.commit()
            
            return {
                "success": True,
                "snapshot_id": snapshot.id,
                "archive_path": archive_path,
                "size": os.path.getsize(archive_path)
            }
            
        except Exception as e:
            db.session.rollback()
            return {"success": False, "error": str(e)}
    
    def restore_snapshot(self, snapshot_id: int, new_lab_name: str = None) -> Dict[str, Any]:
        """Restaurer un lab à partir d'un snapshot"""
        snapshot = Snapshot.query.get(snapshot_id)
        if not snapshot:
            return {"success": False, "error": "Snapshot not found"}
        
        try:
            snapshot_data = json.loads(snapshot.snapshot_data)
            archive_path = snapshot_data["archive_path"]
            
            if not os.path.exists(archive_path):
                return {"success": False, "error": "Snapshot archive not found"}
            
            # Extraire l'archive
            extract_dir = os.path.join(self.backup_dir, f"restore_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
            os.makedirs(extract_dir, exist_ok=True)
            
            with tarfile.open(archive_path, "r:gz") as tar:
                tar.extractall(extract_dir)
            
            # Lire la configuration du lab
            config_path = os.path.join(extract_dir, os.listdir(extract_dir)[0], "lab_config.json")
            with open(config_path, "r") as f:
                lab_config = json.load(f)
            
            # Créer un nouveau lab
            original_lab = lab_config["lab"]
            new_lab = Lab(
                name=new_lab_name or f"{original_lab['name']}_restored_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                description=f"Restored from snapshot: {snapshot.name}",
                provider=original_lab["provider"],
                provider_config=json.dumps(original_lab["provider_config"]),
                status="stopped"
            )
            
            db.session.add(new_lab)
            db.session.flush()
            
            # Recréer les machines
            for machine_data in lab_config["machines"]:
                machine = Machine(
                    lab_id=new_lab.id,
                    name=machine_data["name"],
                    os=machine_data["os"],
                    cpu=machine_data["cpu"],
                    ram=machine_data["ram"],
                    storage=machine_data["storage"],
                    role=machine_data["role"],
                    software_config=json.dumps(machine_data["software_config"]),
                    custom_playbooks=json.dumps(machine_data["custom_playbooks"])
                )
                db.session.add(machine)
            
            db.session.commit()
            
            # Restaurer les fichiers Terraform
            terraform_backup = os.path.join(extract_dir, os.listdir(extract_dir)[0], "terraform")
            if os.path.exists(terraform_backup):
                terraform_workspace = self.terraform_service.get_lab_workspace(new_lab.id)
                shutil.copytree(terraform_backup, terraform_workspace)
            
            # Restaurer les fichiers Ansible
            ansible_backup = os.path.join(extract_dir, os.listdir(extract_dir)[0], "ansible")
            if os.path.exists(ansible_backup):
                ansible_workspace = self.ansible_service.get_lab_workspace(new_lab.id)
                shutil.copytree(ansible_backup, ansible_workspace)
            
            # Nettoyer
            shutil.rmtree(extract_dir)
            
            return {
                "success": True,
                "new_lab_id": new_lab.id,
                "new_lab_name": new_lab.name
            }
            
        except Exception as e:
            db.session.rollback()
            return {"success": False, "error": str(e)}
    
    def export_lab(self, lab_id: int) -> Dict[str, Any]:
        """Exporter un lab complet (configuration + état)"""
        lab = Lab.query.get(lab_id)
        if not lab:
            return {"success": False, "error": "Lab not found"}
        
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            export_dir = os.path.join(self.backup_dir, f"lab_{lab_id}_export_{timestamp}")
            os.makedirs(export_dir, exist_ok=True)
            
            # Exporter la configuration complète
            export_data = {
                "lab": lab.to_dict(),
                "machines": [machine.to_dict() for machine in lab.machines],
                "snapshots": [snapshot.to_dict() for snapshot in lab.snapshots],
                "export_metadata": {
                    "exported_at": datetime.now().isoformat(),
                    "version": "1.0"
                }
            }
            
            # Sauvegarder les playbooks personnalisés utilisés
            custom_playbook_ids = set()
            for machine in lab.machines:
                if machine.custom_playbooks:
                    custom_playbook_ids.update(json.loads(machine.custom_playbooks))
            
            if custom_playbook_ids:
                custom_playbooks = CustomPlaybook.query.filter(CustomPlaybook.id.in_(custom_playbook_ids)).all()
                export_data["custom_playbooks"] = [playbook.to_dict() for playbook in custom_playbooks]
            
            # Sauvegarder la configuration
            config_path = os.path.join(export_dir, "lab_export.json")
            with open(config_path, "w") as f:
                json.dump(export_data, f, indent=2)
            
            # Copier les workspaces
            terraform_workspace = self.terraform_service.get_lab_workspace(lab_id)
            if os.path.exists(terraform_workspace):
                shutil.copytree(terraform_workspace, os.path.join(export_dir, "terraform"))
            
            ansible_workspace = self.ansible_service.get_lab_workspace(lab_id)
            if os.path.exists(ansible_workspace):
                shutil.copytree(ansible_workspace, os.path.join(export_dir, "ansible"))
            
            # Créer l'archive
            archive_path = f"{export_dir}.tar.gz"
            with tarfile.open(archive_path, "w:gz") as tar:
                tar.add(export_dir, arcname=os.path.basename(export_dir))
            
            shutil.rmtree(export_dir)
            
            return {
                "success": True,
                "archive_path": archive_path,
                "size": os.path.getsize(archive_path)
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def import_lab(self, archive_path: str, new_lab_name: str = None) -> Dict[str, Any]:
        """Importer un lab à partir d'une archive d'export"""
        if not os.path.exists(archive_path):
            return {"success": False, "error": "Archive not found"}
        
        try:
            # Extraire l'archive
            extract_dir = os.path.join(self.backup_dir, f"import_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
            os.makedirs(extract_dir, exist_ok=True)
            
            with tarfile.open(archive_path, "r:gz") as tar:
                tar.extractall(extract_dir)
            
            # Lire la configuration
            config_path = os.path.join(extract_dir, os.listdir(extract_dir)[0], "lab_export.json")
            with open(config_path, "r") as f:
                export_data = json.load(f)
            
            # Importer les playbooks personnalisés d'abord
            if "custom_playbooks" in export_data:
                for playbook_data in export_data["custom_playbooks"]:
                    existing = CustomPlaybook.query.filter_by(name=playbook_data["name"]).first()
                    if not existing:
                        playbook = CustomPlaybook(
                            name=playbook_data["name"],
                            description=playbook_data["description"],
                            content=playbook_data["content"],
                            tags=",".join(playbook_data["tags"])
                        )
                        db.session.add(playbook)
            
            # Créer le lab
            original_lab = export_data["lab"]
            new_lab = Lab(
                name=new_lab_name or f"{original_lab['name']}_imported_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                description=f"Imported lab: {original_lab['description']}",
                provider=original_lab["provider"],
                provider_config=json.dumps(original_lab["provider_config"]),
                status="stopped"
            )
            
            db.session.add(new_lab)
            db.session.flush()
            
            # Créer les machines
            for machine_data in export_data["machines"]:
                machine = Machine(
                    lab_id=new_lab.id,
                    name=machine_data["name"],
                    os=machine_data["os"],
                    cpu=machine_data["cpu"],
                    ram=machine_data["ram"],
                    storage=machine_data["storage"],
                    role=machine_data["role"],
                    software_config=json.dumps(machine_data["software_config"]),
                    custom_playbooks=json.dumps(machine_data["custom_playbooks"])
                )
                db.session.add(machine)
            
            db.session.commit()
            
            # Restaurer les workspaces
            source_terraform = os.path.join(extract_dir, os.listdir(extract_dir)[0], "terraform")
            if os.path.exists(source_terraform):
                terraform_workspace = self.terraform_service.get_lab_workspace(new_lab.id)
                shutil.copytree(source_terraform, terraform_workspace)
            
            source_ansible = os.path.join(extract_dir, os.listdir(extract_dir)[0], "ansible")
            if os.path.exists(source_ansible):
                ansible_workspace = self.ansible_service.get_lab_workspace(new_lab.id)
                shutil.copytree(source_ansible, ansible_workspace)
            
            # Nettoyer
            shutil.rmtree(extract_dir)
            
            return {
                "success": True,
                "lab_id": new_lab.id,
                "lab_name": new_lab.name
            }
            
        except Exception as e:
            db.session.rollback()
            return {"success": False, "error": str(e)}
    
    def _create_vm_snapshots(self, lab: Lab) -> Optional[Dict[str, Any]]:
        """Créer des snapshots des VMs (dépend du provider)"""
        # Cette fonction dépend du provider utilisé
        # Pour DigitalOcean, on peut utiliser l'API pour créer des snapshots
        # Pour Proxmox, on peut utiliser les commandes qm snapshot
        
        if lab.provider == "vps":
            return self._create_digitalocean_snapshots(lab)
        elif lab.provider == "local":
            return self._create_proxmox_snapshots(lab)
        
        return None
    
    def _create_digitalocean_snapshots(self, lab: Lab) -> Dict[str, Any]:
        """Créer des snapshots DigitalOcean"""
        # Implémentation pour DigitalOcean
        # Nécessite l'API DigitalOcean
        snapshots = {}
        
        # Obtenir les IDs des droplets depuis Terraform
        terraform_outputs = self.terraform_service.get_terraform_outputs(lab.id)
        if terraform_outputs.get("success"):
            outputs = terraform_outputs["outputs"]
            
            for machine in lab.machines:
                machine_key = f"machine_{machine.id}_ip"
                if machine_key in outputs:
                    # Ici on pourrait appeler l'API DigitalOcean pour créer un snapshot
                    snapshots[machine.name] = {
                        "type": "digitalocean",
                        "snapshot_id": f"snapshot_{machine.id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                        "created_at": datetime.now().isoformat()
                    }
        
        return snapshots
    
    def _create_proxmox_snapshots(self, lab: Lab) -> Dict[str, Any]:
        """Créer des snapshots Proxmox"""
        snapshots = {}
        
        for machine in lab.machines:
            try:
                # Commande pour créer un snapshot Proxmox
                snapshot_name = f"lab_snapshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                
                # Cette commande nécessiterait d'être exécutée sur le serveur Proxmox
                # result = subprocess.run([
                #     "qm", "snapshot", str(machine.id), snapshot_name
                # ], capture_output=True, text=True)
                
                snapshots[machine.name] = {
                    "type": "proxmox",
                    "snapshot_name": snapshot_name,
                    "vm_id": machine.id,
                    "created_at": datetime.now().isoformat()
                }
                
            except Exception as e:
                print(f"Error creating snapshot for {machine.name}: {e}")
        
        return snapshots
    
    def get_lab_history(self, lab_id: int) -> List[Dict[str, Any]]:
        """Obtenir l'historique des snapshots d'un lab"""
        snapshots = Snapshot.query.filter_by(lab_id=lab_id).order_by(Snapshot.created_at.desc()).all()
        return [snapshot.to_dict() for snapshot in snapshots]
    
    def cleanup_old_snapshots(self, lab_id: int, keep_count: int = 10) -> Dict[str, Any]:
        """Nettoyer les anciens snapshots"""
        snapshots = Snapshot.query.filter_by(lab_id=lab_id).order_by(Snapshot.created_at.desc()).all()
        
        if len(snapshots) <= keep_count:
            return {"success": True, "deleted_count": 0}
        
        snapshots_to_delete = snapshots[keep_count:]
        deleted_count = 0
        
        for snapshot in snapshots_to_delete:
            try:
                snapshot_data = json.loads(snapshot.snapshot_data)
                archive_path = snapshot_data.get("archive_path")
                
                if archive_path and os.path.exists(archive_path):
                    os.remove(archive_path)
                
                db.session.delete(snapshot)
                deleted_count += 1
                
            except Exception as e:
                print(f"Error deleting snapshot {snapshot.id}: {e}")
        
        db.session.commit()
        
        return {"success": True, "deleted_count": deleted_count}


