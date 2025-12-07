# Guide de Déploiement VPS - Production

Guide étape par étape pour déployer Video Converter sur un VPS Debian en production.

## 📋 Prérequis

- VPS Debian 11/12 (ou Ubuntu 20.04+)
- Accès SSH
- Au moins 2GB RAM
- Espace disque suffisant pour les vidéos

## 🚀 Déploiement Automatique (Recommandé)

### Option 1 : Quick Start Script

```bash
# Se connecter au VPS
ssh user@your-vps.com

# Télécharger le projet
git clone https://github.com/votre-repo/video-converter.git
cd video-converter

# Rendre le script exécutable et lancer
chmod +x quickstart.sh
./quickstart.sh
```

Le script va :
1. ✅ Installer Docker (si nécessaire)
2. ✅ Créer le fichier `.env` interactivement
3. ✅ Créer les répertoires RAW et PUBLIC
4. ✅ Builder l'image Docker
5. ✅ Démarrer le conteneur

### Option 2 : Makefile

```bash
# Installation initiale
make install    # Créer .env depuis .env.example
nano .env       # Configurer les chemins

# Déploiement
make build      # Builder l'image
make up         # Démarrer le conteneur

# Vérification
make status     # Voir l'état
make logs       # Voir les logs
```

## 🔧 Déploiement Manuel

### 1. Installer Docker

```bash
# Mettre à jour le système
sudo apt update && sudo apt upgrade -y

# Installer Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Installer Docker Compose
sudo apt install docker-compose-plugin -y

# Ajouter votre utilisateur au groupe docker
sudo usermod -aG docker $USER

# Se déconnecter et reconnecter pour appliquer les changements
exit
```

### 2. Préparer le projet

```bash
# Se reconnecter au VPS
ssh user@your-vps.com

# Créer le répertoire du projet
sudo mkdir -p /opt/video-converter
sudo chown $USER:$USER /opt/video-converter
cd /opt/video-converter

# Cloner ou copier les fichiers
git clone https://github.com/votre-repo/video-converter.git .
# OU
# scp -r * user@vps:/opt/video-converter/
```

### 3. Configuration

```bash
# Copier le template de configuration
cp .env.example .env

# Éditer la configuration
nano .env
```

Configuration minimale dans `.env` :
```bash
RAW_DIR=/mnt/videos/raw
PUBLIC_DIR=/var/www/html/videos
CRON_SCHEDULE=0 * * * *
RUN_ON_START=true
```

### 4. Créer les répertoires

```bash
# Créer les répertoires de stockage
sudo mkdir -p /mnt/videos/raw
sudo mkdir -p /var/www/html/videos

# Définir les permissions
sudo chown -R $USER:$USER /mnt/videos
sudo chown -R www-data:www-data /var/www/html/videos
sudo chmod -R 755 /var/www/html/videos
```

### 5. Lancer le conteneur

```bash
# Builder l'image
docker compose build

# Démarrer le conteneur
docker compose up -d

# Vérifier les logs
docker compose logs -f
```

## 🌐 Configuration Nginx (Optionnel)

Si vous voulez servir les vidéos via HTTP :

```bash
# Installer Nginx
sudo apt install nginx -y

# Créer la configuration
sudo nano /etc/nginx/sites-available/videos
```

Contenu du fichier :
```nginx
server {
    listen 80;
    server_name videos.votre-domaine.com;

    # Optionnel : Redirection HTTPS
    # return 301 https://$server_name$request_uri;

    location / {
        alias /var/www/html/videos/;
        autoindex on;
        autoindex_exact_size off;
        autoindex_localtime on;

        # Headers pour le streaming
        add_header Cache-Control "public, max-age=3600";
        add_header Accept-Ranges bytes;

        # CORS (si nécessaire)
        add_header Access-Control-Allow-Origin *;
    }

    # Logs
    access_log /var/log/nginx/videos-access.log;
    error_log /var/log/nginx/videos-error.log;
}
```

Activer et redémarrer :
```bash
sudo ln -s /etc/nginx/sites-available/videos /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

## 🔐 Sécurité

### Pare-feu (UFW)

```bash
# Installer UFW si nécessaire
sudo apt install ufw -y

# Autoriser SSH
sudo ufw allow 22/tcp

# Autoriser HTTP/HTTPS (si Nginx)
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# Activer le pare-feu
sudo ufw enable
```

### Mises à jour automatiques

```bash
# Installer unattended-upgrades
sudo apt install unattended-upgrades -y

# Configurer
sudo dpkg-reconfigure -plow unattended-upgrades
```

### Limiter l'accès SSH

```bash
# Éditer la config SSH
sudo nano /etc/ssh/sshd_config

# Recommandations :
# - PermitRootLogin no
# - PasswordAuthentication no (si vous utilisez des clés SSH)
# - Port 2222 (changer le port par défaut)

# Redémarrer SSH
sudo systemctl restart sshd
```

## 📊 Monitoring

### Vérifier l'état du conteneur

```bash
# Status
docker compose ps

# Stats en temps réel
docker stats video-converter

# Logs
docker compose logs -f --tail=100

# Logs du cron
docker exec video-converter tail -f /var/log/cron.log

# Logs du sync
docker exec video-converter tail -f /app/sync.log
```

### Monitoring avec Portainer (Optionnel)

```bash
# Installer Portainer pour une interface web
docker volume create portainer_data

docker run -d \
  -p 9000:9000 \
  --name portainer \
  --restart always \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v portainer_data:/data \
  portainer/portainer-ce:latest

# Accéder à : http://your-vps-ip:9000
```

## 💾 Backup et Restauration

### Sauvegarder les métadonnées

```bash
# Créer un backup du volume de progression
docker run --rm \
  -v video-converter_progress-data:/data \
  -v /opt/backups:/backup \
  alpine tar czf /backup/progress-$(date +%Y%m%d).tar.gz -C /data .

# Créer un script de backup automatique
cat > /opt/backup-progress.sh << 'EOF'
#!/bin/bash
BACKUP_DIR=/opt/backups
mkdir -p $BACKUP_DIR
docker run --rm \
  -v video-converter_progress-data:/data \
  -v $BACKUP_DIR:/backup \
  alpine tar czf /backup/progress-$(date +%Y%m%d).tar.gz -C /data .
# Garder seulement les 30 derniers jours
find $BACKUP_DIR -name "progress-*.tar.gz" -mtime +30 -delete
EOF

chmod +x /opt/backup-progress.sh

# Ajouter au crontab (tous les jours à 3h)
(crontab -l 2>/dev/null; echo "0 3 * * * /opt/backup-progress.sh") | crontab -
```

### Restaurer depuis un backup

```bash
# Arrêter le conteneur
docker compose down

# Restaurer les données
docker run --rm \
  -v video-converter_progress-data:/data \
  -v /opt/backups:/backup \
  alpine sh -c "cd /data && tar xzf /backup/progress-20250607.tar.gz"

# Redémarrer
docker compose up -d
```

## 🔄 Mise à jour du conteneur

### Mise à jour du code

```bash
cd /opt/video-converter

# Sauvegarder la config actuelle
cp .env .env.backup

# Récupérer les mises à jour
git pull

# Ou copier le nouveau main.py
# scp main.py user@vps:/opt/video-converter/

# Reconstruire l'image
docker compose build --no-cache

# Redémarrer avec la nouvelle image
docker compose down
docker compose up -d

# Vérifier que tout fonctionne
docker compose logs -f
```

### Mise à jour automatique (avec Watchtower)

```bash
# Installer Watchtower pour mise à jour auto
docker run -d \
  --name watchtower \
  --restart unless-stopped \
  -v /var/run/docker.sock:/var/run/docker.sock \
  containrrr/watchtower \
  --interval 86400 \
  --cleanup \
  video-converter
```

## 📈 Optimisations Production

### 1. Ajuster les ressources selon votre VPS

Dans `.env` :
```bash
# VPS avec 4 CPU / 4GB RAM
CPU_LIMIT=3.0
MEMORY_LIMIT=3G

# VPS avec 2 CPU / 2GB RAM
CPU_LIMIT=1.5
MEMORY_LIMIT=1.5G

# VPS avec 8 CPU / 8GB RAM
CPU_LIMIT=6.0
MEMORY_LIMIT=6G
```

### 2. Optimiser les horaires de conversion

```bash
# Éviter les heures de pointe
# Exemple : la nuit entre 2h et 6h du matin
CRON_SCHEDULE=0 2 * * *
```

### 3. Utiliser un disque SSD pour PUBLIC_DIR

Les écritures fréquentes bénéficient d'un SSD :
```bash
# Monter un disque SSD
sudo mkfs.ext4 /dev/sdb
sudo mkdir -p /mnt/ssd
sudo mount /dev/sdb /mnt/ssd

# Ajouter au fstab pour montage automatique
echo "/dev/sdb /mnt/ssd ext4 defaults 0 2" | sudo tee -a /etc/fstab

# Utiliser dans .env
PUBLIC_DIR=/mnt/ssd/videos
```

## 🆘 Troubleshooting Production

### Le conteneur ne démarre pas

```bash
# Voir les logs d'erreur
docker compose logs

# Vérifier que les chemins existent
ls -la $RAW_DIR
ls -la $PUBLIC_DIR

# Permissions
sudo chown -R $USER:$USER $RAW_DIR $PUBLIC_DIR
```

### Espace disque insuffisant

```bash
# Vérifier l'espace
df -h

# Nettoyer Docker
docker system prune -a --volumes

# Nettoyer les anciens fichiers
find $PUBLIC_DIR -name "*.webm" -mtime +90 -delete
```

### Performances lentes

```bash
# Vérifier l'utilisation CPU/RAM
docker stats video-converter

# Augmenter les limites dans .env
CPU_LIMIT=6.0
MEMORY_LIMIT=4G

# Redémarrer
docker compose down && docker compose up -d

# Changer le cpu-used dans main.py (ligne 40)
# '-cpu-used', '4'  # Au lieu de '2' (plus rapide, qualité légèrement moindre)
```

## 📞 Support et Monitoring

### Notifications par email (optionnel)

Installer un système d'alertes :
```bash
# Installer mailutils
sudo apt install mailutils -y

# Script de monitoring
cat > /opt/monitor-converter.sh << 'EOF'
#!/bin/bash
if ! docker ps | grep -q video-converter; then
    echo "Video Converter is down!" | mail -s "Alert: Video Converter Down" admin@example.com
fi
EOF

chmod +x /opt/monitor-converter.sh

# Exécuter toutes les 5 minutes
(crontab -l; echo "*/5 * * * * /opt/monitor-converter.sh") | crontab -
```

### Logs externes (Loki, Papertrail, etc.)

Modifier `compose.yaml` pour ajouter un driver de logs :
```yaml
    logging:
      driver: "syslog"
      options:
        syslog-address: "udp://logs.papertrailapp.com:12345"
        tag: "video-converter"
```

## ✅ Checklist de Déploiement

- [ ] VPS configuré avec Debian/Ubuntu
- [ ] Docker et Docker Compose installés
- [ ] Répertoires RAW et PUBLIC créés
- [ ] `.env` configuré avec les bons chemins
- [ ] Pare-feu (UFW) activé
- [ ] Conteneur démarré : `docker compose up -d`
- [ ] Logs vérifiés : `docker compose logs -f`
- [ ] Test manuel : `make exec`
- [ ] Nginx configuré (si exposition web)
- [ ] Backup automatique configuré
- [ ] Monitoring en place

Votre Video Converter est maintenant en production ! 🎉
