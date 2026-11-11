# Public demo server

A demo anyone can open from a link, without an account. It runs the seeded demo workspace with the
offline mock AI provider and resets every night.

**Use a dedicated server.** Demo mode turns on development sign-in. With `APP_ENV=demo` the API
only issues sign-in tokens for the demo workspace and refuses to create new workspaces, but the
server must still hold nothing except demo data. Never point it at staging or production.

## Set up

1. Infrastructure (the API needs about 1 GB for virus scanning, so use the 2 GB bundle):

```bash
(cd infra/lightsail && terraform workspace new demo && terraform apply -var "environment=demo" -var "bundle_id=small_3_0")
(cd infra/storage && terraform workspace new demo && terraform apply -var "environment=demo")
```

2. Point `demo.<your-domain>` at the static IP and prepare the server as in
   [LIGHTSAIL_STAGING.md](LIGHTSAIL_STAGING.md), using `.env.demo` (copy `.env.demo.example`).
3. Start the stack with the demo override and seed the workspace:

```bash
cd /opt/groundsops/app
export GROUNDSOPS_ENV_FILE=.env.demo
compose="docker compose --env-file .env.demo -f docker-compose.staging.yml -f docker-compose.demo.yml"
$compose up -d --build
$compose run --rm api alembic upgrade head
$compose exec -T api python scripts/seed-demo-workspace.py
```

4. Reset it nightly:

```bash
sudo cp infra/systemd/groundsops-demo-reset.* /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now groundsops-demo-reset.timer
```

5. Add the link to the README's **Live demo** section.
