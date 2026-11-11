# GroundsOps staging observability

## Signals

- FastAPI emits JSON request-completion logs with request ID, method, path,
  status, latency, and environment. Query strings and request bodies are not
  logged.
- Docker JSON logs rotate at 10 MB with three files retained per container.
- `groundsops-monitor.timer` checks disk, memory, container state, public
  readiness, and backup age every five minutes.
- `groundsops-backup.timer` creates an encrypted PostgreSQL backup every day.
- `Monitor staging` checks public readiness from a GitHub-hosted runner every
  fifteen minutes.
- Lightsail alarms cover host status checks, sustained CPU, and low burst
  capacity and notify the configured regional email contact.

## Useful commands

```bash
sudo systemctl status groundsops-monitor.timer groundsops-backup.timer
sudo systemctl list-timers --all | grep groundsops
sudo journalctl -u groundsops-monitor.service --since today
sudo journalctl -t groundsops-monitor --since today
sudo systemctl start groundsops-monitor.service
sudo systemctl start groundsops-backup.service
docker compose --env-file .env.staging -f docker-compose.staging.yml logs --tail=100 api
```

## Response guide

- `disk_usage`: inspect `df -h`, Docker images, and `/opt/groundsops/backups`.
- `memory_usage`: inspect `free -h` and `docker stats --no-stream`.
- `backup_age`: run the backup service and verify the S3 upload.
- `container_*`: inspect Compose status and the affected container logs.
- `public_readiness`: inspect API/database health, Caddy, DNS, and TLS.
- Lightsail status-check alarm: inspect the AWS console before rebooting.
- High CPU or low burst capacity: inspect container load and consider moving
  to a larger Lightsail bundle if sustained.

Never delete the newest verified backup while investigating an incident.
