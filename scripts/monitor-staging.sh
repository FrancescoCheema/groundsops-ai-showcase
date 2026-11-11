#!/usr/bin/env bash
set -euo pipefail

# The same scripts run staging and production; production sets GROUNDSOPS_ENV_FILE=.env.production.
env_file="${GROUNDSOPS_ENV_FILE:-.env.staging}"
export GROUNDSOPS_ENV_FILE="$env_file"

project_dir="${GROUNDSOPS_DIR:-/opt/groundsops/app}"
backup_dir="${GROUNDSOPS_BACKUP_DIR:-/opt/groundsops/backups}"
disk_threshold="${GROUNDSOPS_DISK_THRESHOLD_PERCENT:-85}"
memory_threshold="${GROUNDSOPS_MEMORY_THRESHOLD_PERCENT:-90}"
backup_max_age_hours="${GROUNDSOPS_BACKUP_MAX_AGE_HOURS:-30}"
cd "$project_dir"

disk_percent="$(df -P / | awk 'NR == 2 {gsub("%", "", $5); print $5}')"
memory_percent="$(free | awk '/Mem:/ {printf "%.0f", ($3 / $2) * 100}')"
backup_file="$(find "$backup_dir" -type f -name 'groundsops-*.dump' -printf '%T@ %p\n' 2>/dev/null | sort -nr | head -1 | cut -d' ' -f2-)"
backup_age_hours=-1
if [[ -n "$backup_file" ]]; then
  backup_modified="$(stat -c %Y "$backup_file")"
  backup_age_hours="$(( ($(date +%s) - backup_modified) / 3600 ))"
fi

failures=()
if (( disk_percent >= disk_threshold )); then
  failures+=("disk_usage")
fi
if (( memory_percent >= memory_threshold )); then
  failures+=("memory_usage")
fi
if (( backup_age_hours < 0 || backup_age_hours > backup_max_age_hours )); then
  failures+=("backup_age")
fi

compose=(docker compose --env-file "$env_file" -f docker-compose.staging.yml)
for service in db api web; do
  container_id="$("${compose[@]}" ps -q "$service")"
  if [[ -z "$container_id" ]] || [[ "$(docker inspect -f '{{.State.Status}}' "$container_id")" != "running" ]]; then
    failures+=("container_$service")
  fi
done

if ! curl --fail --silent --show-error --max-time 10 "https://${APP_DOMAIN}/ready" >/dev/null; then
  failures+=("public_readiness")
fi

status="healthy"
if (( ${#failures[@]} > 0 )); then
  status="unhealthy"
fi
failure_csv="$(IFS=,; echo "${failures[*]:-}")"
message="{\"event\":\"staging_monitor\",\"status\":\"$status\",\"disk_percent\":$disk_percent,\"memory_percent\":$memory_percent,\"backup_age_hours\":$backup_age_hours,\"failures\":\"$failure_csv\"}"
logger --tag groundsops-monitor -- "$message"
echo "$message"

if [[ "$status" != "healthy" ]]; then
  "$project_dir/scripts/alert-staging.sh" "staging_monitor_failed" "$message" || true
  exit 1
fi
