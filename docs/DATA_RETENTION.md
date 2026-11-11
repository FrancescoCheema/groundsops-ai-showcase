# Data retention

Default operational policy:

| Data | Default retention |
|---|---:|
| Active customer and job records | Contract duration |
| Soft-deleted vault files | 30 days |
| Application logs | 30 days |
| Database backups | 35 days, with at least one monthly copy |
| Failed temporary generation artifacts | 30 days |
| Security audit records | 365 days |

Run `python scripts/purge-retained-data.py` to preview expired vault records and add `--apply` only during an approved maintenance window. Customer deletion requests require deletion from the primary database, object storage, search indexes and backups according to the operator's legal obligations. Record every production purge.

