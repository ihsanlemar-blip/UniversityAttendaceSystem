#!/bin/bash
# Campus Server Automated Daily Database Backup Script
set -euo pipefail

BACKUP_DIR="${BACKUP_PATH:-/var/backups/attendance}"
TIMESTAMP=$(date -u +"%Y%m%d_%H%M%SZ")
BACKUP_FILE="${BACKUP_DIR}/attendance_backup_${TIMESTAMP}.sql.gz"
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-30}"

mkdir -p "${BACKUP_DIR}"

echo "[$(date -u)] Starting PostgreSQL automated backup..."
docker exec attendance-postgres pg_dump -U "${DATABASE_USER:-attendance_user}" "${DATABASE_NAME:-attendance_db}" | gzip > "${BACKUP_FILE}"

# Compute SHA256 checksum for backup integrity verification
sha256sum "${BACKUP_FILE}" > "${BACKUP_FILE}.sha256"
echo "[$(date -u)] Backup completed successfully: ${BACKUP_FILE}"

# Prune backups older than retention window
echo "[$(date -u)] Pruning backups older than ${RETENTION_DAYS} days..."
find "${BACKUP_DIR}" -name "attendance_backup_*.sql.gz*" -mtime "+${RETENTION_DAYS}" -delete
echo "[$(date -u)] Backup maintenance complete."
