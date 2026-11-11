#!/usr/bin/env bash
set -euo pipefail

readonly expected_prefix="deploy "
command_text="${SSH_ORIGINAL_COMMAND:-}"

if [[ "$command_text" != "$expected_prefix"* ]]; then
  echo "Only staging deployment commands are permitted."
  exit 1
fi

revision="${command_text#"$expected_prefix"}"
if [[ ! "$revision" =~ ^[0-9a-f]{40}$ ]]; then
  echo "Deployment revision must be a full 40-character Git commit SHA."
  exit 1
fi

export GROUNDSOPS_REVISION="$revision"
exec /opt/groundsops/app/scripts/deploy-staging.sh
