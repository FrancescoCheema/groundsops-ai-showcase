# Staging deployment

GroundsOps staging deploys through the manually triggered `Deploy staging`
GitHub Actions workflow. Validation runs on a GitHub-hosted runner. Deployment
runs on a dedicated self-hosted runner on Lightsail using an outbound HTTPS
connection to GitHub, so SSH remains restricted to the administrator's IP. The
server creates an encrypted PostgreSQL backup in S3, advances to the exact
requested commit, runs Alembic, restarts the stack, and verifies `/ready`.

## GitHub environment

Create an environment named `staging`. Add an approval rule if the repository
plan supports protected environments.

Add this environment variable:

- `STAGING_URL`: the public HTTPS origin, without a trailing slash.

The existing GitHub repository deploy key remains read-only and is copied to
the dedicated runner account. The runner is labelled `groundsops-staging` and
is used only by the environment-protected deployment job. Pull-request jobs
must never target this runner.

## Release

Open **Actions**, select **Deploy staging**, and choose **Run workflow**. Leave
the revision blank to deploy the commit associated with the workflow run, or
provide a full 40-character commit SHA.

The deployment stops when validation, backup, migration, container health, or
public readiness fails. Inspect the failed workflow step and server container
logs before retrying.
