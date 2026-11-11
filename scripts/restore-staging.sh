#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "Usage: $0 /absolute/path/to/groundsops.dump" >&2
  exit 2
fi
dump_path="$1"
[[ -f "$dump_path" ]] || { echo "Backup not found: $dump_path" >&2; exit 2; }
[[ "${CONFIRM_RESTORE:-}" == "RESTORE_GROUNDSOPS" ]] || {
  echo "Set CONFIRM_RESTORE=RESTORE_GROUNDSOPS to confirm this destructive restore." >&2
  exit 2
}

cd /opt/groundsops/app
sha_file="$dump_path.sha256"
[[ ! -f "$sha_file" ]] || sha256sum --check "$sha_file"
sudo docker compose --env-file .env.staging -f docker-compose.staging.yml stop api
sudo docker compose --env-file .env.staging -f docker-compose.staging.yml exec -T db \
  dropdb -U groundsops --if-exists groundsops
sudo docker compose --env-file .env.staging -f docker-compose.staging.yml exec -T db \
  createdb -U groundsops groundsops
# Copy the dump in rather than streaming it over `exec` stdin, which can end early.
container_dump="/tmp/groundsops-restore.dump"
sudo docker compose --env-file .env.staging -f docker-compose.staging.yml cp \
  "$dump_path" "db:$container_dump"
sudo docker compose --env-file .env.staging -f docker-compose.staging.yml exec -T db \
  pg_restore -U groundsops -d groundsops --no-owner --no-acl "$container_dump" </dev/null
sudo docker compose --env-file .env.staging -f docker-compose.staging.yml exec -T db \
  rm -f "$container_dump" </dev/null
sudo docker compose --env-file .env.staging -f docker-compose.staging.yml run --rm api \
  alembic upgrade head
sudo docker compose --env-file .env.staging -f docker-compose.staging.yml up -d api
echo "Restore completed. Verify /ready and the business workflow immediately."
