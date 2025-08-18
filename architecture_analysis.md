# Analyse Architecturale : Intégration RDP/VNC dans Lab Creator

## Contexte
Le projet Lab Creator est une application web complète pour créer et gérer des environnements de laboratoire virtuels (VMs). Il utilise :
- Backend : Flask (Python)
- Frontend : React (dans src/static/)
- Infrastructure : Terraform + Ansible
- Base de données : SQLite

## Objectif
Ajouter une interface web graphique avec fonctionnalités RDP/VNC pour permettre l'accès direct aux VMs créées via l'interface web.

## Options Techniques Analysées

### 1. Apache Guacamole
**Avantages :**
- Solution complète et mature
- Support natif RDP, VNC, SSH
- API bien documentée pour intégration
- Authentification intégrée
- Gestion centralisée des connexions

**Inconvénients :**
- Architecture complexe (nécessite Tomcat, base de données)
- Installation lourde
- Intégration plus complexe dans l'application existante

### 2. noVNC
**Avantages :**
- Léger et simple à intégrer
- Client VNC pur JavaScript/HTML5
- Pas de dépendances serveur lourdes
- Intégration directe possible dans React
- Très populaire (12.8k stars GitHub)

**Inconvénients :**
- Support VNC uniquement (pas RDP natif)
- Nécessite websockify pour proxy WebSocket
- Moins de fonctionnalités avancées

### 3. Solution Hybride Recommandée
Utiliser **noVNC** comme base avec des extensions pour RDP :
- noVNC pour les connexions VNC
- Proxy WebSocket personnalisé pour RDP via FreeRDP
- Interface unifiée dans React

## Architecture Proposée

### Backend (Flask)
```
/api/remote-access/
├── /connections          # Gestion des connexions actives
├── /vnc/{lab_id}/{vm_id} # Endpoint WebSocket VNC
├── /rdp/{lab_id}/{vm_id} # Endpoint WebSocket RDP
└── /status/{connection_id} # Statut des connexions
```

### Frontend (React)
```
src/components/RemoteAccess/
├── RemoteDesktop.jsx     # Composant principal
├── VNCViewer.jsx         # Intégration noVNC
├── RDPViewer.jsx         # Client RDP personnalisé
└── ConnectionManager.jsx # Gestion des connexions
```

### Services
```
src/services/
├── websocket_proxy.py    # Proxy WebSocket pour VNC/RDP
├── connection_manager.py # Gestion des connexions
└── remote_access_service.py # Service métier
```

## Points d'Intégration Identifiés

### 1. Modèles de Données
- Étendre le modèle `Machine` pour inclure les informations de connexion
- Ajouter un modèle `RemoteConnection` pour tracker les sessions

### 2. Interface Utilisateur
- Ajouter un bouton "Accès Distant" dans la liste des VMs
- Modal/page dédiée pour l'affichage du bureau distant
- Indicateurs de statut de connexion

### 3. Sécurité
- Authentification via les sessions existantes
- Chiffrement des connexions WebSocket
- Gestion des timeouts et déconnexions

### 4. Configuration
- Paramètres de connexion par VM (port VNC/RDP, credentials)
- Configuration des proxies WebSocket
- Gestion des certificats SSL

## Prochaines Étapes
1. Implémenter le proxy WebSocket pour noVNC
2. Créer les endpoints API Flask
3. Développer les composants React
4. Intégrer avec la gestion existante des labs
5. Tests et validation

