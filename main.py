#!/usr/bin/env python3
"""
Video Converter Sync Script
Syncs raw folder to public folder, converting videos to WebM format
"""

import os
import sys
import subprocess
import shutil
import logging
from pathlib import Path
from datetime import datetime
import argparse
import re
import time
import threading
import hashlib
import json

# Configuration
RAW_DIR = Path(__file__).parent / "files" / "raw"
PUBLIC_DIR = Path(__file__).parent / "files" / "public"
PROGRESS_DIR = Path(__file__).parent / ".progress"
LOCK_FILE = Path(__file__).parent / ".sync.lock"

# Video file extensions to convert
VIDEO_EXTENSIONS = {
    '.mp4', '.avi', '.mkv', '.mov', '.flv', '.wmv', '.m4v',
    '.mpeg', '.mpg', '.webm', '.3gp', '.ogv', '.ts', '.m2ts'
}

# FFmpeg settings for high quality WebM conversion
FFMPEG_SETTINGS = [
    '-vf', 'scale=trunc(min(iw\\,1920)/2)*2:trunc(min(ih\\,1080)/2)*2',  # Scale to max 1080p, keep aspect ratio, no upscaling
    '-c:v', 'libvpx-vp9',              # VP9 codec for better compression
    '-b:v', '0',                       # Use CRF mode (0 = let CRF control bitrate)
    '-crf', '23',                      # Constant Rate Factor (lower = better quality, 23 is high quality)
    '-c:a', 'libopus',                 # Opus audio codec
    '-b:a', '192k',                    # 192kbps audio bitrate (higher quality)
    '-cpu-used', '2',                  # Speed vs quality (0-5, 2 is better quality, slower encoding)
    '-row-mt', '1',                    # Enable row-based multithreading
    '-threads', '0',                   # Use all available threads
    '-deadline', 'good',               # Encoding deadline (good = better quality than realtime)
    '-auto-alt-ref', '1',              # Enable alternate reference frames (better quality)
    '-lag-in-frames', '25',            # Allow encoder to look ahead (better compression)
    '-f', 'webm'                       # Force WebM format
]

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('sync.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Set stdout encoding to utf-8 on Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')


def acquire_lock():
    """Acquire a lock file to prevent multiple instances running"""
    if LOCK_FILE.exists():
        # Check if the lock is stale (older than 24 hours)
        try:
            with open(LOCK_FILE, 'r') as f:
                lock_data = json.load(f)
                lock_time = datetime.fromisoformat(lock_data.get('timestamp', ''))
                lock_pid = lock_data.get('pid')

                # Check if lock is older than 24 hours
                if (datetime.now() - lock_time).total_seconds() > 86400:
                    logger.warning(f"Removing stale lock file (older than 24h)")
                    LOCK_FILE.unlink()
                else:
                    logger.error(f"Another instance is already running (PID: {lock_pid})")
                    logger.error(f"Lock created at: {lock_time.strftime('%Y-%m-%d %H:%M:%S')}")
                    logger.error(f"If this is a stale lock, delete: {LOCK_FILE}")
                    return False
        except Exception as e:
            logger.warning(f"Error reading lock file, removing it: {e}")
            LOCK_FILE.unlink()

    # Create lock file
    try:
        lock_data = {
            'pid': os.getpid(),
            'timestamp': datetime.now().isoformat(),
            'hostname': os.environ.get('COMPUTERNAME', os.environ.get('HOSTNAME', 'unknown'))
        }
        with open(LOCK_FILE, 'w') as f:
            json.dump(lock_data, f, indent=2)
        logger.info(f"Lock acquired (PID: {os.getpid()})")
        return True
    except Exception as e:
        logger.error(f"Failed to create lock file: {e}")
        return False


def release_lock():
    """Release the lock file"""
    try:
        if LOCK_FILE.exists():
            LOCK_FILE.unlink()
            logger.info("Lock released")
    except Exception as e:
        logger.error(f"Error releasing lock: {e}")


def calculate_file_hash(file_path, chunk_size=8192):
    """Calculate MD5 hash of a file for identification"""
    md5 = hashlib.md5()
    try:
        with open(file_path, 'rb') as f:
            # Only hash first 10MB for speed on large files
            bytes_read = 0
            max_bytes = 10 * 1024 * 1024  # 10MB
            while bytes_read < max_bytes:
                chunk = f.read(chunk_size)
                if not chunk:
                    break
                md5.update(chunk)
                bytes_read += len(chunk)
        return md5.hexdigest()
    except Exception as e:
        logger.error(f"Error calculating hash for {file_path}: {e}")
        return None


def get_progress_metadata_path(source_path):
    """Get path to progress metadata file for a source file"""
    file_hash = calculate_file_hash(source_path)
    if not file_hash:
        return None
    PROGRESS_DIR.mkdir(parents=True, exist_ok=True)
    return PROGRESS_DIR / f"{file_hash}.json"


def save_progress_metadata(source_path, output_path, status='in_progress'):
    """Save progress metadata for a conversion"""
    metadata_path = get_progress_metadata_path(source_path)
    if not metadata_path:
        return False

    try:
        metadata = {
            'source_path': str(source_path),
            'output_path': str(output_path),
            'source_hash': calculate_file_hash(source_path),
            'source_size': source_path.stat().st_size,
            'source_mtime': source_path.stat().st_mtime,
            'status': status,
            'timestamp': datetime.now().isoformat()
        }

        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2)
        return True
    except Exception as e:
        logger.error(f"Error saving progress metadata: {e}")
        return False


def load_progress_metadata(source_path):
    """Load progress metadata for a source file"""
    metadata_path = get_progress_metadata_path(source_path)
    if not metadata_path or not metadata_path.exists():
        return None

    try:
        with open(metadata_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading progress metadata: {e}")
        return None


def delete_progress_metadata(source_path):
    """Delete progress metadata for a source file"""
    metadata_path = get_progress_metadata_path(source_path)
    if metadata_path and metadata_path.exists():
        try:
            metadata_path.unlink()
            return True
        except Exception as e:
            logger.error(f"Error deleting progress metadata: {e}")
            return False
    return True


def is_video_file(file_path):
    """Check if file is a video based on extension"""
    return file_path.suffix.lower() in VIDEO_EXTENSIONS


def get_output_path(source_path, raw_dir, public_dir, is_video=False):
    """Get the corresponding output path in public directory"""
    relative_path = source_path.relative_to(raw_dir)
    output_path = public_dir / relative_path

    # Change extension to .webm for video files
    if is_video and output_path.suffix.lower() != '.webm':
        output_path = output_path.with_suffix('.webm')

    return output_path


def should_process_file(source_path, output_path):
    """Check if file should be processed (new or modified)"""
    # Check if output file exists
    if not output_path.exists():
        return True

    # Check for temporary file (incomplete conversion)
    temp_output_path = output_path.with_suffix('.tmp.webm')
    if temp_output_path.exists():
        logger.info(f"Found incomplete conversion, resuming: {source_path.name}")
        return True

    # Load metadata to verify integrity
    metadata = load_progress_metadata(source_path)
    if metadata:
        # Check if source file has changed since last conversion
        current_hash = calculate_file_hash(source_path)
        if current_hash != metadata.get('source_hash'):
            logger.info(f"Source file changed, reconverting: {source_path.name}")
            return True

        # Check if output path matches
        if str(output_path) != metadata.get('output_path'):
            logger.info(f"Output path changed, reconverting: {source_path.name}")
            return True

        # File is up to date
        if metadata.get('status') == 'completed':
            return False

    # Fallback: Compare modification times
    source_mtime = source_path.stat().st_mtime
    output_mtime = output_path.stat().st_mtime

    return source_mtime > output_mtime


def get_video_duration(input_path):
    """Get video duration in seconds using ffprobe"""
    try:
        cmd = [
            'ffprobe',
            '-v', 'error',
            '-show_entries', 'format=duration',
            '-of', 'default=noprint_wrappers=1:nokey=1',
            str(input_path)
        ]
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if result.returncode == 0:
            return float(result.stdout.strip())
    except:
        pass
    return None


def parse_time_to_seconds(time_str):
    """Convert HH:MM:SS.ms to seconds"""
    try:
        parts = time_str.split(':')
        hours = float(parts[0])
        minutes = float(parts[1])
        seconds = float(parts[2])
        return hours * 3600 + minutes * 60 + seconds
    except:
        return 0


def convert_video_to_webm(input_path, output_path):
    """Convert video file to WebM format using ffmpeg with progress bar and resume support"""
    # Use temporary file during conversion
    temp_output_path = output_path.with_suffix('.tmp.webm')

    try:
        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Save progress metadata (mark as in progress)
        save_progress_metadata(input_path, output_path, status='in_progress')

        # Check if there's an incomplete conversion
        if temp_output_path.exists():
            logger.info(f"Removing incomplete file: {temp_output_path.name}")
            temp_output_path.unlink()

        # Get video duration for progress calculation
        duration = get_video_duration(input_path)

        # Build ffmpeg command (output to temp file)
        cmd = [
            'ffmpeg',
            '-i', str(input_path),
            '-y',  # Overwrite output file if exists
            '-progress', 'pipe:1',  # Output progress to stdout
            '-nostats',  # Disable stats output on stderr
        ] + FFMPEG_SETTINGS + [
            str(temp_output_path)
        ]

        logger.info(f"Converting: {input_path.name} -> {output_path.name}")

        start_time = time.time()

        # Run ffmpeg with real-time output
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding='utf-8',
            errors='replace',
            bufsize=1
        )

        # Store stderr output in a separate thread to avoid blocking
        stderr_output = []
        def read_stderr():
            for line in process.stderr:
                stderr_output.append(line)

        stderr_thread = threading.Thread(target=read_stderr, daemon=True)
        stderr_thread.start()

        # Variables for progress tracking
        last_time = 0
        last_print_time = time.time()

        # Read output line by line
        for line in process.stdout:
            line = line.strip()

            # Parse progress information
            if line.startswith('out_time_ms='):
                try:
                    time_ms = int(line.split('=')[1])
                    current_time = time_ms / 1000000.0  # Convert microseconds to seconds

                    # Only update every 0.5 seconds to avoid spam
                    now = time.time()
                    if now - last_print_time >= 0.5:
                        elapsed = now - start_time

                        if duration and duration > 0:
                            progress = (current_time / duration) * 100
                            progress = min(progress, 100)

                            # Calculate ETA
                            if progress > 0:
                                eta = (elapsed / progress) * (100 - progress)
                                eta_str = f"ETA: {int(eta)}s"
                            else:
                                eta_str = "ETA: N/A"

                            # Create progress bar
                            bar_length = 30
                            filled = int(bar_length * progress / 100)
                            bar = '█' * filled + '░' * (bar_length - filled)

                            print(f"\r  [{bar}] {progress:.1f}% | Temps: {int(elapsed)}s | {eta_str}", end='', flush=True)
                        else:
                            print(f"\r  Temps écoulé: {int(elapsed)}s | Position: {int(current_time)}s", end='', flush=True)

                        last_print_time = now
                        last_time = current_time
                except:
                    pass

        # Wait for process to complete
        process.wait()

        # Calculate total conversion time
        total_time = time.time() - start_time

        # Clear progress line and print final result
        print()  # New line after progress bar

        if process.returncode == 0:
            # Move temp file to final destination
            if temp_output_path.exists():
                # Remove old output file if exists
                if output_path.exists():
                    output_path.unlink()
                # Rename temp to final
                temp_output_path.rename(output_path)

            # Update metadata to completed
            save_progress_metadata(input_path, output_path, status='completed')

            logger.info(f"Converti avec succès en {total_time:.1f}s: {output_path.name}")
            return True
        else:
            stderr_text = ''.join(stderr_output)
            logger.error(f"Erreur FFmpeg pour {input_path.name}: {stderr_text}")
            # Keep temp file for potential debugging, will be cleaned up on next run
            return False

    except FileNotFoundError:
        logger.error("FFmpeg not found. Please install ffmpeg and add it to PATH")
        delete_progress_metadata(input_path)
        return False
    except KeyboardInterrupt:
        logger.info(f"\nConversion interrompue: {input_path.name}")
        logger.info(f"Fichier temporaire conservé: {temp_output_path.name}")
        # Keep metadata and temp file for resume
        raise
    except Exception as e:
        logger.error(f"Erreur lors de la conversion de {input_path}: {e}")
        delete_progress_metadata(input_path)
        # Clean up temp file on error
        if temp_output_path.exists():
            temp_output_path.unlink()
        return False


def copy_file(source_path, output_path):
    """Copy non-video file to public directory"""
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, output_path)
        logger.info(f"Copied: {source_path.name}")
        return True
    except Exception as e:
        logger.error(f"Error copying {source_path}: {e}")
        return False


def cleanup_incomplete_conversions(public_dir):
    """Clean up incomplete conversion files and orphaned metadata"""
    logger.info("Cleaning up incomplete conversions...")

    cleaned_count = 0

    # Clean up .tmp.webm files in public directory
    if public_dir.exists():
        for temp_file in public_dir.rglob('*.tmp.webm'):
            try:
                temp_file.unlink()
                logger.info(f"Removed incomplete temp file: {temp_file.name}")
                cleaned_count += 1
            except Exception as e:
                logger.error(f"Error removing temp file {temp_file}: {e}")

    # Clean up orphaned metadata files
    if PROGRESS_DIR.exists():
        for metadata_file in PROGRESS_DIR.glob('*.json'):
            try:
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)

                source_path = Path(metadata.get('source_path', ''))

                # Remove metadata if source file no longer exists
                if not source_path.exists():
                    metadata_file.unlink()
                    logger.info(f"Removed orphaned metadata: {metadata_file.name}")
                    cleaned_count += 1
                # Remove metadata if it's been marked in_progress but output exists
                elif metadata.get('status') == 'in_progress':
                    output_path = Path(metadata.get('output_path', ''))
                    if output_path.exists():
                        # Verify hash matches
                        current_hash = calculate_file_hash(source_path)
                        if current_hash == metadata.get('source_hash'):
                            # Conversion was actually completed, update metadata
                            save_progress_metadata(source_path, output_path, status='completed')
                            logger.info(f"Updated metadata to completed: {source_path.name}")
                        else:
                            # Source changed, remove old metadata
                            metadata_file.unlink()
                            cleaned_count += 1

            except Exception as e:
                logger.error(f"Error processing metadata file {metadata_file}: {e}")

    if cleaned_count > 0:
        logger.info(f"Cleaned up {cleaned_count} incomplete/orphaned files")


def sync_folder_structure(raw_dir, public_dir):
    """
    Sync folder structure between raw and public directories
    - Create new folders in public that exist in raw
    - Delete folders in public that don't exist in raw
    """
    logger.info("Syncing folder structure...")

    # Get all directories in raw and public
    raw_dirs = set()
    for root, dirs, files in os.walk(raw_dir):
        root_path = Path(root)
        for dir_name in dirs:
            dir_path = root_path / dir_name
            relative_path = dir_path.relative_to(raw_dir)
            raw_dirs.add(relative_path)

    public_dirs = set()
    if public_dir.exists():
        for root, dirs, files in os.walk(public_dir):
            root_path = Path(root)
            for dir_name in dirs:
                dir_path = root_path / dir_name
                relative_path = dir_path.relative_to(public_dir)
                public_dirs.add(relative_path)

    # Create missing directories in public
    for dir_rel_path in raw_dirs:
        public_path = public_dir / dir_rel_path
        if not public_path.exists():
            public_path.mkdir(parents=True, exist_ok=True)
            logger.info(f"Created directory: {dir_rel_path}")

    # Delete directories in public that don't exist in raw
    for dir_rel_path in public_dirs:
        if dir_rel_path not in raw_dirs:
            public_path = public_dir / dir_rel_path
            if public_path.exists():
                shutil.rmtree(public_path)
                logger.info(f"Deleted directory: {dir_rel_path}")


def clean_orphaned_files(raw_dir, public_dir):
    """Delete files in public that don't have a corresponding source in raw"""
    logger.info("Cleaning orphaned files...")

    if not public_dir.exists():
        return

    # Get all files in raw
    raw_files = set()
    for root, dirs, files in os.walk(raw_dir):
        root_path = Path(root)
        for file_name in files:
            file_path = root_path / file_name
            relative_path = file_path.relative_to(raw_dir)
            raw_files.add(relative_path)

            # Also add the .webm version if this is a video
            if is_video_file(file_path):
                webm_relative = relative_path.with_suffix('.webm')
                raw_files.add(webm_relative)

    # Check all files in public
    for root, dirs, files in os.walk(public_dir):
        root_path = Path(root)
        for file_name in files:
            file_path = root_path / file_name
            relative_path = file_path.relative_to(public_dir)
            source_exists = False
            if relative_path in raw_files:
                source_exists = True
            else:
                # Check if this is a .webm file that was converted from another format
                if file_path.suffix == '.webm':
                    # Check if any video file with the same name (different extension) exists
                    for ext in VIDEO_EXTENSIONS:
                        possible_source = relative_path.with_suffix(ext)
                        if possible_source in raw_files:
                            source_exists = True
                            break

            if not source_exists:
                file_path.unlink()
                logger.info(f"Deleted orphaned file: {relative_path}")


def process_files(raw_dir, public_dir):
    """Process all files from raw directory"""
    logger.info("Processing files...")

    stats = {
        'converted': 0,
        'copied': 0,
        'skipped': 0,
        'errors': 0
    }

    for root, dirs, files in os.walk(raw_dir):
        root_path = Path(root)

        for file_name in files:
            source_path = root_path / file_name
            is_video = is_video_file(source_path)
            output_path = get_output_path(source_path, raw_dir, public_dir, is_video)

            # Check if file needs processing
            if not should_process_file(source_path, output_path):
                logger.debug(f"Skipping (up-to-date): {source_path.name}")
                stats['skipped'] += 1
                continue

            # Process the file
            if is_video:
                if convert_video_to_webm(source_path, output_path):
                    stats['converted'] += 1
                else:
                    stats['errors'] += 1
            else:
                if copy_file(source_path, output_path):
                    stats['copied'] += 1
                else:
                    stats['errors'] += 1

    return stats


def main():
    """Main sync function"""
    # Try to acquire lock
    if not acquire_lock():
        return 2  # Exit code 2 = already running

    try:
        start_time = datetime.now()
        logger.info("=" * 60)
        logger.info(f"Starting sync at {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("=" * 60)

        # Verify directories exist
        if not RAW_DIR.exists():
            logger.error(f"Raw directory does not exist: {RAW_DIR}")
            return 1

        # Create public directory if it doesn't exist
        PUBLIC_DIR.mkdir(parents=True, exist_ok=True)

        try:
            # Step 1: Clean up incomplete conversions from previous runs
            cleanup_incomplete_conversions(PUBLIC_DIR)

            # Step 2: Sync folder structure
            sync_folder_structure(RAW_DIR, PUBLIC_DIR)

            # Step 3: Clean orphaned files
            clean_orphaned_files(RAW_DIR, PUBLIC_DIR)

            # Step 4: Process files (convert videos, copy others)
            stats = process_files(RAW_DIR, PUBLIC_DIR)

            # Summary
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()

            logger.info("=" * 60)
            logger.info("Sync completed!")
            logger.info(f"Duration: {duration:.2f} seconds")
            logger.info(f"Videos converted: {stats['converted']}")
            logger.info(f"Files copied: {stats['copied']}")
            logger.info(f"Files skipped (up-to-date): {stats['skipped']}")
            logger.info(f"Errors: {stats['errors']}")
            logger.info("=" * 60)

            return 0 if stats['errors'] == 0 else 1

        except KeyboardInterrupt:
            logger.info("\nSync interrupted by user")
            return 1
        except Exception as e:
            logger.error(f"Unexpected error: {e}", exc_info=True)
            return 1

    finally:
        # Always release the lock
        release_lock()


if __name__ == "__main__":

  parser = argparse.ArgumentParser(description="Sync and convert video files.")
  parser.add_argument('--raw-dir', type=Path, default=RAW_DIR, help="Path to the raw files directory")
  parser.add_argument('--public-dir', type=Path, default=PUBLIC_DIR, help="Path to the public files directory")
  args = parser.parse_args()

  RAW_DIR = args.raw_dir
  PUBLIC_DIR = args.public_dir

  sys.exit(main())
