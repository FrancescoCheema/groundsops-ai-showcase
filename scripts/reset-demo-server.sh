#!/usr/bin/env bash
# Wipe and re-seed the public demo workspace. Run nightly on the demo server only.
set -euo pipefail

env_file="${GROUNDSOPS_ENV_FILE:-.env.demo}"
export GROUNDSOPS_ENV_FILE="$env_file"
project_dir="${GROUNDSOPS_DIR:-/opt/groundsops/app}"
cd "$project_dir"

if [[ ! -f "$env_file" ]]; then
  echo "Missing $project_dir/$env_file"
  exit 1
fi

docker compose --env-file "$env_file" -f docker-compose.staging.yml -f docker-compose.demo.yml \
  exec -T api sh -c \
  "python scripts/reset-demo-workspace.py --yes && python scripts/seed-demo-workspace.py" </dev/null
echo "Demo workspace reset and re-seeded."
