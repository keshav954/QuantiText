#!/bin/bash
# Backup script for QuantiText
# Run daily via cron: 0 2 * * * /opt/quantitext/infra/backup.sh
#
# Backs up PostgreSQL and keeps last 7 days.

set -euo pipefail

COMPOSE_FILE="${COMPOSE_FILE:-/opt/quantitext/docker-compose.prod.yml}"
BACKUP_DIR="${BACKUP_DIR:-/opt/backups}"
RETENTION_DAYS=7

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
mkdir -p "$BACKUP_DIR"

echo "[$(date)] Starting backup..."

# PostgreSQL dump
docker compose -f "$COMPOSE_FILE" exec -T postgres \
  pg_dump -U "${POSTGRES_USER:-quantitext}" "${POSTGRES_DB:-quantitext}" \
  | gzip > "$BACKUP_DIR/db_${TIMESTAMP}.sql.gz"

SIZE=$(du -h "$BACKUP_DIR/db_${TIMESTAMP}.sql.gz" | cut -f1)
echo "[$(date)] Database backup: db_${TIMESTAMP}.sql.gz ($SIZE)"

# Cleanup old backups
DELETED=$(find "$BACKUP_DIR" -name "db_*.sql.gz" -mtime +${RETENTION_DAYS} -delete -print | wc -l)
echo "[$(date)] Cleaned up $DELETED old backups (retention: ${RETENTION_DAYS} days)"

echo "[$(date)] Backup complete."
