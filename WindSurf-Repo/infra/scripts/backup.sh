#!/bin/bash
# Backup script for BYOS AI Backend
# Backs up Postgres database and MinIO/S3 data

set -e

BACKUP_DIR="${BACKUP_DIR:-/backups}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
POSTGRES_CONTAINER="${POSTGRES_CONTAINER:-byos_postgres}"
MINIO_CONTAINER="${MINIO_CONTAINER:-byos_minio}"
S3_BUCKET="${S3_BUCKET:-byos-ai}"

echo "Starting backup at $(date)"

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Backup Postgres
echo "Backing up Postgres database..."
docker exec "$POSTGRES_CONTAINER" pg_dump -U postgres byos_ai | gzip > "$BACKUP_DIR/postgres_${TIMESTAMP}.sql.gz"

# Backup MinIO/S3 data
echo "Backing up MinIO/S3 data..."
docker exec "$MINIO_CONTAINER" mc mirror /data "$BACKUP_DIR/minio_${TIMESTAMP}/" --exclude "*.tmp"

# Create archive
echo "Creating backup archive..."
tar -czf "$BACKUP_DIR/backup_${TIMESTAMP}.tar.gz" \
    "$BACKUP_DIR/postgres_${TIMESTAMP}.sql.gz" \
    "$BACKUP_DIR/minio_${TIMESTAMP}/"

# Cleanup individual files
rm -rf "$BACKUP_DIR/postgres_${TIMESTAMP}.sql.gz" "$BACKUP_DIR/minio_${TIMESTAMP}/"

# Keep only last 7 days of backups
find "$BACKUP_DIR" -name "backup_*.tar.gz" -mtime +7 -delete

echo "Backup completed: $BACKUP_DIR/backup_${TIMESTAMP}.tar.gz"
echo "Backup finished at $(date)"
