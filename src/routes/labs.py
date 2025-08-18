from flask import Blueprint, request, jsonify
from src.models.lab import db, Lab, Machine, CustomPlaybook, DeploymentLog
from src.services.terraform_service import TerraformService
from src.services.ansible_service import AnsibleService
from src.services.backup_service import BackupService
import json
from datetime import datetime
import os

labs_bp = Blueprint("labs_bp", __name__)

terraform_service = TerraformService(workspace_dir=os.getenv("TERRAFORM_WORKSPACE_DIR", "/tmp/terraform_workspaces"))
ansible_service = AnsibleService(workspace_dir=os.getenv("ANSIBLE_WORKSPACE_DIR", "/tmp/ansible_workspaces"))
backup_service = BackupService(backup_dir=os.getenv("BACKUP_DIR", "/tmp/lab_backups"))

@labs_bp.route("/labs", methods=["POST"])
def create_lab():
    data = request.get_json()
    
    new_lab = Lab(
        name=data["name"],
        description=data.get("description"),
        provider=data["provider"],
        provider_config=json.dumps(data.get("provider_config", {})),
        status="stopped"
    )
    db.session.add(new_lab)
    db.session.flush()  # To get the new_lab.id
    
    for machine_data in data.get("machines", []):
        new_machine = Machine(
            lab_id=new_lab.id,
            name=machine_data["name"],
            os=machine_data["os"],
            cpu=machine_data.get("cpu", 2),
            ram=machine_data.get("ram", 4),
            storage=machine_data.get("storage", 20),
            role=machine_data.get("role"),
            software_config=json.dumps(machine_data.get("software", [])),
            custom_playbooks=json.dumps(machine_data.get("custom_playbooks", []))
        )
        db.session.add(new_machine)
        
    db.session.commit()
    return jsonify(new_lab.to_dict()), 201

@labs_bp.route("/labs", methods=["GET"])
def get_labs():
    labs = Lab.query.all()
    return jsonify([lab.to_dict() for lab in labs]), 200

@labs_bp.route("/labs/<int:lab_id>", methods=["GET"])
def get_lab(lab_id):
    lab = Lab.query.get_or_404(lab_id)
    return jsonify(lab.to_dict()), 200

@labs_bp.route("/labs/<int:lab_id>", methods=["PUT"])
def update_lab(lab_id):
    lab = Lab.query.get_or_404(lab_id)
    data = request.get_json()
    
    lab.name = data.get("name", lab.name)
    lab.description = data.get("description", lab.description)
    lab.provider = data.get("provider", lab.provider)
    lab.provider_config = json.dumps(data.get("provider_config", {}))
    
    # Update machines (simple replacement for now)
    db.session.query(Machine).filter_by(lab_id=lab_id).delete()
    for machine_data in data.get("machines", []):
        new_machine = Machine(
            lab_id=lab.id,
            name=machine_data["name"],
            os=machine_data["os"],
            cpu=machine_data.get("cpu", 2),
            ram=machine_data.get("ram", 4),
            storage=machine_data.get("storage", 20),
            role=machine_data.get("role"),
            software_config=json.dumps(machine_data.get("software", [])),
            custom_playbooks=json.dumps(machine_data.get("custom_playbooks", []))
        )
        db.session.add(new_machine)
        
    db.session.commit()
    return jsonify(lab.to_dict()), 200

@labs_bp.route("/labs/<int:lab_id>", methods=["DELETE"])
def delete_lab(lab_id):
    lab = Lab.query.get_or_404(lab_id)
    db.session.delete(lab)
    db.session.commit()
    
    # Cleanup workspaces
    terraform_service.cleanup_workspace(lab_id)
    ansible_service.cleanup_workspace(lab_id)
    
    return jsonify({"message": "Lab deleted"}), 204

@labs_bp.route("/labs/<int:lab_id>/deploy", methods=["POST"])
def deploy_lab(lab_id):
    lab = Lab.query.get_or_404(lab_id)
    lab.status = "deploying"
    db.session.commit()
    
    log = DeploymentLog(
        lab_id=lab.id,
        operation="deploy",
        status="running",
        logs=""
    )
    db.session.add(log)
    db.session.commit()
    
    try:
        # 1. Generate Terraform config
        workspace_path = terraform_service.generate_terraform_config(lab)
        log.logs += f"Generated Terraform config in {workspace_path}\n"
        db.session.commit()
        
        # 2. Terraform Init
        init_result = terraform_service.terraform_init(lab.id)
        log.logs += f"Terraform Init: {init_result}\n"
        if not init_result["success"]:
            raise Exception(f"Terraform Init failed: {init_result['stderr']}")
        db.session.commit()
        
        # 3. Terraform Plan
        plan_result = terraform_service.terraform_plan(lab.id)
        log.logs += f"Terraform Plan: {plan_result}\n"
        if not plan_result["success"]:
            raise Exception(f"Terraform Plan failed: {plan_result['stderr']}")
        db.session.commit()
        
        # 4. Terraform Apply
        apply_result = terraform_service.terraform_apply(lab.id)
        log.logs += f"Terraform Apply: {apply_result}\n"
        if not apply_result["success"]:
            raise Exception(f"Terraform Apply failed: {apply_result['stderr']}")
        db.session.commit()
        
        # 5. Get Terraform Outputs (IPs)
        outputs = terraform_service.get_terraform_outputs(lab.id)
        if not outputs["success"]:
            raise Exception(f"Failed to get Terraform outputs: {outputs['error']}")
        
        machine_ips = {}
        for machine in lab.machines:
            ip_output_key = f"machine_{machine.id}_ip"
            if ip_output_key in outputs["outputs"]:
                machine.ip_address = outputs["outputs"][ip_output_key]["value"]
                machine_ips[machine.id] = machine.ip_address
            db.session.commit()
        log.logs += f"Machine IPs: {machine_ips}\n"
        db.session.commit()
        
        # 6. Generate Ansible Inventory
        inventory_path = ansible_service.generate_inventory(lab, machine_ips)
        log.logs += f"Generated Ansible inventory in {inventory_path}\n"
        db.session.commit()
        
        # 7. Save SSH Key (assuming it's provided in provider_config)
        provider_config = json.loads(lab.provider_config)
        ssh_private_key = provider_config.get("ssh_private_key") # Assuming private key is passed
        if ssh_private_key:
            ansible_service.save_ssh_key(lab.id, ssh_private_key)
            log.logs += "SSH private key saved.\n"
            db.session.commit()
        
        # 8. Test Ansible Connectivity
        connectivity_result = ansible_service.test_connectivity(lab.id, inventory_path)
        log.logs += f"Ansible Connectivity Test: {connectivity_result}\n"
        if not connectivity_result["success"]:
            raise Exception(f"Ansible Connectivity Test failed: {connectivity_result['stderr']}")
        db.session.commit()
        
        # 9. Run Ansible Playbooks for each machine
        custom_playbooks = CustomPlaybook.query.filter(CustomPlaybook.id.in_(
            [pb_id for machine in lab.machines for pb_id in json.loads(machine.custom_playbooks) if machine.custom_playbooks]
        )).all()
        
        for machine in lab.machines:
            machine_playbook_path = ansible_service.generate_machine_playbook(machine, custom_playbooks)
            log.logs += f"Generated playbook for {machine.name}: {machine_playbook_path}\n"
            db.session.commit()
            
            playbook_result = ansible_service.run_playbook(lab.id, machine_playbook_path, inventory_path, limit=machine.name)
            log.logs += f"Ansible Playbook for {machine.name}: {playbook_result}\n"
            if not playbook_result["success"]:
                raise Exception(f"Ansible Playbook for {machine.name} failed: {playbook_result['stderr']}")
            db.session.commit()
            
        lab.status = "running"
        log.status = "success"
        log.completed_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({"message": "Lab deployed successfully", "lab": lab.to_dict()}), 200
        
    except Exception as e:
        lab.status = "error"
        log.status = "error"
        log.logs += f"Deployment failed: {str(e)}\n"
        log.completed_at = datetime.utcnow()
        db.session.commit()
        return jsonify({"message": "Deployment failed", "error": str(e)}), 500

@labs_bp.route("/labs/<int:lab_id>/destroy", methods=["POST"])
def destroy_lab(lab_id):
    lab = Lab.query.get_or_404(lab_id)
    lab.status = "destroying"
    db.session.commit()
    
    log = DeploymentLog(
        lab_id=lab.id,
        operation="destroy",
        status="running",
        logs=""
    )
    db.session.add(log)
    db.session.commit()
    
    try:
        destroy_result = terraform_service.terraform_destroy(lab.id)
        log.logs += f"Terraform Destroy: {destroy_result}\n"
        if not destroy_result["success"]:
            raise Exception(f"Terraform Destroy failed: {destroy_result['stderr']}")
        
        lab.status = "stopped"
        log.status = "success"
        log.completed_at = datetime.utcnow()
        db.session.commit()
        
        # Cleanup workspaces after successful destroy
        terraform_service.cleanup_workspace(lab.id)
        ansible_service.cleanup_workspace(lab.id)
        
        return jsonify({"message": "Lab destroyed successfully"}), 200
        
    except Exception as e:
        lab.status = "error"
        log.status = "error"
        log.logs += f"Destroy failed: {str(e)}\n"
        log.completed_at = datetime.utcnow()
        db.session.commit()
        return jsonify({"message": "Destroy failed", "error": str(e)}), 500

@labs_bp.route("/labs/<int:lab_id>/start", methods=["POST"])
def start_lab(lab_id):
    lab = Lab.query.get_or_404(lab_id)
    # Logic to start VMs (provider specific, e.g., DigitalOcean API, Proxmox API)
    # For now, just update status
    lab.status = "running"
    db.session.commit()
    return jsonify({"message": "Lab started (simulated)", "lab": lab.to_dict()}), 200

@labs_bp.route("/labs/<int:lab_id>/stop", methods=["POST"])
def stop_lab(lab_id):
    lab = Lab.query.get_or_404(lab_id)
    # Logic to stop VMs (provider specific)
    # For now, just update status
    lab.status = "stopped"
    db.session.commit()
    return jsonify({"message": "Lab stopped (simulated)", "lab": lab.to_dict()}), 200

@labs_bp.route("/labs/<int:lab_id>/snapshots", methods=["POST"])
def create_lab_snapshot(lab_id):
    data = request.get_json()
    snapshot_name = data.get("name", f"Snapshot-{datetime.now().strftime('%Y%m%d%H%M%S')}")
    description = data.get("description", "")
    
    result = backup_service.create_snapshot(lab_id, snapshot_name, description)
    if result["success"]:
        return jsonify({"message": "Snapshot created", "snapshot_id": result["snapshot_id"]}), 201
    else:
        return jsonify({"error": result["error"]}), 500

@labs_bp.route("/labs/<int:lab_id>/snapshots", methods=["GET"])
def get_lab_snapshots(lab_id):
    snapshots = backup_service.get_lab_history(lab_id)
    return jsonify(snapshots), 200

@labs_bp.route("/snapshots/<int:snapshot_id>/restore", methods=["POST"])
def restore_lab_from_snapshot(snapshot_id):
    data = request.get_json()
    new_lab_name = data.get("new_lab_name")
    result = backup_service.restore_snapshot(snapshot_id, new_lab_name)
    if result["success"]:
        return jsonify({"message": "Lab restored", "new_lab_id": result["new_lab_id"]}), 200
    else:
        return jsonify({"error": result["error"]}), 500

@labs_bp.route("/playbooks", methods=["POST"])
def create_custom_playbook():
    data = request.get_json()
    new_playbook = CustomPlaybook(
        name=data["name"],
        description=data.get("description"),
        content=data["content"],
        tags=",".join(data.get("tags", []))
    )
    db.session.add(new_playbook)
    db.session.commit()
    return jsonify(new_playbook.to_dict()), 201

@labs_bp.route("/playbooks", methods=["GET"])
def get_custom_playbooks():
    playbooks = CustomPlaybook.query.all()
    return jsonify([pb.to_dict() for pb in playbooks]), 200

@labs_bp.route("/playbooks/<int:playbook_id>", methods=["PUT"])
def update_custom_playbook(playbook_id):
    playbook = CustomPlaybook.query.get_or_404(playbook_id)
    data = request.get_json()
    playbook.name = data.get("name", playbook.name)
    playbook.description = data.get("description", playbook.description)
    playbook.content = data.get("content", playbook.content)
    playbook.tags = ",".join(data.get("tags", []))
    db.session.commit()
    return jsonify(playbook.to_dict()), 200

@labs_bp.route("/playbooks/<int:playbook_id>", methods=["DELETE"])
def delete_custom_playbook(playbook_id):
    playbook = CustomPlaybook.query.get_or_404(playbook_id)
    db.session.delete(playbook)
    db.session.commit()
    return jsonify({"message": "Playbook deleted"}), 204

@labs_bp.route("/deployment_logs", methods=["GET"])
def get_deployment_logs():
    logs = DeploymentLog.query.order_by(DeploymentLog.started_at.desc()).all()
    return jsonify([log.to_dict() for log in logs]), 200

@labs_bp.route("/deployment_logs/<int:log_id>", methods=["GET"])
def get_deployment_log(log_id):
    log = DeploymentLog.query.get_or_404(log_id)
    return jsonify(log.to_dict()), 200

@labs_bp.route("/labs/<int:lab_id>/export", methods=["POST"])
def export_lab_route(lab_id):
    result = backup_service.export_lab(lab_id)
    if result["success"]:
        return jsonify({"message": "Lab exported", "archive_path": result["archive_path"], "size": result["size"]}), 200
    else:
        return jsonify({"error": result["error"]}), 500

@labs_bp.route("/labs/import", methods=["POST"])
def import_lab_route():
    data = request.get_json()
    archive_path = data.get("archive_path")
    new_lab_name = data.get("new_lab_name")
    
    if not archive_path:
        return jsonify({"error": "archive_path is required"}), 400
        
    result = backup_service.import_lab(archive_path, new_lab_name)
    if result["success"]:
        return jsonify({"message": "Lab imported", "lab_id": result["lab_id"]}), 200
    else:
        return jsonify({"error": result["error"]}), 500


