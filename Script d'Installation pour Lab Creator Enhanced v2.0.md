# Script d'Installation pour Lab Creator Enhanced v2.0

Ce script automatise le processus d'installation de l'application Lab Creator Enhanced v2.0 sur les systèmes d'exploitation basés sur Debian/Ubuntu.

## Prérequis

Avant d'exécuter ce script, assurez-vous que votre système répond aux exigences suivantes :

- **Système d'exploitation :** Ubuntu 20.04+ ou Debian 10+
- **Python :** Python 3.8 ou supérieur doit être installé et accessible via la commande `python3`.
- **RAM :** Minimum 4 Go (8 Go recommandés).
- **Connexion Internet :** Nécessaire pour télécharger les dépendances et les certificats SSL/TLS (si configuré).

## Utilisation

Suivez les étapes ci-dessous pour installer l'application :

1.  **Téléchargez l'archive de l'application :**
    Assurez-vous que le fichier `lab-creator-enhanced-v2-FINAL.tar.gz` est présent dans le répertoire `/home/ubuntu/upload/`.

2.  **Exécutez le script d'installation :**
    Ouvrez un terminal et exécutez les commandes suivantes :

    ```bash
    cd /home/ubuntu/
    chmod +x install.sh
    ./install.sh
    ```

    Le script vérifiera les prérequis, installera les dépendances système et Python, extraira l'application, créera un environnement virtuel et installera toutes les dépendances Python nécessaires.

## Après l'Installation

Une fois le script terminé, l'application sera installée dans le répertoire `/home/ubuntu/lab-creator-enhanced-v2-FINAL/`.

### Configuration de l'environnement

Le script tentera de copier un fichier `.env.example` (s'il existe dans l'archive) vers `.env` dans le répertoire de l'application. Vous devrez peut-être modifier ce fichier `.env` pour personnaliser la configuration de l'application (par exemple, les ports, les bases de données, etc.).

### Démarrage de l'application

Pour démarrer l'application, naviguez vers le répertoire de l'application et exécutez les commandes suivantes :

```bash
cd /home/ubuntu/lab-creator-enhanced-v2-FINAL
source venv/bin/activate
PYTHONPATH=$(pwd) python3 src/main.py
```

L'application sera accessible via `http://localhost:5000` (ou l'adresse configurée dans votre fichier `.env`).

## Dépannage

-   **Erreur de prérequis :** Si le script échoue lors de la vérification des prérequis, assurez-vous que votre système répond aux exigences listées ci-dessus.
-   **Dépendances manquantes :** Si des erreurs surviennent lors de l'installation des dépendances, vérifiez votre connexion Internet et les permissions.
-   **Fichier `.env.example` manquant :** Si le script indique que `.env.example` n'a pas été trouvé, vous devrez créer un fichier `.env` manuellement avec les configurations nécessaires.

Pour toute autre question ou problème, veuillez consulter la documentation complète de l'application fournie dans l'archive (`GUIDE_INSTALLATION_COMPLETE.md`, `NOTES_TECHNIQUES.md`, etc.).


