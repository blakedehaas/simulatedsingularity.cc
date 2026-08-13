#!/bin/bash
set -e

BACKUP_DIR="./backups"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="${BACKUP_DIR}/chronos_backup_${TIMESTAMP}.tar.gz"

echo "[CHRONOS] Starting backup process..."

# Create backup directory if it doesn't exist
mkdir -p "${BACKUP_DIR}"

# Compress data directories
echo "[CHRONOS] Compressing data/sqlite and data/vector..."
tar -czf "${BACKUP_FILE}" data/sqlite data/vector

echo "[CHRONOS] Backup successfully created at ${BACKUP_FILE}"

# Rotate backups older than 7 days
echo "[CHRONOS] Rotating backups older than 7 days..."
find "${BACKUP_DIR}" -type f -name "chronos_backup_*.tar.gz" -mtime +7 -exec rm {} \;

echo "[CHRONOS] Backup process completed successfully."
