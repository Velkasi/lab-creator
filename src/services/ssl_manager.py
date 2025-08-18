import os
import subprocess
import logging
import json
import shutil
from typing import Dict, Optional, List
from pathlib import Path

logger = logging.getLogger(__name__)

class SSLManager:
    """Gestionnaire pour la configuration SSL/TLS automatique avec Caddy"""
    
    def __init__(self, config_dir: str = "/etc/caddy", data_dir: str = "/var/lib/caddy"):
        self.config_dir = Path(config_dir)
        self.data_dir = Path(data_dir)
        self.caddyfile_path = self.config_dir / "Caddyfile"
        self.caddy_service = "caddy"
        
    def is_caddy_installed(self) -> bool:
        """Vérifie si Caddy est installé"""
        try:
            result = subprocess.run(['caddy', 'version'], capture_output=True, text=True)
            return result.returncode == 0
        except FileNotFoundError:
            return False
    
    def install_caddy(self) -> bool:
        """Installe Caddy (nécessite les privilèges sudo)"""
        try:
            # Ajouter le repository Caddy
            commands = [
                ['curl', '-1sLf', 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key'],
                ['sudo', 'gpg', '--dearmor', '-o', '/usr/share/keyrings/caddy-stable-archive-keyring.gpg'],
                ['curl', '-1sLf', 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt'],
                ['sudo', 'tee', '/etc/apt/sources.list.d/caddy-stable.list'],
                ['sudo', 'apt', 'update'],
                ['sudo', 'apt', 'install', '-y', 'caddy']
            ]
            
            # Exécuter les commandes d'installation
            for i, cmd in enumerate(commands):
                if i == 0:  # Première commande avec pipe
                    p1 = subprocess.Popen(cmd, stdout=subprocess.PIPE)
                    p2 = subprocess.Popen(commands[1], stdin=p1.stdout, stdout=subprocess.PIPE)
                    p1.stdout.close()
                    p2.communicate()
                elif i == 2:  # Troisième commande avec pipe
                    p1 = subprocess.Popen(cmd, stdout=subprocess.PIPE)
                    p2 = subprocess.Popen(commands[3], stdin=p1.stdout, stdout=subprocess.PIPE)
                    p1.stdout.close()
                    p2.communicate()
                elif i not in [1, 3]:  # Éviter les commandes déjà exécutées
                    result = subprocess.run(cmd, capture_output=True, text=True)
                    if result.returncode != 0:
                        logger.error(f"Erreur lors de l'installation de Caddy: {result.stderr}")
                        return False
            
            return self.is_caddy_installed()
            
        except Exception as e:
            logger.error(f"Erreur lors de l'installation de Caddy: {e}")
            return False
    
    def generate_caddyfile(self, domain: str, flask_port: int = 5000, 
                          websocket_port: int = 8765, static_dir: str = "/home/ubuntu/src/static",
                          email: str = None, staging: bool = False) -> str:
        """Génère un Caddyfile pour la configuration SSL/TLS"""
        
        # Configuration de base
        config_lines = []
        
        # Configuration globale
        global_config = [
            "{",
            "    # Configuration globale Caddy",
            "    admin off",
            "    log {",
            "        level INFO",
            "    }"
        ]
        
        if email and not domain.startswith('localhost'):
            global_config.extend([
                f"    email {email}",
                "    # Utiliser Let's Encrypt staging pour les tests" if staging else "    # Let's Encrypt production",
                "    acme_ca https://acme-staging-v02.api.letsencrypt.org/directory" if staging else ""
            ])
        
        global_config.append("}")
        config_lines.extend(global_config)
        config_lines.append("")
        
        # Redirection HTTP vers HTTPS (sauf pour localhost en développement)
        if not domain.startswith('localhost'):
            config_lines.extend([
                f"{domain}:80 {{",
                f"    redir https://{domain}{{uri}}",
                "}",
                ""
            ])
        
        # Configuration HTTPS
        https_config = [
            f"{domain}:443 {{" if not domain.startswith('localhost') else f"{domain} {{",
        ]
        
        # Configuration TLS
        if domain.startswith('localhost'):
            https_config.append("    tls internal")
        elif email:
            https_config.extend([
                "    tls {",
                f"        email {email}",
                "    }"
            ])
        
        # Proxies et routes
        https_config.extend([
            "",
            "    # Proxy vers l'API Flask",
            f"    reverse_proxy /api/* localhost:{flask_port}",
            "",
            "    # Proxy WebSocket pour RDP/VNC",
            f"    reverse_proxy /ws/* localhost:{websocket_port} {{",
            "        header_up Upgrade {>Upgrade}",
            "        header_up Connection {>Connection}",
            "    }",
            "",
            "    # Servir les fichiers statiques",
            "    handle_path /static/* {",
            f"        root * {static_dir}",
            "        file_server",
            "    }",
            "",
            "    # Route pour les sessions distantes",
            "    handle_path /remote-session* {",
            f"        root * {static_dir}",
            "        try_files {path} /remote-session.html",
            "        file_server",
            "    }",
            "",
            "    # Application principale",
            f"    reverse_proxy localhost:{flask_port}",
            "",
            "    # Headers de sécurité",
            "    header {",
            "        Strict-Transport-Security \"max-age=31536000; includeSubDomains; preload\"",
            "        X-Content-Type-Options \"nosniff\"",
            "        X-Frame-Options \"SAMEORIGIN\"",
            "        X-XSS-Protection \"1; mode=block\"",
            "        Content-Security-Policy \"default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com; font-src 'self' https://cdnjs.cloudflare.com; connect-src 'self' ws: wss:; img-src 'self' data:;\"",
            "    }",
            "",
            "    # Logs",
            "    log {",
            f"        output file /var/log/caddy/{domain.replace(':', '_')}.log",
            "        format json",
            "    }",
            "}"
        ])
        
        config_lines.extend(https_config)
        
        return "\n".join(config_lines)
    
    def deploy_caddyfile(self, content: str) -> bool:
        """Déploie le Caddyfile généré"""
        try:
            # Créer le répertoire de configuration si nécessaire
            self.config_dir.mkdir(parents=True, exist_ok=True)
            
            # Sauvegarder l'ancien Caddyfile si il existe
            if self.caddyfile_path.exists():
                backup_path = self.caddyfile_path.with_suffix('.bak')
                shutil.copy2(self.caddyfile_path, backup_path)
                logger.info(f"Ancien Caddyfile sauvegardé: {backup_path}")
            
            # Écrire le nouveau Caddyfile
            with open(self.caddyfile_path, 'w') as f:
                f.write(content)
            
            # Vérifier la syntaxe
            if not self.validate_caddyfile():
                logger.error("Erreur de syntaxe dans le Caddyfile")
                return False
            
            logger.info(f"Caddyfile déployé: {self.caddyfile_path}")
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors du déploiement du Caddyfile: {e}")
            return False
    
    def validate_caddyfile(self) -> bool:
        """Valide la syntaxe du Caddyfile"""
        try:
            result = subprocess.run(
                ['caddy', 'validate', '--config', str(self.caddyfile_path)],
                capture_output=True, text=True
            )
            return result.returncode == 0
        except Exception as e:
            logger.error(f"Erreur lors de la validation: {e}")
            return False
    
    def start_caddy(self) -> bool:
        """Démarre le service Caddy"""
        try:
            result = subprocess.run(['sudo', 'systemctl', 'start', self.caddy_service], 
                                  capture_output=True, text=True)
            return result.returncode == 0
        except Exception as e:
            logger.error(f"Erreur lors du démarrage de Caddy: {e}")
            return False
    
    def stop_caddy(self) -> bool:
        """Arrête le service Caddy"""
        try:
            result = subprocess.run(['sudo', 'systemctl', 'stop', self.caddy_service], 
                                  capture_output=True, text=True)
            return result.returncode == 0
        except Exception as e:
            logger.error(f"Erreur lors de l'arrêt de Caddy: {e}")
            return False
    
    def restart_caddy(self) -> bool:
        """Redémarre le service Caddy"""
        try:
            result = subprocess.run(['sudo', 'systemctl', 'restart', self.caddy_service], 
                                  capture_output=True, text=True)
            return result.returncode == 0
        except Exception as e:
            logger.error(f"Erreur lors du redémarrage de Caddy: {e}")
            return False
    
    def reload_caddy(self) -> bool:
        """Recharge la configuration Caddy sans interruption"""
        try:
            result = subprocess.run(['sudo', 'systemctl', 'reload', self.caddy_service], 
                                  capture_output=True, text=True)
            return result.returncode == 0
        except Exception as e:
            logger.error(f"Erreur lors du rechargement de Caddy: {e}")
            return False
    
    def enable_caddy(self) -> bool:
        """Active le service Caddy au démarrage"""
        try:
            result = subprocess.run(['sudo', 'systemctl', 'enable', self.caddy_service], 
                                  capture_output=True, text=True)
            return result.returncode == 0
        except Exception as e:
            logger.error(f"Erreur lors de l'activation de Caddy: {e}")
            return False
    
    def get_caddy_status(self) -> Dict:
        """Récupère le statut du service Caddy"""
        try:
            result = subprocess.run(['sudo', 'systemctl', 'status', self.caddy_service], 
                                  capture_output=True, text=True)
            
            is_active = subprocess.run(['sudo', 'systemctl', 'is-active', self.caddy_service], 
                                     capture_output=True, text=True)
            
            is_enabled = subprocess.run(['sudo', 'systemctl', 'is-enabled', self.caddy_service], 
                                      capture_output=True, text=True)
            
            return {
                'active': is_active.stdout.strip() == 'active',
                'enabled': is_enabled.stdout.strip() == 'enabled',
                'status_output': result.stdout,
                'status_code': result.returncode
            }
        except Exception as e:
            logger.error(f"Erreur lors de la récupération du statut: {e}")
            return {'active': False, 'enabled': False, 'error': str(e)}
    
    def get_certificates_info(self) -> List[Dict]:
        """Récupère les informations sur les certificats SSL"""
        try:
            # Chercher les certificats dans le répertoire de données Caddy
            cert_dir = self.data_dir / "certificates"
            certificates = []
            
            if cert_dir.exists():
                for cert_path in cert_dir.rglob("*.crt"):
                    try:
                        # Utiliser openssl pour lire les informations du certificat
                        result = subprocess.run([
                            'openssl', 'x509', '-in', str(cert_path), 
                            '-text', '-noout'
                        ], capture_output=True, text=True)
                        
                        if result.returncode == 0:
                            # Parser les informations basiques
                            cert_info = {
                                'path': str(cert_path),
                                'domain': cert_path.parent.name,
                                'details': result.stdout
                            }
                            certificates.append(cert_info)
                    except Exception as e:
                        logger.warning(f"Erreur lecture certificat {cert_path}: {e}")
            
            return certificates
            
        except Exception as e:
            logger.error(f"Erreur lors de la récupération des certificats: {e}")
            return []
    
    def setup_ssl_for_domain(self, domain: str, email: str = None, 
                           flask_port: int = 5000, websocket_port: int = 8765,
                           static_dir: str = "/home/ubuntu/src/static",
                           staging: bool = False) -> bool:
        """Configure SSL/TLS automatique pour un domaine"""
        try:
            logger.info(f"Configuration SSL/TLS pour {domain}")
            
            # Vérifier que Caddy est installé
            if not self.is_caddy_installed():
                logger.info("Installation de Caddy...")
                if not self.install_caddy():
                    logger.error("Impossible d'installer Caddy")
                    return False
            
            # Générer le Caddyfile
            caddyfile_content = self.generate_caddyfile(
                domain=domain,
                flask_port=flask_port,
                websocket_port=websocket_port,
                static_dir=static_dir,
                email=email,
                staging=staging
            )
            
            # Déployer la configuration
            if not self.deploy_caddyfile(caddyfile_content):
                logger.error("Impossible de déployer le Caddyfile")
                return False
            
            # Activer et démarrer Caddy
            self.enable_caddy()
            
            if not self.restart_caddy():
                logger.error("Impossible de démarrer Caddy")
                return False
            
            logger.info(f"SSL/TLS configuré avec succès pour {domain}")
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors de la configuration SSL: {e}")
            return False
    
    def create_ssl_setup_script(self, output_path: str = "/home/ubuntu/setup_ssl.sh") -> bool:
        """Crée un script de configuration SSL automatisé"""
        script_content = '''#!/bin/bash

# Script de configuration SSL/TLS automatique pour Lab Creator
# Usage: ./setup_ssl.sh [domain] [email]

set -e

DOMAIN=${1:-"localhost"}
EMAIL=${2:-""}
FLASK_PORT=5000
WEBSOCKET_PORT=8765
STATIC_DIR="/home/ubuntu/src/static"

echo "=== Configuration SSL/TLS pour Lab Creator ==="
echo "Domaine: $DOMAIN"
echo "Email: $EMAIL"
echo ""

# Vérifier les privilèges sudo
if ! sudo -n true 2>/dev/null; then
    echo "Ce script nécessite les privilèges sudo."
    exit 1
fi

# Installer Caddy si nécessaire
if ! command -v caddy &> /dev/null; then
    echo "Installation de Caddy..."
    curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
    curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | sudo tee /etc/apt/sources.list.d/caddy-stable.list
    sudo apt update
    sudo apt install -y caddy
    echo "Caddy installé avec succès."
else
    echo "Caddy est déjà installé."
fi

# Créer les répertoires nécessaires
sudo mkdir -p /etc/caddy
sudo mkdir -p /var/log/caddy
sudo chown caddy:caddy /var/log/caddy

# Générer le Caddyfile
echo "Génération de la configuration Caddy..."
python3 -c "
from src.services.ssl_manager import SSLManager
ssl_manager = SSLManager()
content = ssl_manager.generate_caddyfile('$DOMAIN', $FLASK_PORT, $WEBSOCKET_PORT, '$STATIC_DIR', '$EMAIL')
print(content)
" | sudo tee /etc/caddy/Caddyfile > /dev/null

# Valider la configuration
echo "Validation de la configuration..."
if ! caddy validate --config /etc/caddy/Caddyfile; then
    echo "Erreur dans la configuration Caddy!"
    exit 1
fi

# Activer et démarrer Caddy
echo "Activation et démarrage de Caddy..."
sudo systemctl enable caddy
sudo systemctl restart caddy

# Vérifier le statut
sleep 2
if sudo systemctl is-active --quiet caddy; then
    echo ""
    echo "✅ SSL/TLS configuré avec succès!"
    echo ""
    echo "Votre application est maintenant accessible via:"
    if [[ "$DOMAIN" == "localhost" ]]; then
        echo "  - https://localhost (certificat auto-signé)"
    else
        echo "  - https://$DOMAIN (certificat Let's Encrypt)"
    fi
    echo ""
    echo "Les logs Caddy sont disponibles dans /var/log/caddy/"
else
    echo "❌ Erreur: Caddy n'a pas pu démarrer"
    echo "Vérifiez les logs: sudo journalctl -u caddy -f"
    exit 1
fi
'''
        
        try:
            with open(output_path, 'w') as f:
                f.write(script_content)
            
            # Rendre le script exécutable
            os.chmod(output_path, 0o755)
            
            logger.info(f"Script de configuration SSL créé: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors de la création du script: {e}")
            return False

# Instance globale
ssl_manager = SSLManager()

