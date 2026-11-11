"""Delete the dedicated demo workspace so it can be seeded again."""

import argparse

from sqlalchemy import select

from groundsops.config import get_settings
from groundsops.db import SessionLocal
from groundsops.models import Organization

DEMO_ORGANIZATION_ID = "00000000-0000-4000-8000-000000000001"


def reset(confirmed: bool) -> None:
    settings = get_settings()
    if not settings.demo_workspace_enabled or settings.auth_mode != "development":
        raise RuntimeError(
            "Demo reset requires DEMO_WORKSPACE_ENABLED=true and AUTH_MODE=development"
        )
    if not confirmed:
        raise RuntimeError("Pass --yes to confirm deletion of the dedicated demo workspace")
    with SessionLocal() as db:
        organization = db.scalar(
            select(Organization).where(Organization.id == DEMO_ORGANIZATION_ID)
        )
        if organization is None:
            print("Demo workspace is already absent.")
            return
        db.delete(organization)
        db.commit()
        print(f"Demo workspace deleted: organization={DEMO_ORGANIZATION_ID}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--yes", action="store_true")
    reset(parser.parse_args().yes)
