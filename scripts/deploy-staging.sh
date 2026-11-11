#!/usr/bin/env bash
set -euo pipefail

project_dir="${GROUNDSOPS_DIR:-/opt/groundsops/app}"
deploy_branch="${GROUNDSOPS_BRANCH:-main}"
deploy_revision="${GROUNDSOPS_REVISION:-}"
deploy_key="${GROUNDSOPS_DEPLOY_KEY:-$HOME/.ssh/groundsops_deploy}"
cd "$project_dir"

if [[ ! -f .env.staging ]]; then
  echo "Missing $project_dir/.env.staging"
  exit 1
fi

if [[ -n "$(git status --porcelain)" ]]; then
  echo "Refusing to deploy over uncommitted server changes."
  exit 1
fi

if [[ -n "$deploy_revision" && ! "$deploy_revision" =~ ^[0-9a-f]{40}$ ]]; then
  echo "GROUNDSOPS_REVISION must be a full 40-character Git commit SHA."
  exit 1
fi

echo "Creating the pre-deployment database backup."
"$project_dir/scripts/backup-staging-db.sh"

export GIT_SSH_COMMAND="ssh -i $deploy_key -o IdentitiesOnly=yes -o StrictHostKeyChecking=yes"
git fetch origin "$deploy_branch"
if git show-ref --verify --quiet "refs/heads/$deploy_branch"; then
  git switch "$deploy_branch"
else
  git switch --track -c "$deploy_branch" "origin/$deploy_branch"
fi
if [[ -n "$deploy_revision" ]]; then
  git merge --ff-only "$deploy_revision"
else
  git merge --ff-only "origin/$deploy_branch"
fi

echo "Deploying commit $(git rev-parse HEAD)."
docker compose --env-file .env.staging -f docker-compose.staging.yml build
docker compose --env-file .env.staging -f docker-compose.staging.yml up -d db
docker compose --env-file .env.staging -f docker-compose.staging.yml run --rm api \
  alembic upgrade head
docker compose --env-file .env.staging -f docker-compose.staging.yml up -d

set -a
# shellcheck disable=SC1091
source .env.staging
set +a

for attempt in {1..20}; do
  if curl --fail --silent --show-error "https://${APP_DOMAIN}/ready" >/dev/null; then
    docker compose --env-file .env.staging -f docker-compose.staging.yml ps
    echo "GroundsOps staging deployment is healthy."
    exit 0
  fi
  sleep 3
done

docker compose --env-file .env.staging -f docker-compose.staging.yml logs --tail=100
echo "Deployment failed its readiness check."
exit 1
