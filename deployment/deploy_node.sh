#!/bin/bash
set -e

echo "[SYS.LOG] Starting deployment process..."

# We assume this is run from the project root based on the workflow script
echo "[SYS.LOG] Pulling latest images..."
podman-compose -f deployment/podman-compose.yml pull

echo "[SYS.LOG] Starting services..."
podman-compose -f deployment/podman-compose.yml up -d --remove-orphans

echo "[SYS.LOG] Cleaning up unused images..."
podman image prune -a -f

echo "[SYS.LOG] Deployment completed successfully."
