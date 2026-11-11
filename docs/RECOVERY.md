# Disaster recovery

1. Declare the incident and stop writes when integrity is uncertain.
2. Preserve logs and identify the last known-good deployment and backup.
3. Restore into an isolated database and verify the dump before touching production.
4. Run migrations, `/ready`, the smoke test and the complete customer-to-invoice workflow.
5. Redirect traffic only after authorization and record recovery time and data-loss window.

Test `scripts/verify-backup-restore.sh` automatically and perform a documented staging restore quarterly. Cognito recovery requires verified administrator access and exported configuration. S3 recovery requires versioning, encryption keys and tested IAM access. Failed deployments should roll back application images first; restore data only when writes are incompatible or corrupted.

