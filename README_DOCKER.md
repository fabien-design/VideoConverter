# Video Converter - Docker Deployment Guide

Guide complet pour déployer Video Converter sur un VPS Debian avec Docker.

## 🚀 Installation Rapide

### 1. Prérequis sur le VPS

```bash
# Mettre à jour le système
sudo apt update && sudo apt upgrade -y

# Installer Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Installer Docker Compose
sudo apt install docker-compose-plugin -y

# Ajouter votre utilisateur au groupe docker (optionnel)
sudo usermod -aG docker $USER
# Se déconnecter et reconnecter pour appliquer
```

### 2. Déployer le projet

```bash
# Cloner ou copier le projet
cd /opt
sudo git clone <votre-repo> video-converter
cd video-converter

# Créer le fichier .env
cp .env.example .env
nano .env  # Modifier les chemins RAW_DIR et PUBLIC_DIR
```

### 3. Configuration des chemins

Éditez `.env` pour spécifier vos répertoires :

```bash
# Exemple pour un VPS avec stockage externe
RAW_DIR=/mnt/storage/videos/raw
PUBLIC_DIR=/mnt/storage/videos/public

# Ou chemins locaux
RAW_DIR=/home/user/videos/raw
PUBLIC_DIR=/var/www/videos

# Planning (toutes les heures par défaut)
CRON_SCHEDULE=0 * * * *
```

### 4. Créer les répertoires

```bash
# Créer les répertoires s'ils n'existent pas
sudo mkdir -p /mnt/storage/videos/raw
sudo mkdir -p /mnt/storage/videos/public

# Permissions (ajuster selon vos besoins)
sudo chown -R $USER:$USER /mnt/storage/videos
```

### 5. Lancer le conteneur

```bash
# Build et démarrage
docker compose up -d

# Vérifier les logs
docker compose logs -f

# Voir le statut
docker compose ps
```

## 📋 Configuration Détaillée

### Variables d'environnement (.env)

| Variable | Description | Défaut | Exemples |
|----------|-------------|--------|----------|
| `RAW_DIR` | Dossier source (lecture seule) | `./files/raw` | `/mnt/videos/raw` |
| `PUBLIC_DIR` | Dossier de sortie | `./files/public` | `/var/www/videos` |
| `CRON_SCHEDULE` | Planning cron | `0 * * * *` | `*/30 * * * *` (toutes les 30min) |
| `RUN_ON_START` | Exécuter au démarrage | `true` | `true` / `false` |
| `CPU_LIMIT` | Limite CPU | `4.0` | `2.0`, `8.0` |
| `MEMORY_LIMIT` | Limite mémoire | `2G` | `1G`, `4G` |

### Exemples de planification cron

```bash
# Toutes les 30 minutes
CRON_SCHEDULE=*/30 * * * *

# Toutes les 6 heures
CRON_SCHEDULE=0 */6 * * *

# Tous les jours à 2h du matin
CRON_SCHEDULE=0 2 * * *

# Toutes les 2 heures entre 8h et 20h
CRON_SCHEDULE=0 8-20/2 * * *
```

## 🔧 Commandes Docker Utiles

### Gestion du conteneur

```bash
# Démarrer
docker compose up -d

# Arrêter
docker compose down

# Redémarrer
docker compose restart

# Reconstruire l'image
docker compose build --no-cache

# Voir les logs en temps réel
docker compose logs -f

# Voir les logs des 100 dernières lignes
docker compose logs --tail=100

# Voir uniquement les logs du cron
docker exec video-converter tail -f /var/log/cron.log
```

### Exécuter une conversion manuelle

```bash
# Lancer une conversion immédiatement
docker exec video-converter python main.py

# Voir la progression en temps réel
docker exec -it video-converter python main.py
```

### Vérifier l'état

```bash
# Statistiques en temps réel
docker stats video-converter

# Processus en cours
docker top video-converter

# Informations du conteneur
docker inspect video-converter
```

## 📊 Monitoring et Logs

### Accéder aux logs

```bash
# Logs du script principal
docker exec video-converter tail -f /app/sync.log

# Logs du cron
docker exec video-converter tail -f /var/log/cron.log

# Logs Docker
docker compose logs -f --tail=100
```

### Vérifier le fichier de verrouillage

```bash
# Voir si une conversion est en cours
docker exec video-converter cat /app/.sync.lock

# Supprimer le lock manuellement (si bloqué)
docker exec video-converter rm -f /app/.sync.lock
```

### Vérifier les métadonnées de progression

```bash
# Lister les fichiers de progression
docker exec video-converter ls -lah /app/.progress/

# Voir le contenu d'une métadonnée
docker exec video-converter cat /app/.progress/<hash>.json
```

## 🔄 Mise à jour du conteneur

```bash
# Arrêter le conteneur
docker compose down

# Récupérer les dernières modifications
git pull  # ou copier le nouveau main.py

# Reconstruire l'image
docker compose build --no-cache

# Redémarrer
docker compose up -d

# Vérifier les logs
docker compose logs -f
```

## 🛠️ Troubleshooting

### Le conteneur ne démarre pas

```bash
# Vérifier les logs d'erreur
docker compose logs

# Vérifier que les chemins existent
ls -la $RAW_DIR
ls -la $PUBLIC_DIR

# Vérifier les permissions
docker exec video-converter ls -la /app/files/
```

### Pas de conversions

```bash
# Vérifier le planning cron
docker exec video-converter crontab -l

# Voir les logs du cron
docker exec video-converter tail -f /var/log/cron.log

# Tester manuellement
docker exec -it video-converter python main.py
```

### Performances lentes

```bash
# Augmenter les limites CPU/RAM dans .env
CPU_LIMIT=8.0
MEMORY_LIMIT=4G

# Redémarrer avec les nouvelles limites
docker compose down
docker compose up -d

# Vérifier l'utilisation
docker stats video-converter
```

### Espace disque insuffisant

```bash
# Nettoyer les images Docker non utilisées
docker system prune -a

# Nettoyer les volumes orphelins
docker volume prune

# Vérifier l'espace
df -h
```

## 🔐 Sécurité et Permissions

### Permissions recommandées

```bash
# RAW_DIR en lecture seule (ro dans compose.yaml)
chmod -R 755 $RAW_DIR

# PUBLIC_DIR en lecture/écriture
chmod -R 755 $PUBLIC_DIR

# Le conteneur tourne en tant que root par défaut
# Pour plus de sécurité, vous pouvez ajouter dans compose.yaml :
# user: "1000:1000"  # UID:GID de votre utilisateur
```

### Backup des métadonnées

```bash
# Backup du volume de progression
docker run --rm -v video-converter_progress-data:/data -v $(pwd):/backup \
  alpine tar czf /backup/progress-backup.tar.gz -C /data .

# Restauration
docker run --rm -v video-converter_progress-data:/data -v $(pwd):/backup \
  alpine tar xzf /backup/progress-backup.tar.gz -C /data
```

## 🌐 Intégration avec un serveur web

### Nginx pour servir les vidéos

```nginx
server {
    listen 80;
    server_name videos.exemple.com;

    location / {
        alias /mnt/storage/videos/public/;
        autoindex on;

        # Headers pour le streaming
        add_header Cache-Control "public, max-age=3600";
        add_header Accept-Ranges bytes;
    }
}
```

### Synchronisation avec rsync

```bash
# Copier les RAW depuis un autre serveur
rsync -avz --progress user@source:/videos/ /mnt/storage/videos/raw/

# Script de synchronisation automatique (sur le VPS)
#!/bin/bash
rsync -avz --progress user@source:/videos/ /mnt/storage/videos/raw/
```

## 📈 Optimisations

### Pour un VPS avec beaucoup de RAM

```bash
# Dans .env
MEMORY_LIMIT=8G
CPU_LIMIT=8.0
```

### Pour limiter l'utilisation des ressources

```bash
# Dans .env
MEMORY_LIMIT=1G
CPU_LIMIT=2.0

# Modifier le script pour baisser cpu-used dans FFMPEG_SETTINGS
# Dans main.py: '-cpu-used', '4' (au lieu de '2')
```

## 🎯 Exemple de déploiement complet

```bash
# 1. Installation sur VPS Debian
ssh user@your-vps.com
sudo apt update && sudo apt upgrade -y
curl -fsSL https://get.docker.com | sudo sh

# 2. Créer la structure
sudo mkdir -p /opt/video-converter
sudo chown $USER:$USER /opt/video-converter
cd /opt/video-converter

# 3. Copier les fichiers (via git ou scp)
# Option A: Git
git clone https://github.com/votre-repo/video-converter.git .

# Option B: SCP depuis votre machine
# scp -r * user@vps:/opt/video-converter/

# 4. Configuration
cp .env.example .env
nano .env  # Configurer les chemins

# Exemple de configuration
cat > .env << 'EOF'
RAW_DIR=/mnt/storage/raw
PUBLIC_DIR=/var/www/html/videos
CRON_SCHEDULE=0 */2 * * *
RUN_ON_START=true
CPU_LIMIT=4.0
MEMORY_LIMIT=2G
EOF

# 5. Créer les dossiers
sudo mkdir -p /mnt/storage/raw
sudo mkdir -p /var/www/html/videos
sudo chown -R www-data:www-data /var/www/html/videos

# 6. Lancer
docker compose up -d

# 7. Vérifier
docker compose logs -f
```

## 📞 Support

En cas de problème :
1. Vérifiez les logs : `docker compose logs -f`
2. Vérifiez ffmpeg : `docker exec video-converter ffmpeg -version`
3. Testez manuellement : `docker exec -it video-converter python main.py`
4. Vérifiez les permissions des volumes montés
