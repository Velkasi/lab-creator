# Guide d'Installation - Fonctionnalités RDP/VNC

## 🎯 Prérequis

### Système
- Lab Creator existant fonctionnel
- Python 3.8+ avec pip
- Accès root ou sudo
- Ports 5000 et 8765 disponibles

### Machines Virtuelles
- **Pour VNC** : Serveur VNC installé (vncserver, tigervnc, etc.)
- **Pour RDP** : Service RDP activé (Windows) ou xrdp (Linux)
- Pare-feu configuré pour autoriser les connexions

## 📦 Installation

### 1. Sauvegarde
```bash
# Sauvegarder l'installation existante
sudo systemctl stop lab-creator
cp -r /opt/lab-creator /opt/lab-creator.backup
```

### 2. Déploiement
```bash
# Extraire la nouvelle version
tar -xzf lab-creator-with-rdp-vnc.tar.gz
cd lab-creator-with-rdp-vnc

# Copier les fichiers
sudo cp -r src/* /opt/lab-creator/src/
sudo cp requirements.txt /opt/lab-creator/
```

### 3. Dépendances
```bash
# Installer les nouvelles dépendances
cd /opt/lab-creator
source venv/bin/activate
pip install -r requirements.txt
```

### 4. Base de Données
```bash
# Les nouvelles tables seront créées automatiquement
# Aucune migration manuelle nécessaire
```

### 5. Configuration
```bash
# Vérifier la configuration
sudo nano /opt/lab-creator/.env

# Ajouter si nécessaire :
WEBSOCKET_HOST=0.0.0.0
WEBSOCKET_PORT=8765
```

### 6. Pare-feu
```bash
# Autoriser le port WebSocket
sudo ufw allow 8765
sudo ufw reload
```

### 7. Redémarrage
```bash
# Redémarrer le service
sudo systemctl start lab-creator
sudo systemctl status lab-creator
```

## 🔧 Configuration des VMs

### Configuration VNC (Linux)
```bash
# Installer VNC server
sudo apt update
sudo apt install tigervnc-standalone-server

# Configurer VNC pour un utilisateur
vncserver :1
vncpasswd

# Démarrer VNC au boot
sudo systemctl enable vncserver@:1
sudo systemctl start vncserver@:1
```

### Configuration RDP (Windows)
```powershell
# Activer RDP via PowerShell (Admin)
Set-ItemProperty -Path 'HKLM:\System\CurrentControlSet\Control\Terminal Server' -name "fDenyTSConnections" -value 0
Enable-NetFirewallRule -DisplayGroup "Remote Desktop"
```

### Configuration RDP (Linux)
```bash
# Installer xrdp
sudo apt update
sudo apt install xrdp

# Configurer et démarrer
sudo systemctl enable xrdp
sudo systemctl start xrdp

# Autoriser dans le pare-feu
sudo ufw allow 3389
```

## 🧪 Tests

### 1. Test de l'API
```bash
# Tester l'API REST
curl http://localhost:5000/api/remote-access/info/1

# Réponse attendue :
{
  "machine_id": 1,
  "machine_name": "test-vm",
  "available_types": ["vnc"],
  "status": "running"
}
```

### 2. Test WebSocket
```bash
# Vérifier que le serveur WebSocket écoute
netstat -tlnp | grep 8765

# Réponse attendue :
tcp 0 0 0.0.0.0:8765 0.0.0.0:* LISTEN 1234/python3
```

### 3. Test Interface Web
1. Ouvrir http://localhost:5000
2. Naviguer vers une machine en cours d'exécution
3. Cliquer sur "Accès Distant"
4. Tester la connexion VNC

## 🐛 Dépannage

### Problème : WebSocket ne démarre pas
```bash
# Vérifier les logs
sudo journalctl -u lab-creator -f

# Solution : Redémarrer le service
sudo systemctl restart lab-creator
```

### Problème : Connexion VNC échoue
```bash
# Vérifier que VNC fonctionne sur la VM
ssh user@vm-ip
netstat -tlnp | grep 5901

# Vérifier la connectivité
telnet vm-ip 5901
```

### Problème : Interface web ne se charge pas
```bash
# Vérifier les permissions des fichiers statiques
sudo chown -R lab-creator:lab-creator /opt/lab-creator/src/static/

# Vérifier les logs Flask
tail -f /opt/lab-creator/logs/app.log
```

### Problème : Erreurs de base de données
```bash
# Recréer la base de données si nécessaire
cd /opt/lab-creator
source venv/bin/activate
python3 -c "from src.main import app, db; app.app_context().push(); db.create_all()"
```

## 📊 Monitoring

### Logs Importants
```bash
# Logs de l'application
tail -f /opt/lab-creator/logs/app.log

# Logs système
sudo journalctl -u lab-creator -f

# Logs WebSocket (dans les logs de l'application)
grep "WebSocket" /opt/lab-creator/logs/app.log
```

### Métriques à Surveiller
- Nombre de connexions WebSocket actives
- Utilisation CPU/RAM lors des connexions VNC
- Temps de réponse des APIs
- Erreurs de connexion

## 🔒 Sécurité

### Recommandations
1. **HTTPS** : Configurer un reverse proxy avec SSL
2. **Authentification** : Intégrer avec le système d'auth existant
3. **Pare-feu** : Limiter l'accès aux ports nécessaires
4. **Chiffrement** : Utiliser WSS (WebSocket Secure) en production

### Configuration SSL (Nginx)
```nginx
server {
    listen 443 ssl;
    server_name your-domain.com;
    
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    
    location / {
        proxy_pass http://localhost:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
    
    location /ws/ {
        proxy_pass http://localhost:8765;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

## 📈 Performance

### Optimisations Recommandées
1. **Limite de connexions** : Configurer un maximum de connexions simultanées
2. **Timeout** : Ajuster les timeouts WebSocket
3. **Compression** : Activer la compression pour VNC
4. **Cache** : Mettre en cache les ressources statiques

### Configuration de Production
```python
# Dans src/main.py, ajouter :
app.config['MAX_WEBSOCKET_CONNECTIONS'] = 50
app.config['WEBSOCKET_TIMEOUT'] = 300  # 5 minutes
```

---

**Support** : En cas de problème, consulter les logs et la documentation technique dans `architecture_analysis.md` et `test_results.md`.

