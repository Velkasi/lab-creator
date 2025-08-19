#!/bin/bash

# Script d'installation pour Lab Creator Enhanced v2.0

# Fonction pour afficher les messages d'erreur et quitter
function error_exit {
    echo "Erreur: $1" >&2
    exit 1
}

echo "Démarrage du script d'installation de Lab Creator Enhanced v2.0..."

# 1. Vérifier les prérequis système
echo "Vérification des prérequis système..."

# Vérifier l'OS (Ubuntu/Debian)
if [[ -f /etc/os-release ]]; then
    . /etc/os-release
    if [[ "$ID" != "ubuntu" && "$ID" != "debian" ]]; then
        error_exit "Ce script est conçu pour Ubuntu ou Debian. Votre OS est $ID."
    fi
else
    error_exit "Impossible de détecter le système d'exploitation. Ce script est conçu pour Ubuntu ou Debian."
fi

# Vérifier la version de Python (3.8+)
PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")' 2>/dev/null)
if [[ $? -ne 0 ]]; then
    error_exit "Python 3 n'est pas installé ou n'est pas accessible via 'python3'. Veuillez l'installer."
fi

PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d'.' -f1)
PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d'.' -f2)

if (( PYTHON_MAJOR < 3 || (PYTHON_MAJOR == 3 && PYTHON_MINOR < 8) )); then
    error_exit "Python 3.8 ou supérieur est requis. Version actuelle: $PYTHON_VERSION. Veuillez mettre à jour Python."
fi

echo "Prérequis système vérifiés avec succès."

# Rendre le script exécutable
chmod +x install.sh

# Continuer avec les étapes d'installation...




# 2. Installer les dépendances système
echo "Installation des dépendances système (peut prendre quelques minutes)..."
sudo apt update || error_exit "Échec de la mise à jour des paquets."
sudo apt install -y python3 python3-pip python3-venv tar || error_exit "Échec de l'installation des dépendances système."
echo "Dépendances système installées avec succès."




# 3. Extraction de l'archive de l'application (modifier le chemin en fonction de votre utilisateur)
echo "Extraction de l'archive de l'application..."
APP_ARCHIVE="/home/test/Téléchargements/lab-creator-main.zip"
APP_DIR="/home/test/Téléchargements/lab-creator-main"

if [ ! -f "$APP_ARCHIVE" ]; then
    error_exit "L'archive de l'application n'a pas été trouvée à $APP_ARCHIVE."
fi

mkdir -p "$APP_DIR" || error_exit "Échec de la création du répertoire de l'application."
unzip -q "$APP_ARCHIVE" -d "$APP_DIR" || error_exit "Échec de l'extraction de l'archive."
echo "Archive extraite avec succès dans $APP_DIR."

cd "$APP_DIR" || error_exit "Impossible de naviguer vers le répertoire de l'application."

# Copier le fichier requirements_updated.txt dans le répertoire de l'application
# cp /home/ubuntu/requirements_updated.txt "$APP_DIR" || error_exit "Échec de la copie de requirements_updated.txt."

# 4. Créer et activer l'environnement virtuel Python
echo "Création et activation de l'environnement virtuel Python..."
python3 -m venv venv || error_exit "Échec de la création de l'environnement virtuel."
source venv/bin/activate || error_exit "Échec de l'activation de l'environnement virtuel."
echo "Environnement virtuel activé."

# 5. Installer les dépendances Python
echo "Installation des dépendances Python..."
pip install -r "$APP_DIR/requirements_updated.txt" || error_exit "Échec de l'installation des dépendances Python."
echo "Dépendances Python installées avec succès."

# 6. Configurer l'environnement
echo "Configuration de l'environnement..."
if [ -f ".env.example" ]; then
    cp .env.example .env || error_exit "Échec de la copie de .env.example vers .env."
    echo "Fichier .env créé. Veuillez le modifier si nécessaire pour personnaliser la configuration."
else
    echo "Le fichier .env.example n'a pas été trouvé. Veuillez créer un fichier .env manuellement si nécessaire."
fi

echo "Configuration de l'environnement terminée."

# 7. Instructions pour démarrer l'application
echo "\nInstallation terminée avec succès !"
echo "Pour démarrer l'application, naviguez vers le répertoire de l'application et exécutez:"
echo "cd $APP_DIR"
echo "source venv/bin/activate"
echo "PYTHONPATH=$(pwd) python3 src/main.py"
echo "\nL'application sera accessible via http://localhost:5000 (ou l'adresse configurée dans .env)."




# Copier le fichier requirements_updated.txt dans le répertoire de l'application
# cp /home/ubuntu/requirements_updated.txt "$APP_DIR" || error_exit "Échec de la copie de requirements_updated.txt."


