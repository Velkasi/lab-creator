import os
import subprocess
import json
import yaml
import tempfile
from typing import Dict, List, Any
from src.models.lab import Lab, Machine, CustomPlaybook

class AnsibleService:
    def __init__(self, workspace_dir: str = "/tmp/ansible_workspaces"):
        self.workspace_dir = workspace_dir
        os.makedirs(workspace_dir, exist_ok=True)
        self.playbooks_dir = os.path.join(workspace_dir, "playbooks")
        os.makedirs(self.playbooks_dir, exist_ok=True)
    
    def get_lab_workspace(self, lab_id: int) -> str:
        """Obtenir le répertoire de travail Ansible pour un lab"""
        workspace = os.path.join(self.workspace_dir, f"lab_{lab_id}")
        os.makedirs(workspace, exist_ok=True)
        return workspace
    
    def generate_inventory(self, lab: Lab, machine_ips: Dict[int, str]) -> str:
        """Générer l'inventaire Ansible pour un lab"""
        workspace = self.get_lab_workspace(lab.id)
        inventory_path = os.path.join(workspace, "inventory.yml")
        
        inventory = {
            'all': {
                'children': {}
            }
        }
        
        # Grouper les machines par rôle
        roles = {}
        for machine in lab.machines:
            role = machine.role or 'default'
            if role not in roles:
                roles[role] = []
            
            machine_ip = machine_ips.get(machine.id)
            if machine_ip:
                roles[role].append({
                    'name': machine.name,
                    'ip': machine_ip,
                    'machine_id': machine.id
                })
        
        # Créer les groupes dans l'inventaire
        for role, machines in roles.items():
            inventory['all']['children'][role] = {
                'hosts': {}
            }
            
            for machine in machines:
                inventory['all']['children'][role]['hosts'][machine['name']] = {
                    'ansible_host': machine['ip'],
                    'ansible_user': 'ubuntu',
                    'ansible_ssh_private_key_file': f"{workspace}/ssh_key",
                    'machine_id': machine['machine_id']
                }
        
        # Variables globales
        inventory['all']['vars'] = {
            'ansible_ssh_common_args': '-o StrictHostKeyChecking=no',
            'ansible_python_interpreter': '/usr/bin/python3'
        }
        
        with open(inventory_path, 'w') as f:
            yaml.dump(inventory, f, default_flow_style=False)
        
        return inventory_path
    
    def generate_base_playbooks(self) -> Dict[str, str]:
        """Générer les playbooks de base pour les logiciels courants"""
        playbooks = {}
        
        # Playbook Docker
        playbooks['docker'] = '''---
- name: Install Docker
  hosts: all
  become: yes
  tasks:
    - name: Update apt cache
      apt:
        update_cache: yes
    
    - name: Install required packages
      apt:
        name:
          - apt-transport-https
          - ca-certificates
          - curl
          - gnupg
          - lsb-release
        state: present
    
    - name: Add Docker GPG key
      apt_key:
        url: https://download.docker.com/linux/ubuntu/gpg
        state: present
    
    - name: Add Docker repository
      apt_repository:
        repo: "deb [arch=amd64] https://download.docker.com/linux/ubuntu {{ ansible_distribution_release }} stable"
        state: present
    
    - name: Install Docker
      apt:
        name:
          - docker-ce
          - docker-ce-cli
          - containerd.io
          - docker-compose-plugin
        state: present
    
    - name: Start and enable Docker
      systemd:
        name: docker
        state: started
        enabled: yes
    
    - name: Add user to docker group
      user:
        name: "{{ ansible_user }}"
        groups: docker
        append: yes
'''
        
        # Playbook Nginx
        playbooks['nginx'] = '''---
- name: Install and configure Nginx
  hosts: all
  become: yes
  tasks:
    - name: Update apt cache
      apt:
        update_cache: yes
    
    - name: Install Nginx
      apt:
        name: nginx
        state: present
    
    - name: Start and enable Nginx
      systemd:
        name: nginx
        state: started
        enabled: yes
    
    - name: Configure firewall for Nginx
      ufw:
        rule: allow
        name: 'Nginx Full'
'''
        
        # Playbook MySQL
        playbooks['mysql'] = '''---
- name: Install MySQL
  hosts: all
  become: yes
  vars:
    mysql_root_password: "mysql_secure_password"
  tasks:
    - name: Update apt cache
      apt:
        update_cache: yes
    
    - name: Install MySQL server
      apt:
        name: mysql-server
        state: present
    
    - name: Install Python MySQL dependencies
      apt:
        name: python3-pymysql
        state: present
    
    - name: Start and enable MySQL
      systemd:
        name: mysql
        state: started
        enabled: yes
    
    - name: Set MySQL root password
      mysql_user:
        name: root
        password: "{{ mysql_root_password }}"
        login_unix_socket: /var/run/mysqld/mysqld.sock
        state: present
    
    - name: Create MySQL configuration file
      template:
        src: my.cnf.j2
        dest: /root/.my.cnf
        owner: root
        group: root
        mode: '0600'
'''
        
        # Playbook PostgreSQL
        playbooks['postgresql'] = '''---
- name: Install PostgreSQL
  hosts: all
  become: yes
  vars:
    postgres_password: "postgres_secure_password"
  tasks:
    - name: Update apt cache
      apt:
        update_cache: yes
    
    - name: Install PostgreSQL
      apt:
        name:
          - postgresql
          - postgresql-contrib
          - python3-psycopg2
        state: present
    
    - name: Start and enable PostgreSQL
      systemd:
        name: postgresql
        state: started
        enabled: yes
    
    - name: Set PostgreSQL password
      postgresql_user:
        name: postgres
        password: "{{ postgres_password }}"
      become_user: postgres
'''
        
        # Playbook Node.js
        playbooks['nodejs'] = '''---
- name: Install Node.js
  hosts: all
  become: yes
  tasks:
    - name: Update apt cache
      apt:
        update_cache: yes
    
    - name: Install Node.js dependencies
      apt:
        name:
          - curl
          - software-properties-common
        state: present
    
    - name: Add NodeSource repository
      shell: curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
    
    - name: Install Node.js
      apt:
        name: nodejs
        state: present
    
    - name: Install npm packages globally
      npm:
        name: "{{ item }}"
        global: yes
      loop:
        - pm2
        - nodemon
'''
        
        # Playbook Python
        playbooks['python'] = '''---
- name: Install Python development environment
  hosts: all
  become: yes
  tasks:
    - name: Update apt cache
      apt:
        update_cache: yes
    
    - name: Install Python and development tools
      apt:
        name:
          - python3
          - python3-pip
          - python3-venv
          - python3-dev
          - build-essential
        state: present
    
    - name: Install common Python packages
      pip:
        name:
          - virtualenv
          - pipenv
          - poetry
          - jupyter
          - requests
          - flask
          - django
        executable: pip3
'''
        
        # Playbook Git
        playbooks['git'] = '''---
- name: Install and configure Git
  hosts: all
  become: yes
  tasks:
    - name: Update apt cache
      apt:
        update_cache: yes
    
    - name: Install Git
      apt:
        name: git
        state: present
    
    - name: Configure Git global settings
      git_config:
        name: "{{ item.name }}"
        value: "{{ item.value }}"
        scope: global
      loop:
        - { name: "user.name", value: "Lab User" }
        - { name: "user.email", value: "user@lab.local" }
        - { name: "init.defaultBranch", value: "main" }
      become_user: "{{ ansible_user }}"
'''
        
        # Playbook VS Code Server
        playbooks['vscode-server'] = '''---
- name: Install VS Code Server
  hosts: all
  become: yes
  tasks:
    - name: Update apt cache
      apt:
        update_cache: yes
    
    - name: Install dependencies
      apt:
        name:
          - wget
          - curl
          - unzip
        state: present
    
    - name: Download VS Code Server
      get_url:
        url: "https://github.com/coder/code-server/releases/latest/download/code-server_4.16.1_amd64.deb"
        dest: "/tmp/code-server.deb"
    
    - name: Install VS Code Server
      apt:
        deb: "/tmp/code-server.deb"
        state: present
    
    - name: Create code-server config directory
      file:
        path: "/home/{{ ansible_user }}/.config/code-server"
        state: directory
        owner: "{{ ansible_user }}"
        group: "{{ ansible_user }}"
    
    - name: Configure code-server
      copy:
        content: |
          bind-addr: 0.0.0.0:8080
          auth: password
          password: codeserver123
          cert: false
        dest: "/home/{{ ansible_user }}/.config/code-server/config.yaml"
        owner: "{{ ansible_user }}"
        group: "{{ ansible_user }}"
    
    - name: Create systemd service for code-server
      copy:
        content: |
          [Unit]
          Description=code-server
          After=network.target
          
          [Service]
          Type=simple
          User={{ ansible_user }}
          ExecStart=/usr/bin/code-server
          Restart=always
          
          [Install]
          WantedBy=multi-user.target
        dest: "/etc/systemd/system/code-server.service"
    
    - name: Start and enable code-server
      systemd:
        name: code-server
        state: started
        enabled: yes
        daemon_reload: yes
'''
        
        # Sauvegarder les playbooks
        for name, content in playbooks.items():
            playbook_path = os.path.join(self.playbooks_dir, f"{name}.yml")
            with open(playbook_path, 'w') as f:
                f.write(content)
        
        return playbooks
    
    def generate_machine_playbook(self, machine: Machine, custom_playbooks: List[CustomPlaybook] = None) -> str:
        """Générer un playbook spécifique pour une machine"""
        workspace = self.get_lab_workspace(machine.lab_id)
        playbook_path = os.path.join(workspace, f"machine_{machine.id}_playbook.yml")
        
        software_config = json.loads(machine.software_config) if machine.software_config else []
        custom_playbook_ids = json.loads(machine.custom_playbooks) if machine.custom_playbooks else []
        
        playbook = {
            'name': f'Configure {machine.name}',
            'hosts': machine.name,
            'become': True,
            'tasks': []
        }
        
        # Tâches de base
        playbook['tasks'].extend([
            {
                'name': 'Update apt cache',
                'apt': {'update_cache': True}
            },
            {
                'name': 'Install basic packages',
                'apt': {
                    'name': ['curl', 'wget', 'vim', 'htop', 'unzip'],
                    'state': 'present'
                }
            }
        ])
        
        # Inclure les playbooks pour les logiciels sélectionnés
        for software in software_config:
            playbook_file = os.path.join(self.playbooks_dir, f"{software}.yml")
            if os.path.exists(playbook_file):
                playbook['tasks'].append({
                    'name': f'Include {software} playbook',
                    'include': playbook_file
                })
        
        # Ajouter les playbooks personnalisés
        if custom_playbooks:
            for custom_playbook in custom_playbooks:
                if custom_playbook.id in custom_playbook_ids:
                    # Sauvegarder le playbook personnalisé
                    custom_path = os.path.join(workspace, f"custom_{custom_playbook.id}.yml")
                    with open(custom_path, 'w') as f:
                        f.write(custom_playbook.content)
                    
                    playbook['tasks'].append({
                        'name': f'Include custom playbook: {custom_playbook.name}',
                        'include': custom_path
                    })
        
        # Sauvegarder le playbook principal
        with open(playbook_path, 'w') as f:
            yaml.dump([playbook], f, default_flow_style=False)
        
        return playbook_path
    
    def run_playbook(self, lab_id: int, playbook_path: str, inventory_path: str, limit: str = None) -> Dict[str, Any]:
        """Exécuter un playbook Ansible"""
        workspace = self.get_lab_workspace(lab_id)
        
        cmd = [
            'ansible-playbook',
            '-i', inventory_path,
            playbook_path,
            '-v'
        ]
        
        if limit:
            cmd.extend(['--limit', limit])
        
        try:
            result = subprocess.run(
                cmd,
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
                'stderr': 'Timeout during ansible playbook execution',
                'returncode': -1
            }
    
    def test_connectivity(self, lab_id: int, inventory_path: str) -> Dict[str, Any]:
        """Tester la connectivité avec les machines"""
        workspace = self.get_lab_workspace(lab_id)
        
        try:
            result = subprocess.run(
                ['ansible', 'all', '-i', inventory_path, '-m', 'ping'],
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
                'stderr': 'Timeout during connectivity test',
                'returncode': -1
            }
    
    def save_ssh_key(self, lab_id: int, private_key: str) -> str:
        """Sauvegarder la clé SSH privée pour un lab"""
        workspace = self.get_lab_workspace(lab_id)
        key_path = os.path.join(workspace, "ssh_key")
        
        with open(key_path, 'w') as f:
            f.write(private_key)
        
        os.chmod(key_path, 0o600)
        return key_path
    
    def cleanup_workspace(self, lab_id: int):
        """Nettoyer le workspace Ansible d'un lab"""
        workspace = self.get_lab_workspace(lab_id)
        if os.path.exists(workspace):
            import shutil
            shutil.rmtree(workspace)


