# GroundsOps AWS staging deployment

This environment is intended for realistic iPhone testing and a small private beta. It runs Caddy,
the exported Next.js frontend, FastAPI, and PostgreSQL on one 2 GB Lightsail server. Private uploads
remain in S3 and user identity remains in Cognito.

## 1. Prerequisites

Use the Windows development machine for provisioning. Install and authenticate:

```powershell
aws configure
aws sts get-caller-identity
terraform version
```

Select `ca-central-1`. Never commit AWS credentials, `.env.staging`, Terraform state, or Cognito
secrets.

## 2. Provision Cognito and private storage

If these modules are already applied, do not create duplicates. Read their current outputs instead.

```powershell
cd infra\cognito
terraform init
terraform apply
terraform output

cd ..\storage
Copy-Item terraform.tfvars.example terraform.tfvars
terraform init
terraform apply
terraform output
```

Use the final HTTPS application origin in `allowed_origins` when it is known. The storage module
keeps the bucket private, enables versioning, encrypts objects, expires incomplete uploads, and
retains database backups for 30 days.

Create a dedicated IAM user named `groundsops-staging-storage` with only the policy returned by:

```powershell
terraform output -raw application_iam_policy_json
```

Create one access key for that user. Store it only in the server's `.env.staging`. Lightsail does not
support attaching an EC2 instance profile, which is why this tightly scoped key is required in this
low-cost architecture.

## 3. Provision the Lightsail server

Find the public IP of the computer that will administer the server:

```powershell
(Invoke-RestMethod https://checkip.amazonaws.com).Trim()
```

Create the local variable file:

```powershell
cd ..\lightsail
Copy-Item terraform.tfvars.example terraform.tfvars
notepad terraform.tfvars
```

Set the public IP with `/32`, the billing-alert email, and a USD budget:

```hcl
aws_region         = "ca-central-1"
availability_zone  = "ca-central-1a"
environment        = "staging"
bundle_id          = "small_3_0"
ssh_allowed_cidrs  = ["203.0.113.10/32"]
billing_email      = "you@example.com"
monthly_budget_usd = 35
```

Provision only after reviewing the plan:

```powershell
terraform init
terraform fmt
terraform validate
terraform plan -out staging.tfplan
terraform apply staging.tfplan
terraform output
```

This action starts AWS billing. Keep the Terraform state private and backed up.

## 4. Point a domain at the static IP

Create an `A` record with the DNS provider:

```text
staging.yourdomain.com -> PUBLIC_IP_FROM_TERRAFORM
```

Wait until this returns the Lightsail IP:

```powershell
Resolve-DnsName staging.yourdomain.com
```

Caddy requests and renews the TLS certificate automatically after DNS resolves and ports 80/443
reach the server.

## 5. Connect and install the application

Download the regional Lightsail default private key from the AWS console, restrict its permissions,
and connect using the Terraform output. Alternatively, use the Lightsail browser SSH terminal for
the first installation.

On the server:

```bash
cloud-init status --wait
docker --version
git clone https://github.com/FrancescoCheema/GroundsOps-AI.git /opt/groundsops/app
cd /opt/groundsops/app
git switch main
cp .env.staging.example .env.staging
nano .env.staging
```

If the repository is private, use a read-only GitHub deploy key rather than putting a personal token
in the clone URL.

Populate `.env.staging` with:

- the real application domain;
- a random PostgreSQL password;
- Cognito issuer, client ID, and JWKS URL;
- the private S3 bucket name;
- the scoped IAM access key;
- the exact HTTPS and Capacitor CORS origins; and
- the S3 database backup destination.

Generate the database password on the server:

```bash
openssl rand -hex 32
chmod 600 .env.staging
chmod +x scripts/deploy-staging.sh scripts/backup-staging-db.sh
./scripts/deploy-staging.sh
```

## 6. Enable nightly encrypted database backups

Test one backup first:

```bash
./scripts/backup-staging-db.sh
```

Then schedule it at 09:15 UTC:

```bash
(crontab -l 2>/dev/null; echo '15 9 * * * /opt/groundsops/app/scripts/backup-staging-db.sh >> /var/log/groundsops-backup.log 2>&1') | crontab -
```

Confirm the object appears under `database-backups/` in the private S3 bucket. A backup is not proven
until a restore has also been tested.

## 7. Validate staging

```bash
curl --fail https://staging.yourdomain.com/health
curl --fail https://staging.yourdomain.com/ready
docker compose --env-file .env.staging -f docker-compose.staging.yml ps
docker compose --env-file .env.staging -f docker-compose.staging.yml logs --tail=100
```

Sign-up is invite-only, so create the first workspace (your own) from the server and open the
invitation link it prints:

```bash
docker compose --env-file .env.staging -f docker-compose.staging.yml exec -T api \
  python scripts/create-workspace.py --name "Your Company" --owner-email you@example.com
```

Open the link, create your Cognito account with that exact email, verify it, and upload a small test
file. To manage other companies from **Platform admin**, add yourself to the
`groundsops-platform-admins` Cognito group (see the Cognito outputs in `infra/cognito`).

## 8. Connect the iOS application

On the MacBook, set `frontend/.env.local`:

```text
NEXT_PUBLIC_API_URL=https://staging.yourdomain.com
NEXT_PUBLIC_AUTH_MODE=cognito
NEXT_PUBLIC_COGNITO_REGION=ca-central-1
NEXT_PUBLIC_COGNITO_CLIENT_ID=your-client-id
NEXT_PUBLIC_STORAGE_DIRECT_URLS=true
```

Then synchronize and run:

```bash
cd frontend
npm install
npm run ios:setup
# For later web changes:
npm run ios:sync
```

Because staging uses trusted HTTPS, remove any temporary `Allow Arbitrary Loads` exception from the
iOS target before TestFlight.

## 9. Import existing local data only if needed

Do not copy the raw Docker volume. Export and restore through PostgreSQL tools:

```powershell
docker compose exec -T db pg_dump -U groundsops -d groundsops --no-owner --no-acl > groundsops-local.sql
```

Transfer the dump securely, stop API writes, back up staging, and restore into the staging database.
For initial testing, creating a clean company is safer than importing demonstration records.

## 10. Operating limits

This is a cost-controlled single-server staging/private-beta architecture, not high availability.
Before storing important data for paying customers:

- move PostgreSQL to RDS;
- test point-in-time recovery;
- add centralized monitoring and alerts;
- add automated deployment rollback; and
- complete security and privacy review.
