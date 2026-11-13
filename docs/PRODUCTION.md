# Production environment

Production runs the same stack as staging (`docker-compose.staging.yml`) on its own Lightsail
instance, with its own Cognito pool, S3 bucket, database and Stripe live keys. Deploys are manual
and approval-gated.

## 1. Create the infrastructure

Terraform state is local to each `infra/*` folder. Back up the `terraform.tfstate*` files first.
Then create production in its own workspace so staging state is untouched:

```bash
for dir in infra/cognito infra/storage infra/lightsail; do
  (cd "$dir" && terraform workspace new production && terraform apply -var "environment=production")
done
```

Point `app.<your-domain>` (A record) at the production static IP.

## 2. Prepare the server

Follow [LIGHTSAIL_STAGING.md](LIGHTSAIL_STAGING.md) on the new instance, with two differences:

- Put the settings in `/opt/groundsops/app/.env.production` (copy `.env.staging.example`), using the
  **production** Cognito, S3 and Stripe live values and a new database password.
- Every script reads `GROUNDSOPS_ENV_FILE`; set it to `.env.production` for systemd timers:

```bash
sudo systemctl edit groundsops-backup.service   # add: [Service] Environment=GROUNDSOPS_ENV_FILE=.env.production
sudo systemctl edit groundsops-monitor.service  # same line
```

## 3. Register the production runner

Register a self-hosted GitHub Actions runner on the production server **with only the
`production` label**, so staging jobs (`[self-hosted, linux, x64]`) can never run there:

```bash
./config.sh --url https://github.com/<owner>/<repo> --token <token> --no-default-labels --labels production
```

## 4. Protect and deploy

1. GitHub → Settings → Environments → **production** → add yourself as a required reviewer.
2. GitHub → Settings → Variables → add `PRODUCTION_URL` (for example `https://app.example.com`).
3. Actions → **Deploy production** → Run workflow, with the full SHA of a `main` commit that is
   already green on staging. Approve the run when prompted.

The workflow checks the commit is on `main`, syncs the server checkout to it, takes a verified
database backup, builds, runs migrations and checks `/ready`.

## 5. Create your first workspace

A fresh production database has no users, and sign-up is invite-only. Create your own workspace from
the server, open the printed link, and sign up with that exact email:

```bash
cd /opt/groundsops/app
docker compose --env-file .env.production -f docker-compose.staging.yml exec -T api \
  python scripts/create-workspace.py --name "GroundsOps" --owner-email you@example.com
```

Then add yourself to the `groundsops-platform-admins` group in the **production** Cognito pool, and
create customer workspaces from **Platform admin → Create a workspace**.

## 6. Prove recovery

Run `scripts/verify-backup-restore.sh` once against a production backup, and
`scripts/configure-lightsail-alarms.ps1` for the production instance.
