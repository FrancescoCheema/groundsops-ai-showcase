# GroundsOps commercial release runbook

## Release gate

Before deploying, require all backend, frontend, browser workflow, dependency and secret-scanning jobs to pass. Confirm the deployment commit matches `origin/main`, back up PostgreSQL, and verify that `.env.staging` contains no placeholder secrets.

```bash
python -m ruff check .
python -m pytest
npm --prefix frontend ci
npm --prefix frontend run build
npm --prefix frontend run test:e2e
```

The business workflow test covers customer, property, design, concept approval, measurement, estimate, quote approval, scheduling, crew assignment, completion, invoice creation, partial payment and final settlement. Paid AI calls remain mocked in CI.

## Deploy

```bash
git fetch origin
git checkout main
git pull --ff-only origin main
sudo docker compose --env-file .env.staging -f docker-compose.staging.yml build
sudo docker compose --env-file .env.staging -f docker-compose.staging.yml run --rm api alembic upgrade head
sudo docker compose --env-file .env.staging -f docker-compose.staging.yml up -d --force-recreate
curl --fail https://YOUR_HOST/health
curl --fail https://YOUR_HOST/ready
```

`/health` proves the process is responding. `/ready` proves the database and object storage are available. Do not send traffic when readiness returns 503.

## Demo workspace

Use a separate development-auth deployment. Never enable demo mode in a customer environment.

```bash
export AUTH_MODE=development
export DEMO_WORKSPACE_ENABLED=true
python scripts/reset-demo-workspace.py --yes
python scripts/seed-demo-workspace.py
```

The reset command can only target the fixed demo organization ID and refuses to run unless both safety flags are enabled.

## Backup and restore drill

Create an encrypted PostgreSQL dump before every schema migration. Quarterly, restore the dump into an isolated database, run `alembic upgrade head`, and execute the complete business workflow. Record the dump timestamp, restore duration and operator.

## Rollback

1. Stop incoming traffic or put the application into maintenance mode.
2. Redeploy the previously known-good commit and image.
3. If the release wrote incompatible data, restore the pre-release database backup. Do not blindly downgrade a migration after customer writes.
4. Verify `/ready`, sign in, and open customers, Design Studio, scheduling and invoices.
5. Document the incident and preserve logs.

## Operational checks

- Alert on readiness failures, HTTP 5xx rate, repeated 429 responses and background generation failures.
- Review AI spend and failed quality evaluations daily while the product is in pilot.
- Rotate JWT, object-storage and Replicate credentials after any suspected disclosure.
- Confirm rate limiting is enabled in staging and production.
- Re-run the smoke test after certificate renewal and every deployment.

## Deferred external integrations

Stripe payment capture, transactional email, live vendor inventory, and native AR/LiDAR measurement require provider credentials and separate acceptance testing. The current payment ledger records externally received payments; it does not charge a card. Camera measurements remain estimates and must be verified on site before ordering materials.
