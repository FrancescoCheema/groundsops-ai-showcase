#!/usr/bin/env bash
set -euo pipefail

# The same scripts run staging and production; production sets GROUNDSOPS_ENV_FILE=.env.production.
env_file="${GROUNDSOPS_ENV_FILE:-.env.staging}"
export GROUNDSOPS_ENV_FILE="$env_file"

project_dir="${GROUNDSOPS_DIR:-/opt/groundsops/app}"
backup_dir="${GROUNDSOPS_BACKUP_DIR:-/opt/groundsops/backups}"
cd "$project_dir"

if [[ ! -f "$env_file" ]]; then
  echo "Missing $project_dir/$env_file"
  exit 1
fi

set -a
# shellcheck disable=SC1090,SC1091
source "$env_file"
set +a

compose() {
  docker compose --env-file "$env_file" -f docker-compose.staging.yml "$@"
}

if [[ -z "$(compose ps --status running --quiet db)" ]]; then
  echo "The staging database container is not running; cannot take a backup." >&2
  compose ps >&2 || true
  exit 1
fi

mkdir -p "$backup_dir"
timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
backup_file="$backup_dir/groundsops-$timestamp.dump"
container_file="/tmp/groundsops-$timestamp.dump"
trap 'compose exec -T db rm -f "$container_file" </dev/null >/dev/null 2>&1 || true' EXIT

# Dump and verify inside the container, then copy the file out. Streaming the dump
# through `docker compose exec` stdout can silently produce an empty file when the
# caller has no interactive stdin (CI runners, systemd timers).
compose exec -T db pg_dump --format=custom --compress=9 --no-owner \
  -U groundsops -f "$container_file" groundsops </dev/null
compose exec -T db pg_restore --list "$container_file" </dev/null >/dev/null
container_size="$(compose exec -T db stat -c %s "$container_file" </dev/null | tr -d '[:space:]')"
compose cp "db:$container_file" "$backup_file"

local_size="$(stat -c %s "$backup_file")"
if [[ ! -s "$backup_file" || "$local_size" != "$container_size" ]]; then
  echo "Database backup copy is incomplete ($local_size of $container_size bytes)." >&2
  exit 1
fi
sha256sum "$backup_file" >"$backup_file.sha256"

AWS_ACCESS_KEY_ID="$S3_ACCESS_KEY_ID" \
AWS_SECRET_ACCESS_KEY="$S3_SECRET_ACCESS_KEY" \
AWS_DEFAULT_REGION="$AWS_REGION" \
  aws s3 cp "$backup_file" "$BACKUP_S3_URI/$(basename "$backup_file")" \
  --sse AES256

find "$backup_dir" -type f -name 'groundsops-*.dump*' -mtime +7 -delete
echo "Uploaded encrypted database backup: $(basename "$backup_file") ($local_size bytes)"
