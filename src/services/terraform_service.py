import os
import subprocess
import json
import tempfile
import shutil
from typing import Dict, List, Any
from src.models.lab import Lab, Machine

class TerraformService:
    def __init__(self, workspace_dir: str = "/tmp/terraform_workspaces"):
        self.workspace_dir = workspace_dir
        os.makedirs(workspace_dir, exist_ok=True)
    
    def get_lab_workspace(self, lab_id: int) -> str:
        """Obtenir le répertoire de travail pour un lab spécifique"""
        workspace = os.path.join(self.workspace_dir, f"lab_{lab_id}")
        os.makedirs(workspace, exist_ok=True)
        return workspace
    
    def generate_terraform_config(self, lab: Lab) -> str:
        """Générer la configuration Terraform pour un lab"""
        workspace = self.get_lab_workspace(lab.id)
        
        # Choisir le template selon le provider
        if lab.provider == 'vps':
            config = self._generate_vps_config(lab)
        elif lab.provider == 'local':
            config = self._generate_local_config(lab)
        else:
            raise ValueError(f"Provider non supporté: {lab.provider}")
        
        # Écrire le fichier main.tf
        main_tf_path = os.path.join(workspace, "main.tf")
        with open(main_tf_path, 'w') as f:
            f.write(config)
        
        # Générer le fichier variables.tf
        variables_tf_path = os.path.join(workspace, "variables.tf")
        with open(variables_tf_path, 'w') as f:
            f.write(self._generate_variables_config(lab))
        
        # Générer le fichier terraform.tfvars
        tfvars_path = os.path.join(workspace, "terraform.tfvars")
        with open(tfvars_path, 'w') as f:
            f.write(self._generate_tfvars(lab))
        
        return workspace
    
    def _generate_vps_config(self, lab: Lab) -> str:
        """Générer la configuration Terraform pour VPS (DigitalOcean exemple)"""
        provider_config = json.loads(lab.provider_config) if lab.provider_config else {}
        
        config = f'''
terraform {{
  required_providers {{
    digitalocean = {{
      source  = "digitalocean/digitalocean"
      version = "~> 2.0"
    }}
  }}
}}

provider "digitalocean" {{
  token = var.do_token
}}

# Réseau privé pour le lab
resource "digitalocean_vpc" "lab_network" {{
  name     = "{lab.name}-network"
  region   = var.region
  ip_range = "10.0.0.0/16"
  
  tags = [
    "lab:{lab.name}",
    "lab_id:{lab.id}"
  ]
}}

# Clé SSH pour l'accès aux machines
resource "digitalocean_ssh_key" "lab_key" {{
  name       = "{lab.name}-key"
  public_key = var.ssh_public_key
}}
'''
        
        # Générer les ressources pour chaque machine
        for i, machine in enumerate(lab.machines):
            config += f'''
# Machine: {machine.name}
resource "digitalocean_droplet" "machine_{machine.id}" {{
  image    = var.machine_{machine.id}_image
  name     = "{machine.name}"
  region   = var.region
  size     = var.machine_{machine.id}_size
  vpc_uuid = digitalocean_vpc.lab_network.id
  
  ssh_keys = [digitalocean_ssh_key.lab_key.id]
  
  tags = [
    "lab:{lab.name}",
    "lab_id:{lab.id}",
    "machine:{machine.name}",
    "role:{machine.role}"
  ]
  
  user_data = <<-EOF
#!/bin/bash
apt-get update
apt-get install -y python3 python3-pip
pip3 install ansible
EOF
}}

# IP publique pour {machine.name}
resource "digitalocean_floating_ip" "machine_{machine.id}_ip" {{
  droplet = digitalocean_droplet.machine_{machine.id}.id
  region  = var.region
}}
'''
        
        # Outputs
        config += '''
# Outputs
'''
        for machine in lab.machines:
            config += f'''
output "machine_{machine.id}_ip" {{
  value = digitalocean_floating_ip.machine_{machine.id}_ip.ip_address
}}

output "machine_{machine.id}_private_ip" {{
  value = digitalocean_droplet.machine_{machine.id}.ipv4_address_private
}}
'''
        
        return config
    
    def _generate_local_config(self, lab: Lab) -> str:
        """Générer la configuration Terraform pour serveur local (Proxmox exemple)"""
        config = f'''
terraform {{
  required_providers {{
    proxmox = {{
      source  = "telmate/proxmox"
      version = "2.9.14"
    }}
  }}
}}

provider "proxmox" {{
  pm_api_url      = var.proxmox_api_url
  pm_user         = var.proxmox_user
  pm_password     = var.proxmox_password
  pm_tls_insecure = true
}}
'''
        
        # Générer les ressources pour chaque machine
        for machine in lab.machines:
            config += f'''
# Machine: {machine.name}
resource "proxmox_vm_qemu" "machine_{machine.id}" {{
  name        = "{machine.name}"
  target_node = var.proxmox_node
  clone       = var.machine_{machine.id}_template
  
  cores   = {machine.cpu}
  memory  = {machine.ram * 1024}
  sockets = 1
  
  disk {{
    size    = "{machine.storage}G"
    type    = "scsi"
    storage = var.proxmox_storage
  }}
  
  network {{
    model  = "virtio"
    bridge = var.proxmox_bridge
  }}
  
  os_type = "cloud-init"
  
  ciuser     = var.vm_user
  cipassword = var.vm_password
  sshkeys    = var.ssh_public_key
  
  tags = "lab:{lab.name},lab_id:{lab.id},machine:{machine.name},role:{machine.role}"
}}
'''
        
        # Outputs
        config += '''
# Outputs
'''
        for machine in lab.machines:
            config += f'''
output "machine_{machine.id}_ip" {{
  value = proxmox_vm_qemu.machine_{machine.id}.default_ipv4_address
}}
'''
        
        return config
    
    def _generate_variables_config(self, lab: Lab) -> str:
        """Générer le fichier variables.tf"""
        if lab.provider == 'vps':
            variables = '''
variable "do_token" {
  description = "DigitalOcean API Token"
  type        = string
  sensitive   = true
}

variable "region" {
  description = "DigitalOcean region"
  type        = string
  default     = "fra1"
}

variable "ssh_public_key" {
  description = "SSH public key for access"
  type        = string
}
'''
        else:  # local
            variables = '''
variable "proxmox_api_url" {
  description = "Proxmox API URL"
  type        = string
}

variable "proxmox_user" {
  description = "Proxmox username"
  type        = string
}

variable "proxmox_password" {
  description = "Proxmox password"
  type        = string
  sensitive   = true
}

variable "proxmox_node" {
  description = "Proxmox node name"
  type        = string
}

variable "proxmox_storage" {
  description = "Proxmox storage name"
  type        = string
  default     = "local-lvm"
}

variable "proxmox_bridge" {
  description = "Proxmox network bridge"
  type        = string
  default     = "vmbr0"
}

variable "vm_user" {
  description = "VM default user"
  type        = string
  default     = "ubuntu"
}

variable "vm_password" {
  description = "VM default password"
  type        = string
  sensitive   = true
}

variable "ssh_public_key" {
  description = "SSH public key for access"
  type        = string
}
'''
        
        # Ajouter les variables spécifiques aux machines
        for machine in lab.machines:
            if lab.provider == 'vps':
                variables += f'''
variable "machine_{machine.id}_image" {{
  description = "Image for {machine.name}"
  type        = string
  default     = "{self._get_do_image(machine.os)}"
}}

variable "machine_{machine.id}_size" {{
  description = "Size for {machine.name}"
  type        = string
  default     = "{self._get_do_size(machine.cpu, machine.ram)}"
}}
'''
            else:  # local
                variables += f'''
variable "machine_{machine.id}_template" {{
  description = "Template for {machine.name}"
  type        = string
  default     = "{self._get_proxmox_template(machine.os)}"
}}
'''
        
        return variables
    
    def _generate_tfvars(self, lab: Lab) -> str:
        """Générer le fichier terraform.tfvars avec des valeurs par défaut"""
        provider_config = json.loads(lab.provider_config) if lab.provider_config else {}
        
        if lab.provider == 'vps':
            tfvars = f'''
# DigitalOcean Configuration
do_token = "{provider_config.get('api_token', 'YOUR_DO_TOKEN')}"
region = "{provider_config.get('region', 'fra1')}"
ssh_public_key = "{provider_config.get('ssh_public_key', 'YOUR_SSH_PUBLIC_KEY')}"
'''
        else:  # local
            tfvars = f'''
# Proxmox Configuration
proxmox_api_url = "{provider_config.get('api_url', 'https://your-proxmox:8006/api2/json')}"
proxmox_user = "{provider_config.get('user', 'root@pam')}"
proxmox_password = "{provider_config.get('password', 'YOUR_PASSWORD')}"
proxmox_node = "{provider_config.get('node', 'proxmox')}"
proxmox_storage = "{provider_config.get('storage', 'local-lvm')}"
proxmox_bridge = "{provider_config.get('bridge', 'vmbr0')}"
vm_user = "{provider_config.get('vm_user', 'ubuntu')}"
vm_password = "{provider_config.get('vm_password', 'ubuntu')}"
ssh_public_key = "{provider_config.get('ssh_public_key', 'YOUR_SSH_PUBLIC_KEY')}"
'''
        
        return tfvars
    
    def _get_do_image(self, os: str) -> str:
        """Mapper les OS vers les images DigitalOcean"""
        mapping = {
            'ubuntu-22.04': 'ubuntu-22-04-x64',
            'ubuntu-20.04': 'ubuntu-20-04-x64',
            'centos-8': 'centos-8-x64',
            'debian-11': 'debian-11-x64'
        }
        return mapping.get(os, 'ubuntu-22-04-x64')
    
    def _get_do_size(self, cpu: int, ram: int) -> str:
        """Mapper CPU/RAM vers les tailles DigitalOcean"""
        if cpu <= 1 and ram <= 1:
            return 's-1vcpu-1gb'
        elif cpu <= 1 and ram <= 2:
            return 's-1vcpu-2gb'
        elif cpu <= 2 and ram <= 4:
            return 's-2vcpu-4gb'
        elif cpu <= 4 and ram <= 8:
            return 's-4vcpu-8gb'
        else:
            return 's-8vcpu-16gb'
    
    def _get_proxmox_template(self, os: str) -> str:
        """Mapper les OS vers les templates Proxmox"""
        mapping = {
            'ubuntu-22.04': 'ubuntu-22.04-template',
            'ubuntu-20.04': 'ubuntu-20.04-template',
            'centos-8': 'centos-8-template',
            'debian-11': 'debian-11-template'
        }
        return mapping.get(os, 'ubuntu-22.04-template')
    
    def terraform_init(self, lab_id: int) -> Dict[str, Any]:
        """Initialiser Terraform pour un lab"""
        workspace = self.get_lab_workspace(lab_id)
        
        try:
            result = subprocess.run(
                ['terraform', 'init'],
                cwd=workspace,
                capture_output=True,
                text=True,
                timeout=300
            )
            
            return {
                'success': result.returncode == 0,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'returncode': result.returncode
            }
        except subprocess.TimeoutExpired:
            return {
                'success': False,
                'stdout': '',
                'stderr': 'Timeout during terraform init',
                'returncode': -1
            }
    
    def terraform_plan(self, lab_id: int) -> Dict[str, Any]:
        """Planifier le déploiement Terraform"""
        workspace = self.get_lab_workspace(lab_id)
        
        try:
            result = subprocess.run(
                ['terraform', 'plan', '-out=tfplan'],
                cwd=workspace,
                capture_output=True,
                text=True,
                timeout=300
            )
            
            return {
                'success': result.returncode == 0,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'returncode': result.returncode
            }
        except subprocess.TimeoutExpired:
            return {
                'success': False,
                'stdout': '',
                'stderr': 'Timeout during terraform plan',
                'returncode': -1
            }
    
    def terraform_apply(self, lab_id: int) -> Dict[str, Any]:
        """Appliquer la configuration Terraform"""
        workspace = self.get_lab_workspace(lab_id)
        
        try:
            result = subprocess.run(
                ['terraform', 'apply', '-auto-approve', 'tfplan'],
                cwd=workspace,
                capture_output=True,
                text=True,
                timeout=1800  # 30 minutes
            )
            
            return {
                'success': result.returncode == 0,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'returncode': result.returncode
            }
        except subprocess.TimeoutExpired:
            return {
                'success': False,
                'stdout': '',
                'stderr': 'Timeout during terraform apply',
                'returncode': -1
            }
    
    def terraform_destroy(self, lab_id: int) -> Dict[str, Any]:
        """Détruire l'infrastructure Terraform"""
        workspace = self.get_lab_workspace(lab_id)
        
        try:
            result = subprocess.run(
                ['terraform', 'destroy', '-auto-approve'],
                cwd=workspace,
                capture_output=True,
                text=True,
                timeout=1800  # 30 minutes
            )
            
            return {
                'success': result.returncode == 0,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'returncode': result.returncode
            }
        except subprocess.TimeoutExpired:
            return {
                'success': False,
                'stdout': '',
                'stderr': 'Timeout during terraform destroy',
                'returncode': -1
            }
    
    def get_terraform_outputs(self, lab_id: int) -> Dict[str, Any]:
        """Récupérer les outputs Terraform"""
        workspace = self.get_lab_workspace(lab_id)
        
        try:
            result = subprocess.run(
                ['terraform', 'output', '-json'],
                cwd=workspace,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode == 0:
                return {
                    'success': True,
                    'outputs': json.loads(result.stdout)
                }
            else:
                return {
                    'success': False,
                    'error': result.stderr
                }
        except (subprocess.TimeoutExpired, json.JSONDecodeError) as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def cleanup_workspace(self, lab_id: int):
        """Nettoyer le workspace d'un lab"""
        workspace = self.get_lab_workspace(lab_id)
        if os.path.exists(workspace):
            shutil.rmtree(workspace)


