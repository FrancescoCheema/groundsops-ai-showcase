import importlib.util
from decimal import Decimal
from pathlib import Path

from sqlalchemy import func, select

from groundsops.config import get_settings
from groundsops.db import SessionLocal
from groundsops.models import (
    Customer,
    Invoice,
    InvoiceItem,
    InvoicePayment,
    Organization,
    OrganizationUser,
    Property,
)

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "reset-demo-workspace.py"


def _load_reset():
    spec = importlib.util.spec_from_file_location("reset_demo_workspace", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_reset_removes_demo_data_including_line_items_and_keeps_other_tenants(monkeypatch):
    reset = _load_reset()
    settings = get_settings()
    monkeypatch.setattr(settings, "demo_workspace_enabled", True)
    monkeypatch.setattr(settings, "auth_mode", "development")
    demo_id = reset.DEMO_ORGANIZATION_ID

    with SessionLocal() as db:
        for org_id, name in ((demo_id, "Demo"), ("other-org", "Other")):
            db.add(Organization(id=org_id, name=name))
            db.flush()
            db.add(OrganizationUser(organization_id=org_id, email=f"{name}@example.com",
                                    display_name=name, role="admin"))
            customer = Customer(organization_id=org_id, name=f"{name} customer")
            db.add(customer)
            db.flush()
            db.add(Property(organization_id=org_id, customer_id=customer.id, name="Yard"))
            invoice = Invoice(organization_id=org_id, customer_id=customer.id,
                              number=f"INV-{name}", description="Sod installation",
                              quantity=Decimal("1"), rate=Decimal("100"), subtotal=Decimal("100"))
            db.add(invoice)
            db.flush()
            db.add(InvoiceItem(invoice_id=invoice.id, description="Sod", quantity=Decimal("1"),
                               rate=Decimal("100"), line_total=Decimal("100")))
            db.add(InvoicePayment(organization_id=org_id, invoice_id=invoice.id,
                                  amount=Decimal("50"), method="etransfer"))
        db.commit()

    reset.reset(confirmed=True)

    with SessionLocal() as db:
        assert db.get(Organization, demo_id) is None
        assert db.get(Organization, "other-org") is not None
        assert db.scalar(select(func.count()).select_from(Customer)) == 1
        assert db.scalar(select(func.count()).select_from(InvoiceItem)) == 1
        assert db.scalar(select(func.count()).select_from(InvoicePayment)) == 1

    reset.reset(confirmed=True)  # idempotent when the workspace is already gone
