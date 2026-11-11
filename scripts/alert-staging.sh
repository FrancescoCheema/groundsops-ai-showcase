#!/usr/bin/env bash
set -euo pipefail
event="${1:-groundsops_alert}"
detail="${2:-{}}"
payload="$(printf '{\"event\":\"%s\",\"host\":\"%s\",\"detail\":%s}' "$event" "$(hostname)" "$detail")"
logger --tag groundsops-alert -- "$payload"
if [[ -n "${ALERT_WEBHOOK_URL:-}" ]]; then
  curl --fail --silent --show-error --max-time 15 -H 'Content-Type: application/json' -d "$payload" "$ALERT_WEBHOOK_URL" >/dev/null
fi

