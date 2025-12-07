# Video Converter - Raw to Public Sync

Automatic video converter that syncs a `raw` folder to a `public` folder, converting videos to WebM format for efficient streaming.

## Features

- **Folder Structure Sync**: Automatically mirrors folder structure from raw to public
- **Smart File Detection**: Only processes new or modified files
- **Video Conversion**: Converts video files to WebM (VP9/Opus) with high quality settings
- **Non-Video Files**: Copies other files (subtitles, images, etc.) as-is
- **Automatic Cleanup**: Removes orphaned files and folders from public directory
- **Resume Support**: Hash-based tracking system to resume interrupted conversions
- **Instance Locking**: Prevents multiple instances from running simultaneously (cron-safe)
- **Progress Bar**: Real-time progress with ETA for each video conversion
- **Comprehensive Logging**: Logs all operations to `sync.log` and console

## Requirements

- Python 3.6 or higher
- FFmpeg installed and available in PATH

### Installing FFmpeg

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install ffmpeg
```

**CentOS/RHEL:**
```bash
sudo yum install epel-release
sudo yum install ffmpeg
```

**Windows:**
Download from https://ffmpeg.org/download.html and add to PATH

## Setup

1. Ensure your directory structure looks like this:
```
VideoConverter/
├── main.py
├── files/
│   ├── raw/          # Place your source videos here
│   └── public/       # Converted files will appear here
```

2. Make the script executable (Linux/Mac):
```bash
chmod +x main.py
```

3. Test the script:
```bash
python main.py
```

## Cron Job Setup (Automated Scheduling)

### Instance Locking Feature

Le script utilise un système de verrouillage (lock file `.sync.lock`) pour éviter que plusieurs instances s'exécutent en même temps. C'est particulièrement utile pour les tâches cron :

- ✅ Si le script est déjà en cours, la nouvelle instance s'arrête immédiatement (exit code 2)
- ✅ Les locks périmés (>24h) sont automatiquement nettoyés
- ✅ Le lock est toujours libéré, même en cas d'interruption (Ctrl+C) ou d'erreur
- ✅ Pas besoin de vérifier manuellement si une instance tourne

### Linux/Mac

1. Open crontab editor:
```bash
crontab -e
```

2. Add this line to run every hour:
```bash
0 * * * * cd /path/to/VideoConverter && /usr/bin/python3 main.py >> /path/to/VideoConverter/cron.log 2>&1
```

Replace `/path/to/VideoConverter` with your actual path.

**Note**: Si le script précédent n'est pas terminé, le cron ne créera pas d'instance supplémentaire grâce au système de verrouillage.

### Examples of Other Schedules

Run every 30 minutes:
```bash
*/30 * * * * cd /path/to/VideoConverter && /usr/bin/python3 main.py >> /path/to/VideoConverter/cron.log 2>&1
```

Run every 6 hours:
```bash
0 */6 * * * cd /path/to/VideoConverter && /usr/bin/python3 main.py >> /path/to/VideoConverter/cron.log 2>&1
```

Run every day at 2 AM:
```bash
0 2 * * * cd /path/to/VideoConverter && /usr/bin/python3 main.py >> /path/to/VideoConverter/cron.log 2>&1
```

### Windows Task Scheduler

1. Open Task Scheduler
2. Create Basic Task
3. Name: "Video Converter Sync"
4. Trigger: Daily, repeat every 1 hour (or your preferred interval)
5. Action: Start a program
   - Program: `python` (or full path: `C:\Python39\python.exe`)
   - Arguments: `main.py`
   - Start in: `K:\python\VideoConverter`
6. Settings (important):
   - ✅ "Run whether user is logged on or not" (pour exécution en arrière-plan)
   - ✅ "Do not start a new instance if the task is already running" (redondant avec notre lock, mais sécuritaire)
   - ❌ "Stop the task if it runs longer than..." (décocher pour les longues conversions)

### Vérifier les logs du cron

```bash
# Voir le log du script
tail -f sync.log

# Voir le log du cron
tail -f cron.log

# Vérifier le fichier de verrouillage
cat .sync.lock
```

### Exit Codes

Le script retourne différents codes de sortie :
- `0` - Succès complet
- `1` - Erreur durant l'exécution
- `2` - Une autre instance est déjà en cours (lock file exists)

## How It Works

1. **Instance Lock**: Checks for existing lock file to prevent concurrent executions

2. **Cleanup**: Removes incomplete conversions (`.tmp.webm` files) from previous interrupted runs

3. **Folder Sync**: Creates new folders in `public` that exist in `raw`, deletes folders from `public` that no longer exist in `raw`

4. **File Cleanup**: Removes files from `public` that don't have a corresponding source in `raw`

5. **File Processing**:
   - **Video files**: Converted to WebM format with VP9 video codec and Opus audio codec
   - **Other files**: Copied as-is to maintain folder structure

6. **Smart Updates**: Only processes files that are new or have been modified since last conversion

7. **Progress Tracking**: Stores metadata (hash, timestamps) in `.progress/` directory for resume support

## Resume Support System

Le script utilise un système de hachage MD5 (similaire à copyparty) pour identifier et reprendre les conversions interrompues :

### Comment ça fonctionne :

1. **Hash MD5** : Calcule un hash des 10 premiers MB de chaque fichier source
2. **Métadonnées** : Stocke dans `.progress/` un fichier JSON contenant :
   - Hash du fichier source
   - Taille et date de modification
   - Chemin de sortie
   - Statut de conversion (in_progress/completed)

3. **Fichiers temporaires** : Pendant la conversion, utilise `.tmp.webm` puis renomme en `.webm` une fois terminé

4. **Détection de changements** :
   - Si le fichier source change → hash différent → reconversion
   - Si le fichier est déjà converti et inchangé → skip
   - Si une conversion était interrompue → nettoie et recommence

### Exemple de reprise :

```bash
# Première exécution (interrompue à 45%)
Converting: video.mp4 -> video.webm
  [█████████████░░░░░░░░░░░░░░░░░] 45.2% | Temps: 120s | ETA: 146s
^C  # Ctrl+C

# Deuxième exécution (détecte l'interruption)
Cleaning up incomplete conversions...
Removed incomplete temp file: video.tmp.webm
Found incomplete conversion, resuming: video.mp4
Converting: video.mp4 -> video.webm  # Redémarre proprement
  [██████████████████████████████] 100% | Temps: 265s
Converti avec succès en 265.3s: video.webm
```

## Supported Video Formats

The script detects and converts the following video formats:
- .mp4, .avi, .mkv, .mov, .flv, .wmv, .m4v
- .mpeg, .mpg, .webm, .3gp, .ogv, .ts, .m2ts

## WebM Conversion Settings

The script uses high quality settings optimized for streaming:
- **Video Codec**: VP9 (libvpx-vp9)
- **CRF**: 23 (high quality, visually near-lossless)
- **Encoding Mode**: CRF-based (variable bitrate for optimal quality)
- **Audio Codec**: Opus
- **Audio Bitrate**: 192 kbps (high quality)
- **CPU Preset**: 2 (better quality, slower encoding)
- **Advanced Features**:
  - Alternate reference frames enabled
  - 25-frame lookahead for better compression
  - Row-based multithreading
- **Max Resolution**: 1080p (no upscaling)

## Logs

- **sync.log**: Detailed log of all operations
- **Console output**: Real-time progress during execution
- **cron.log**: Output when running via cron (if configured)

## Example Usage

```bash
# Run manually
python main.py

# Check logs
tail -f sync.log

# View cron log
tail -f cron.log
```

## Troubleshooting

**FFmpeg not found:**
- Ensure ffmpeg is installed: `ffmpeg -version`
- Check if ffmpeg is in PATH: `which ffmpeg` (Linux/Mac) or `where ffmpeg` (Windows)

**Permission denied:**
- Make sure you have read/write permissions for both `raw` and `public` directories
- On Linux: `chmod +x main.py`

**Files not converting:**
- Check `sync.log` for error messages
- Verify the source file is a valid video format
- Ensure there's enough disk space

**"Another instance is already running":**
- Le script détecte qu'une instance est déjà en cours
- Vérifiez avec `ps aux | grep main.py` (Linux) ou Task Manager (Windows)
- Si le lock est périmé (>24h), il sera automatiquement nettoyé
- Pour forcer la suppression du lock : `rm .sync.lock`

**Stale lock file (script crashed):**
- Normalement auto-nettoyé après 24h
- Pour supprimer manuellement :
  ```bash
  rm .sync.lock
  ```

**Incomplete conversions after interruption:**
- Les fichiers `.tmp.webm` sont automatiquement nettoyés au prochain démarrage
- Les métadonnées dans `.progress/` permettent de suivre l'état
- Pour tout nettoyer manuellement :
  ```bash
  find files/public -name "*.tmp.webm" -delete
  rm -rf .progress/
  ```

**Cron job not running:**
- Check cron is running: `sudo systemctl status cron`
- Verify cron job syntax: `crontab -l`
- Check system logs: `grep CRON /var/log/syslog`
- Verify Python path in cron: use absolute paths
