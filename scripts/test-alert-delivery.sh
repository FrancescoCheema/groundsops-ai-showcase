#!/usr/bin/env bash
set -euo pipefail
[[ -n "${ALERT_WEBHOOK_URL:-}" ]] || { echo "ALERT_WEBHOOK_URL is required"; exit 2; }
"$(dirname "$0")/alert-staging.sh" "alert_delivery_test" '{"severity":"test","message":"GroundsOps alert delivery test"}'
echo "Test alert delivered. Confirm receipt in the configured destination."

