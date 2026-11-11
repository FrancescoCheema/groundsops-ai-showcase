"""Delete the dedicated demo workspace so it can be seeded again."""

import argparse

from sqlalchemy import Table, delete, select

import groundsops.models  # noqa: F401  (registers every table on Base.metadata)
from groundsops.config import get_settings
from groundsops.db import Base, SessionLocal
from groundsops.models import Organization
from groundsops.storage import get_object_storage

DEMO_ORGANIZATION_ID = "00000000-0000-4000-8000-000000000001"


def _tenant_tables() -> list[Table]:
    """Tables holding tenant data, children before parents."""
    return [
        table
        for table in reversed(Base.metadata.sorted_tables)
        if table.name != Organization.__tablename__
    ]


def _owner_filter(table: Table, organization_id: str):
    """Rows of ``table`` that belong to the organization.

    Most tables carry organization_id; line-item tables only point at a parent that does.
    """
    if "organization_id" in table.c:
        return table.c.organization_id == organization_id
    for fk in table.foreign_keys:
        parent = fk.column.table
        if "organization_id" in parent.c:
            owned = select(fk.column).where(parent.c.organization_id == organization_id)
            return fk.parent.in_(owned)
    raise RuntimeError(f"Cannot determine tenant ownership for table {table.name}")


def reset(confirmed: bool) -> None:
    settings = get_settings()
    if not settings.demo_workspace_enabled or settings.auth_mode != "development":
        raise RuntimeError(
            "Demo reset requires DEMO_WORKSPACE_ENABLED=true and AUTH_MODE=development"
        )
    if not confirmed:
        raise RuntimeError("Pass --yes to confirm deletion of the dedicated demo workspace")
    with SessionLocal() as db:
        if db.get(Organization, DEMO_ORGANIZATION_ID) is None:
            print("Demo workspace is already absent.")
            return
        tables = _tenant_tables()
        storage_keys: set[str] = set()
        for table in tables:
            key_columns = [column for column in table.c if column.name.endswith("storage_key")]
            for column in key_columns:
                rows = db.execute(
                    select(column).where(_owner_filter(table, DEMO_ORGANIZATION_ID))
                ).scalars()
                storage_keys.update(key for key in rows if key)
        deleted_rows = 0
        for table in tables:
            result = db.execute(delete(table).where(_owner_filter(table, DEMO_ORGANIZATION_ID)))
            deleted_rows += result.rowcount or 0
        db.execute(delete(Organization).where(Organization.id == DEMO_ORGANIZATION_ID))
        db.commit()

    storage = get_object_storage()
    removed_files = 0
    for key in sorted(storage_keys):
        try:
            storage.delete(key)
            removed_files += 1
        except Exception as exc:  # a missing file must not block the reset
            print(f"Could not delete stored object {key}: {exc}")
    print(
        f"Demo workspace deleted: organization={DEMO_ORGANIZATION_ID} "
        f"rows={deleted_rows} files={removed_files}"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--yes", action="store_true")
    reset(parser.parse_args().yes)
