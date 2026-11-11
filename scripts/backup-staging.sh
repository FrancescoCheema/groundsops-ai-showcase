#!/usr/bin/env bash
set -euo pipefail

# The same scripts run staging and production; production sets GROUNDSOPS_ENV_FILE=.env.production.
env_file="${GROUNDSOPS_ENV_FILE:-.env.staging}"
export GROUNDSOPS_ENV_FILE="$env_file"

cd /opt/groundsops/app
backup_dir="${BACKUP_DIR:-/opt/groundsops/backups}"
retention_days="${BACKUP_RETENTION_DAYS:-14}"
timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -p "$backup_dir"
umask 077

sudo docker compose --env-file "$env_file" -f docker-compose.staging.yml exec -T db \
  pg_dump -U groundsops -d groundsops --format=custom --no-owner --no-acl \
  > "$backup_dir/groundsops-$timestamp.dump"

sha256sum "$backup_dir/groundsops-$timestamp.dump" \
  > "$backup_dir/groundsops-$timestamp.dump.sha256"
find "$backup_dir" -type f -mtime "+$retention_days" -delete
echo "Backup created: $backup_dir/groundsops-$timestamp.dump"
