#!/usr/bin/env bash
set -euo pipefail

if [[ "${EUID}" -ne 0 ]]; then
  echo "Run this installer with sudo."
  exit 1
fi

project_dir="${GROUNDSOPS_DIR:-/opt/groundsops/app}"
chown github-runner:groundsops-deploy \
  "$project_dir/scripts/monitor-staging.sh" \
  "$project_dir/scripts/backup-staging-db.sh" \
  "$project_dir/scripts/alert-staging.sh" \
  "$project_dir/scripts/test-alert-delivery.sh"
chmod 750 \
  "$project_dir/scripts/monitor-staging.sh" \
  "$project_dir/scripts/backup-staging-db.sh" \
  "$project_dir/scripts/alert-staging.sh" \
  "$project_dir/scripts/test-alert-delivery.sh"

for unit in \
  groundsops-monitor.service \
  groundsops-monitor.timer \
  groundsops-backup.service \
  groundsops-backup.timer; do
  sed 's/\r$//' "$project_dir/infra/systemd/$unit" >"/etc/systemd/system/$unit"
  chmod 644 "/etc/systemd/system/$unit"
done

systemctl daemon-reload
systemctl enable --now groundsops-monitor.timer groundsops-backup.timer
systemctl start groundsops-monitor.service
systemctl status --no-pager groundsops-monitor.service
systemctl list-timers --all --no-pager | grep groundsops
