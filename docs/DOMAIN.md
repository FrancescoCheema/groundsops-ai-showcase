# Domain: groundsopsai.ca

The domain is registered in Route 53, which also creates its public hosted zone. Each
environment gets its own name, created by Terraform in `infra/lightsail` (`dns.tf`):

| Environment | Name | Terraform workspace | Variables |
| --- | --- | --- | --- |
| Staging | `staging.groundsopsai.ca` | `default` | `hostname = "staging"` |
| Production | `app.groundsopsai.ca` | `production` | `hostname = "app"` |
| Public demo | `demo.groundsopsai.ca` | `demo` | `hostname = "demo"` |

Commands below are for PowerShell on your computer, plus SSH to the server.

## 1. Wait for the registration

1. Route 53 → **Registered domains**: the status should be *Successful*.
2. Accept the emails from AWS (email verification) and from CIRA (registrant agreement).
   A `.ca` is suspended if these are not confirmed within about 15 days.
3. Check that the hosted zone exists:

   ```powershell
   aws route53 list-hosted-zones-by-name --dns-name groundsopsai.ca --max-items 1
   ```

## 2. Point staging at the server

In `infra/lightsail`, add the two variables to your local `terraform.tfvars` (it is not
committed). Keeping them there matters: a later plan without them would delete the record.

```hcl
domain_name = "groundsopsai.ca"
hostname    = "staging"
```

```powershell
cd infra/lightsail
terraform workspace select default
terraform plan
```

The plan must show **1 to add** (`aws_route53_record.app[0]`) and nothing to change or
destroy. Then:

```powershell
terraform apply
Resolve-DnsName staging.groundsopsai.ca
```

The name should resolve to the staging static IP (`terraform output public_ip`). New
records usually resolve within a few minutes.

## 3. Switch the staging server to the new name

Over SSH on the staging server:

```bash
cd /opt/groundsops/app
cp .env.staging ".env.staging.bak-$(date +%F)"
sed -i \
  -e 's#^APP_DOMAIN=.*#APP_DOMAIN=staging.groundsopsai.ca#' \
  -e 's#^APP_PUBLIC_URL=.*#APP_PUBLIC_URL=https://staging.groundsopsai.ca#' \
  -e 's#^CORS_ORIGIN_REGEX=.*#CORS_ORIGIN_REGEX="^(https://staging\\.groundsopsai\\.ca|capacitor://localhost)$"#' \
  .env.staging
grep -E '^(APP_DOMAIN|APP_PUBLIC_URL|CORS_ORIGIN_REGEX)=' .env.staging
docker compose --env-file .env.staging -f docker-compose.staging.yml up -d --build web api
curl -fsS https://staging.groundsopsai.ca/ready
```

`web` is rebuilt because the API address is built into the frontend, and Caddy requests a
new TLS certificate for the name on first request. The old `sslip.io` address stops working
after this; update anything that links to it.

## 4. Point CI at the new name

GitHub → the repository → **Settings → Secrets and variables → Actions → Variables** →
edit `STAGING_URL` to `https://staging.groundsopsai.ca`. The deploy, smoke test and
monitor workflows read it.

If Stripe test mode is set up, update the webhook endpoint to
`https://staging.groundsopsai.ca/api/v1/billing/webhook`.

## Production and demo

When following [PRODUCTION.md](PRODUCTION.md) and [DEMO_SERVER.md](DEMO_SERVER.md), add the
variables to that workspace's plan instead of creating DNS records by hand:

```powershell
terraform workspace select production
terraform plan -var "environment=production" -var "domain_name=groundsopsai.ca" -var "hostname=app"
```

```powershell
terraform workspace select demo
terraform plan -var "environment=demo" -var "bundle_id=small_3_0" -var "domain_name=groundsopsai.ca" -var "hostname=demo"
```

Then use `https://app.groundsopsai.ca` and `https://demo.groundsopsai.ca` for `APP_DOMAIN`,
`APP_PUBLIC_URL`, `CORS_ORIGIN_REGEX` and the `PRODUCTION_URL` repository variable.

## Costs

The domain renews yearly (auto-renew on), and the hosted zone is about USD 0.50 a month.
