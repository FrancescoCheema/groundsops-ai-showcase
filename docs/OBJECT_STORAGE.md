# Private object storage

GroundsOps supports local disk for development and private S3-compatible storage for staging and
production. Database rows contain opaque object keys; bucket names and credentials are never sent
to clients.

## Object layout

New objects use tenant-scoped keys:

```text
organizations/{organization_id}/vault/{file_id}/{filename}
organizations/{organization_id}/captures/{capture_id}/original.jpg
organizations/{organization_id}/generations/{job_id}/mask.png
organizations/{organization_id}/generations/{job_id}/output.png
organizations/{organization_id}/branding/{logo_id}/logo.png
```

The API verifies the authenticated organization and role before returning a signed URL. Signed URLs
expire after five minutes by default and their API responses use `Cache-Control: private, no-store`.

## AWS deployment

Create the staging bucket with Terraform:

```bash
cd infra/storage
cp terraform.tfvars.example terraform.tfvars
terraform init
terraform plan
terraform apply
```

Attach the sensitive `application_iam_policy_json` output to the API task role. Prefer an IAM role
on AWS; do not create long-lived access keys for ECS.

Set the backend variables:

```text
STORAGE_BACKEND=s3
S3_BUCKET=<terraform bucket_name output>
S3_REGION=ca-central-1
STORAGE_SIGNED_URL_TTL_SECONDS=300
```

For an S3-compatible provider, also configure `S3_ENDPOINT_URL`, `S3_ACCESS_KEY_ID`, and
`S3_SECRET_ACCESS_KEY` through the hosting platform's secret manager. Set
`S3_FORCE_PATH_STYLE=true` when the provider requires path-style addressing. If it encrypts every
object automatically but rejects S3 encryption headers, set `S3_SERVER_SIDE_ENCRYPTION=none`.

Set the frontend variable after bucket CORS is configured:

```text
NEXT_PUBLIC_STORAGE_DIRECT_URLS=true
```

Keep the bucket private. Never add a public bucket policy or store credentials in frontend
environment variables. Existing objects written with older keys remain readable; only new uploads
use the standardized tenant path.
