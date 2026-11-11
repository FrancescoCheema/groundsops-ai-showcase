# Public release checklist

- [ ] Full-history Gitleaks scan passes.
- [ ] Every historical credential finding is rotated and documented.
- [ ] No environment files, dumps, reports, logs, keys or customer data are tracked.
- [ ] Every README screenshot is manually reviewed and contains demo-only data.
- [ ] Demo uses `INFERENCE_PROVIDER=mock` and cannot incur paid inference charges.
- [ ] Quality, security, public-release, deployment and staging smoke workflows pass on `main`.
- [ ] Backup restore drill passes in an isolated database.
- [ ] Test alert is received by the configured on-call destination.
- [ ] Load smoke thresholds pass.
- [ ] Rate limiting and required malware scanning are enabled outside development.
- [ ] Privacy, terms, security, support, retention and recovery documents are reviewed.
- [ ] Controlled beta owner and participants are identified.
- [ ] Main branch protection requires passing checks and pull-request review.
- [ ] Repository topics and homepage are configured.
- [ ] `v1.0.0` tag and GitHub release are created from verified `main`.

Items requiring credentials, legal approval or GitHub administration cannot be truthfully automated. Attach evidence for each completed item.

