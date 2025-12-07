.PHONY: help build up down restart logs logs-cron logs-sync shell exec clean status

# Default target
help:
	@echo "Video Converter - Docker Management"
	@echo ""
	@echo "Available commands:"
	@echo "  make build       - Build the Docker image"
	@echo "  make up          - Start the container"
	@echo "  make down        - Stop the container"
	@echo "  make restart     - Restart the container"
	@echo "  make logs        - Show all logs (follow)"
	@echo "  make logs-cron   - Show cron logs"
	@echo "  make logs-sync   - Show sync logs"
	@echo "  make shell       - Open shell in container"
	@echo "  make exec        - Execute manual sync"
	@echo "  make status      - Show container status"
	@echo "  make clean       - Remove container, image, and volumes"
	@echo ""

# Build the Docker image
build:
	docker compose build --no-cache

# Start the container
up:
	docker compose up -d
	@echo "Container started. View logs with: make logs"

# Stop the container
down:
	docker compose down

# Restart the container
restart:
	docker compose restart
	@echo "Container restarted"

# Show all logs (follow mode)
logs:
	docker compose logs -f --tail=100

# Show cron logs
logs-cron:
	docker exec video-converter tail -f /var/log/cron.log

# Show sync logs
logs-sync:
	docker exec video-converter tail -f /app/sync.log

# Open shell in container
shell:
	docker exec -it video-converter /bin/bash

# Execute manual sync
exec:
	docker exec -it video-converter python main.py

# Show container status
status:
	@echo "=== Container Status ==="
	docker compose ps
	@echo ""
	@echo "=== Resource Usage ==="
	docker stats video-converter --no-stream
	@echo ""
	@echo "=== Lock File ==="
	@docker exec video-converter cat /app/.sync.lock 2>/dev/null || echo "No lock file (no conversion in progress)"

# Clean everything
clean:
	docker compose down -v
	docker rmi video-converter:latest 2>/dev/null || true
	@echo "Cleaned up containers, volumes, and images"

# Install (copy .env.example to .env if not exists)
install:
	@if [ ! -f .env ]; then \
		cp .env.example .env; \
		echo ".env file created. Please edit it with your configuration."; \
		echo "Then run: make up"; \
	else \
		echo ".env file already exists"; \
	fi
