#!/bin/bash
# Campus Server Database Restoration Script
set -euo pipefail

if [ "$#" -ne 1 ]; then
    echo "Usage: $0 <path-to-backup-file.sql.gz>"
    exit 1
fi

BACKUP_FILE="$1"

if [ ! -f "${BACKUP_FILE}" ]; then
    echo "Error: Backup file not found: ${BACKUP_FILE}"
    exit 1
fi

# Verify checksum if .sha256 file exists
if [ -f "${BACKUP_FILE}.sha256" ]; then
    echo "Verifying backup checksum..."
    sha256sum -c "${BACKUP_FILE}.sha256"
fi

echo "Restoring database from: ${BACKUP_FILE}..."
gunzip -c "${BACKUP_FILE}" | docker exec -i attendance-postgres psql -U "${DATABASE_USER:-attendance_user}" "${DATABASE_NAME:-attendance_db}"
echo "Restoration completed successfully."
