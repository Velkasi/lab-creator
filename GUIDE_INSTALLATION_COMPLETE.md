# Guide d'Installation Complet - Lab Creator Enhanced v2.0

## 🚀 Vue d'Ensemble

Lab Creator Enhanced v2.0 est une version considérablement améliorée de l'application originale, incluant des fonctionnalités avancées pour l'accès distant RDP/VNC, l'optimisation des performances, et la sécurité SSL/TLS automatique.

## 📋 Prérequis Système

### Système d'Exploitation
- **Ubuntu 20.04+ / Debian 10+** (recommandé)
- **CentOS 8+ / RHEL 8+** (supporté)
- **Windows 10/11** avec WSL2 (expérimental)

### Ressources Minimales
- **CPU:** 2 cœurs (4 cœurs recommandés)
- **RAM:** 4 GB (8 GB recommandés)
- **Stockage:** 10 GB d'espace libre
- **Réseau:** Connexion Internet pour les certificats SSL

### Logiciels Requis
```bash
# Mise à jour du système
sudo apt update && sudo apt upgrade -y

# Dépendances système
sudo apt install -y python3 python3-pip python3-venv git curl wget unzip
sudo apt install -y build-essential libssl-dev libffi-dev python3-dev
sudo apt install -y postgresql postgresql-contrib  # Optionnel pour production
```

## 📦 Installation

### Étape 1: Téléchargement et Extraction

```bash
# Créer le répertoire d'installation
sudo mkdir -p /opt/lab-creator
cd /opt/lab-creator

# Extraire l'archive (remplacer par le chemin réel)
sudo tar -xzf /path/to/lab-creator-enhanced-v2.tar.gz
sudo chown -R $USER:$USER /opt/lab-creator
```

### Étape 2: Configuration de l'Environnement Python

```bash
# Créer un environnement virtuel
python3 -m venv venv
source venv/bin/activate

# Installer les dépendances
pip install --upgrade pip
pip install -r requirements_updated.txt

# Dépendances supplémentaires pour les fonctionnalités avancées
pip install psutil websockets flask-cors
```

### Étape 3: Configuration de la Base de Données

```bash
# Pour SQLite (développement)
mkdir -p src/database
touch src/database/app.db

# Pour PostgreSQL (production)
sudo -u postgres createdb lab_creator
sudo -u postgres createuser lab_creator_user
sudo -u postgres psql -c "ALTER USER lab_creator_user PASSWORD 'secure_password';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE lab_creator TO lab_creator_user;"
```

### Étape 4: Configuration SSL/TLS avec Caddy

```bash
# Installation de Caddy
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | sudo tee /etc/apt/sources.list.d/caddy-stable.list
sudo apt update
sudo apt install caddy

# Copier la configuration Caddy
sudo cp Caddyfile /etc/caddy/Caddyfile

# Personnaliser la configuration
sudo nano /etc/caddy/Caddyfile
# Remplacer 'localhost' par votre domaine si nécessaire
```

### Étape 5: Configuration des Variables d'Environnement

```bash
# Créer le fichier .env
cat > .env << EOF
# Configuration Flask
FLASK_ENV=production
FLASK_DEBUG=False
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")

# Base de données
# Pour SQLite
DATABASE_URL=sqlite:///$(pwd)/src/database/app.db

# Pour PostgreSQL (décommenter si utilisé)
# DATABASE_URL=postgresql://lab_creator_user:secure_password@localhost/lab_creator

# Serveur
HOST=0.0.0.0
PORT=5000

# SSL/TLS
SSL_ENABLED=true
DOMAIN=localhost  # Remplacer par votre domaine

# Performance
MAX_CONCURRENT_CONNECTIONS=50
CACHE_TTL_DEFAULT=300
MEMORY_THRESHOLD=80
CPU_THRESHOLD=85

# Sécurité
ENABLE_RATE_LIMITING=true
MAX_REQUESTS_PER_MINUTE=100
EOF
```

## 🔧 Configuration Avancée

### Configuration Multi-Écrans

```bash
# Installer les dépendances pour le support multi-écrans
sudo apt install -y xvfb x11vnc

# Configuration pour les sessions VNC multi-écrans
mkdir -p ~/.vnc
cat > ~/.vnc/config << EOF
geometry=1920x1080
depth=24
dpi=96
EOF
```

### Configuration FreeRDP

```bash
# Installation de FreeRDP pour le support RDP complet
sudo apt install -y freerdp2-dev freerdp2-x11

# Configuration des permissions
sudo usermod -a -G video $USER
sudo usermod -a -G audio $USER
```

### Configuration du Firewall

```bash
# Ouvrir les ports nécessaires
sudo ufw allow 5000/tcp   # Flask
sudo ufw allow 8765/tcp   # WebSocket
sudo ufw allow 80/tcp     # HTTP
sudo ufw allow 443/tcp    # HTTPS
sudo ufw allow 5900:5999/tcp  # VNC
sudo ufw allow 3389/tcp   # RDP

# Activer le firewall
sudo ufw --force enable
```

## 🚀 Démarrage de l'Application

### Mode Développement

```bash
# Activer l'environnement virtuel
source venv/bin/activate

# Démarrer l'application
cd /opt/lab-creator
PYTHONPATH=/opt/lab-creator python3 src/main.py
```

### Mode Production avec Systemd

```bash
# Créer le service systemd
sudo tee /etc/systemd/system/lab-creator.service > /dev/null << EOF
[Unit]
Description=Lab Creator Enhanced
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=/opt/lab-creator
Environment=PATH=/opt/lab-creator/venv/bin
Environment=PYTHONPATH=/opt/lab-creator
ExecStart=/opt/lab-creator/venv/bin/python src/main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Activer et démarrer le service
sudo systemctl daemon-reload
sudo systemctl enable lab-creator
sudo systemctl start lab-creator

# Démarrer Caddy pour SSL/TLS
sudo systemctl enable caddy
sudo systemctl start caddy
```

### Vérification du Démarrage

```bash
# Vérifier le statut des services
sudo systemctl status lab-creator
sudo systemctl status caddy

# Tester l'API
curl http://localhost:5000/api/performance/health

# Tester l'interface web
curl http://localhost:5000/
```

## 🔍 Dépannage

### Problèmes Courants

#### 1. Erreur WebSocket "no running event loop"
```bash
# Solution temporaire: redémarrer l'application
sudo systemctl restart lab-creator

# Solution permanente: vérifier la configuration asyncio
# (Correction incluse dans les prochaines versions)
```

#### 2. Timeout lors des requêtes HTTP
```bash
# Vérifier les ressources système
htop
df -h

# Optimiser la configuration
nano .env
# Réduire MAX_CONCURRENT_CONNECTIONS à 25
# Augmenter CACHE_TTL_DEFAULT à 600
```

#### 3. Problèmes de certificats SSL
```bash
# Vérifier la configuration Caddy
sudo caddy validate --config /etc/caddy/Caddyfile

# Forcer le renouvellement des certificats
sudo caddy reload --config /etc/caddy/Caddyfile
```

#### 4. Connexions RDP/VNC qui échouent
```bash
# Vérifier les ports
sudo netstat -tlnp | grep -E '(5900|3389|8765)'

# Vérifier les logs
sudo journalctl -u lab-creator -f
```

### Logs et Monitoring

```bash
# Logs de l'application
sudo journalctl -u lab-creator -f

# Logs Caddy
sudo journalctl -u caddy -f

# Monitoring des performances
# Accéder à http://localhost:5000/performance (une fois l'interface créée)
```

## 📊 Monitoring et Maintenance

### Surveillance des Performances

L'application inclut un système de monitoring intégré accessible via l'interface web:

- **URL:** `http://votre-domaine/performance`
- **Métriques:** CPU, mémoire, connexions, temps de réponse
- **Alertes:** Seuils configurables pour les ressources critiques

### Maintenance Régulière

```bash
# Script de maintenance hebdomadaire
cat > /opt/lab-creator/maintenance.sh << 'EOF'
#!/bin/bash
# Nettoyage des logs anciens
sudo journalctl --vacuum-time=7d

# Nettoyage du cache application
curl -X POST http://localhost:5000/api/performance/cache/clear

# Nettoyage des connexions expirées
curl -X POST http://localhost:5000/api/performance/connections/cleanup?aggressive=true

# Sauvegarde de la base de données
if [ -f "src/database/app.db" ]; then
    cp src/database/app.db backups/app_$(date +%Y%m%d).db
fi

echo "Maintenance terminée: $(date)"
EOF

chmod +x /opt/lab-creator/maintenance.sh

# Ajouter au crontab
(crontab -l 2>/dev/null; echo "0 2 * * 0 /opt/lab-creator/maintenance.sh >> /var/log/lab-creator-maintenance.log 2>&1") | crontab -
```

## 🔐 Sécurité

### Recommandations de Sécurité

1. **Changer les mots de passe par défaut**
2. **Utiliser HTTPS en production**
3. **Configurer un reverse proxy (Nginx/Apache)**
4. **Activer les logs d'audit**
5. **Mettre à jour régulièrement les dépendances**

### Configuration Nginx (Optionnel)

```nginx
# /etc/nginx/sites-available/lab-creator
server {
    listen 80;
    server_name votre-domaine.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name votre-domaine.com;

    ssl_certificate /path/to/certificate.crt;
    ssl_certificate_key /path/to/private.key;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /ws/ {
        proxy_pass http://127.0.0.1:8765;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

## 📞 Support

### Documentation
- **Architecture:** `architecture_analysis.md`
- **Changelog:** `CHANGELOG_RDP_VNC.md`
- **Tests:** `test_results_enhanced.md`

### Problèmes Connus
- WebSocket server nécessite une refactorisation pour la stabilité
- Performance de démarrage à optimiser
- Support RDP complet en cours de finalisation

### Contact
Pour le support technique, consultez la documentation incluse ou créez un ticket avec les logs d'erreur.

---

**Version:** Lab Creator Enhanced v2.0  
**Date:** Août 2025  
**Licence:** Selon les termes du projet original

