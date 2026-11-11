"""Seed an idempotent public demo workspace.

Run only in a dedicated development-auth demo deployment:
DEMO_WORKSPACE_ENABLED=true python scripts/seed-demo-workspace.py
"""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy import select

from groundsops.config import get_settings
from groundsops.db import SessionLocal
from groundsops.models import (
    Customer,
    DesignProject,
    Invoice,
    InvoiceItem,
    Organization,
    OrganizationUser,
    Property,
    Quote,
    QuoteItem,
    WorkOrder,
)

DEMO_EMAIL = "demo@groundsops.ai"
DEMO_ORGANIZATION = "GroundsOps Demo Landscaping"
DEMO_ORGANIZATION_ID = "00000000-0000-4000-8000-000000000001"


def seed() -> None:
    settings = get_settings()
    if not settings.demo_workspace_enabled or settings.auth_mode != "development":
        raise RuntimeError(
            "Demo seeding requires DEMO_WORKSPACE_ENABLED=true and AUTH_MODE=development"
        )
    with SessionLocal() as db:
        existing = db.scalar(select(OrganizationUser).where(OrganizationUser.email == DEMO_EMAIL))
        if existing is not None:
            print(
                f"Demo already exists: organization={existing.organization_id} "
                f"email={DEMO_EMAIL}"
            )
            return
        organization = Organization(id=DEMO_ORGANIZATION_ID, name=DEMO_ORGANIZATION)
        db.add(organization)
        db.flush()
        admin = OrganizationUser(
            organization_id=organization.id,
            email=DEMO_EMAIL,
            display_name="GroundsOps Demo Admin",
            role="admin",
        )
        crew = OrganizationUser(
            organization_id=organization.id,
            email="crew.demo@groundsops.ai",
            display_name="Alex Demo Crew",
            role="crew",
        )
        db.add_all([admin, crew])
        db.flush()
        customer = Customer(
            organization_id=organization.id,
            name="Evergreen Family Residence",
            email="evergreen@example.com",
            phone="604-555-0182",
            address="1288 Cedar View, Vancouver, BC",
        )
        db.add(customer)
        db.flush()
        property_record = Property(
            organization_id=organization.id,
            customer_id=customer.id,
            name="Cedar View Front Yard",
            location="1288 Cedar View, Vancouver, BC",
        )
        db.add(property_record)
        db.flush()
        design = DesignProject(
            organization_id=organization.id,
            property_id=property_record.id,
            name="Low-maintenance front-yard redesign",
            goal="Replace worn lawn with drought-tolerant planting, pavers and fresh borders.",
            status="accepted",
        )
        db.add(design)
        db.flush()
        quote = Quote(
            organization_id=organization.id,
            design_project_id=design.id,
            number="Q-DEMO-0001",
            title="Front-yard landscape installation",
            status="approved",
            subtotal=Decimal("6125.00"),
            markup_rate=Decimal("10"),
            markup_amount=Decimal("612.50"),
            discount_amount=Decimal("250.00"),
            tax_rate=Decimal("5"),
            tax_amount=Decimal("324.38"),
            total=Decimal("6811.88"),
            currency="CAD",
            assumptions="Demo measurements were verified on site before ordering.",
        )
        quote.items = [
            QuoteItem(
                description="Premium sod and soil",
                category="material",
                quantity=Decimal("650"),
                unit="sq_ft",
                unit_price=Decimal("4.25"),
                line_total=Decimal("2762.50"),
                position=0,
            ),
            QuoteItem(
                description="Paver border",
                category="material",
                quantity=Decimal("85"),
                unit="linear_ft",
                unit_price=Decimal("12.50"),
                line_total=Decimal("1062.50"),
                position=1,
            ),
            QuoteItem(
                description="Installation labour",
                category="labour",
                quantity=Decimal("40"),
                unit="hour",
                unit_price=Decimal("57.50"),
                line_total=Decimal("2300.00"),
                position=2,
            ),
        ]
        db.add(quote)
        db.flush()
        start = datetime.now(UTC) + timedelta(days=3)
        work_order = WorkOrder(
            organization_id=organization.id,
            property_id=property_record.id,
            quote_id=quote.id,
            design_project_id=design.id,
            title=quote.title,
            description=f"Created from approved quote {quote.number}.",
            status="scheduled",
            assigned_user_id=crew.id,
            scheduled_start=start,
            scheduled_end=start + timedelta(hours=8),
            priority="high",
            quoted_total=quote.total,
            quote_currency="CAD",
            material_checklist=[
                {
                    "description": "Premium sod and soil",
                    "category": "material",
                    "quantity": "650",
                    "unit": "sq_ft",
                },
                {
                    "description": "Paver border",
                    "category": "material",
                    "quantity": "85",
                    "unit": "linear_ft",
                },
            ],
            customer_instructions="Protect the driveway and use the side gate.",
        )
        db.add(work_order)
        invoice = Invoice(
            organization_id=organization.id,
            customer_id=customer.id,
            number="INV-DEMO-0001",
            description="Landscape design deposit",
            quantity=Decimal("1"),
            rate=Decimal("1500.00"),
            subtotal=Decimal("1500.00"),
            currency="CAD",
            status="sent",
            customer_name=customer.name,
            customer_email=customer.email,
            customer_phone=customer.phone,
            customer_address=customer.address,
            gst_rate=Decimal("5"),
            pst_rate=Decimal("0"),
            gst_amount=Decimal("75.00"),
            pst_amount=Decimal("0"),
            total=Decimal("1575.00"),
            notes="Seeded demonstration invoice.",
        )
        invoice.items = [
            InvoiceItem(
                description="Landscape design deposit",
                quantity=Decimal("1"),
                rate=Decimal("1500.00"),
                line_total=Decimal("1500.00"),
                position=0,
            )
        ]
        db.add(invoice)
        db.commit()
        print(f"Demo seeded: organization={organization.id} email={DEMO_EMAIL}")


if __name__ == "__main__":
    seed()
