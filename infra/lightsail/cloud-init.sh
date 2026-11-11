#!/usr/bin/env bash
set -euo pipefail

export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y ca-certificates curl git awscli unattended-upgrades
curl -fsSL https://get.docker.com | sh
usermod -aG docker ubuntu
systemctl enable --now docker

mkdir -p /opt/groundsops/app /opt/groundsops/backups
chown -R ubuntu:ubuntu /opt/groundsops

fallocate -l 2G /swapfile
chmod 600 /swapfile
mkswap /swapfile
swapon /swapfile
echo '/swapfile none swap sw 0 0' >>/etc/fstab

cat >/etc/sysctl.d/99-groundsops.conf <<'EOF'
vm.swappiness=10
EOF
sysctl --system
