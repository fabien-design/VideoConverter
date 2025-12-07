#!/bin/bash

# Video Converter - Quick Start Script for VPS
# This script helps you quickly deploy the video converter on a fresh VPS

set -e

echo "========================================="
echo "Video Converter - Quick Start Setup"
echo "========================================="
echo ""

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    echo "Please don't run this script as root."
    echo "Run as your regular user with sudo access."
    exit 1
fi

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

echo "Step 1/5: Checking prerequisites..."
echo "-----------------------------------"

# Check for Docker
if command_exists docker; then
    echo "✓ Docker is installed"
    docker --version
else
    echo "✗ Docker is not installed"
    read -p "Do you want to install Docker? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "Installing Docker..."
        curl -fsSL https://get.docker.com -o get-docker.sh
        sudo sh get-docker.sh
        sudo usermod -aG docker $USER
        rm get-docker.sh
        echo "✓ Docker installed successfully"
        echo "⚠ You need to log out and back in for docker group changes to take effect"
        echo "⚠ After re-login, run this script again"
        exit 0
    else
        echo "Docker is required. Exiting."
        exit 1
    fi
fi

# Check for Docker Compose
if command_exists docker && docker compose version >/dev/null 2>&1; then
    echo "✓ Docker Compose is installed"
    docker compose version
else
    echo "✗ Docker Compose is not installed"
    echo "Installing Docker Compose plugin..."
    sudo apt-get update
    sudo apt-get install -y docker-compose-plugin
    echo "✓ Docker Compose installed successfully"
fi

echo ""
echo "Step 2/5: Configuration"
echo "----------------------"

# Check if .env exists
if [ -f .env ]; then
    echo "Found existing .env file"
    read -p "Do you want to reconfigure? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Using existing .env configuration"
    else
        rm .env
    fi
fi

# Create .env if it doesn't exist
if [ ! -f .env ]; then
    echo "Creating .env configuration file..."
    cp .env.example .env

    # Interactive configuration
    read -p "Enter RAW directory path [/mnt/videos/raw]: " raw_dir
    raw_dir=${raw_dir:-/mnt/videos/raw}

    read -p "Enter PUBLIC directory path [/mnt/videos/public]: " public_dir
    public_dir=${public_dir:-/mnt/videos/public}

    read -p "Cron schedule (default: every hour) [0 * * * *]: " cron_schedule
    cron_schedule=${cron_schedule:-0 * * * *}

    read -p "Run sync on container start? [true]: " run_on_start
    run_on_start=${run_on_start:-true}

    # Update .env file
    sed -i "s|RAW_DIR=.*|RAW_DIR=$raw_dir|" .env
    sed -i "s|PUBLIC_DIR=.*|PUBLIC_DIR=$public_dir|" .env
    sed -i "s|CRON_SCHEDULE=.*|CRON_SCHEDULE=$cron_schedule|" .env
    sed -i "s|RUN_ON_START=.*|RUN_ON_START=$run_on_start|" .env

    echo "✓ Configuration saved to .env"
fi

echo ""
echo "Step 3/5: Creating directories"
echo "------------------------------"

# Source .env to get paths
source .env

# Create directories if they don't exist
if [ ! -d "$RAW_DIR" ]; then
    echo "Creating RAW directory: $RAW_DIR"
    sudo mkdir -p "$RAW_DIR"
    sudo chown $USER:$USER "$RAW_DIR"
    echo "✓ RAW directory created"
else
    echo "✓ RAW directory already exists: $RAW_DIR"
fi

if [ ! -d "$PUBLIC_DIR" ]; then
    echo "Creating PUBLIC directory: $PUBLIC_DIR"
    sudo mkdir -p "$PUBLIC_DIR"
    sudo chown $USER:$USER "$PUBLIC_DIR"
    echo "✓ PUBLIC directory created"
else
    echo "✓ PUBLIC directory already exists: $PUBLIC_DIR"
fi

echo ""
echo "Step 4/5: Building Docker image"
echo "-------------------------------"

echo "Building video-converter image..."
docker compose build

echo "✓ Docker image built successfully"

echo ""
echo "Step 5/5: Starting container"
echo "---------------------------"

docker compose up -d

echo "✓ Container started successfully"

echo ""
echo "========================================="
echo "Installation Complete! 🎉"
echo "========================================="
echo ""
echo "Configuration:"
echo "  RAW Directory:    $RAW_DIR"
echo "  PUBLIC Directory: $PUBLIC_DIR"
echo "  Cron Schedule:    $CRON_SCHEDULE"
echo "  Run on Start:     $RUN_ON_START"
echo ""
echo "Next steps:"
echo "  1. Add videos to: $RAW_DIR"
echo "  2. View logs: docker compose logs -f"
echo "  3. Check status: docker compose ps"
echo "  4. Manual sync: docker exec video-converter python main.py"
echo ""
echo "Useful commands:"
echo "  make logs        - View all logs"
echo "  make status      - Check container status"
echo "  make exec        - Run manual sync"
echo "  make shell       - Open shell in container"
echo ""
echo "For more information, see README_DOCKER.md"
echo ""
