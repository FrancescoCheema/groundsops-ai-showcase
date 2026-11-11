import argparse
from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from groundsops.db import SessionLocal
from groundsops.models import VaultFile
from groundsops.storage import get_object_storage

parser = argparse.ArgumentParser(description="Purge expired soft-deleted vault files")
parser.add_argument("--days", type=int, default=30)
parser.add_argument("--apply", action="store_true")
args = parser.parse_args()
if args.days < 1:
    raise SystemExit("--days must be positive")
cutoff = datetime.now(UTC) - timedelta(days=args.days)
with SessionLocal() as db:
    records = list(
        db.scalars(
            select(VaultFile).where(
                VaultFile.deleted_at.is_not(None), VaultFile.deleted_at < cutoff
            )
        )
    )
    print(f"candidates={len(records)} cutoff={cutoff.isoformat()} apply={args.apply}")
    if args.apply:
        storage = get_object_storage()
        for record in records:
            storage.delete(record.storage_key)
            db.delete(record)
        db.commit()
        print(f"purged={len(records)}")
