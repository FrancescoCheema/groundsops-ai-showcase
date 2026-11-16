"""Seed an idempotent public demo workspace.

Run only in a dedicated development-auth demo deployment:
DEMO_WORKSPACE_ENABLED=true python scripts/seed-demo-workspace.py
"""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from hashlib import sha256
from pathlib import Path

from sqlalchemy import select

from groundsops.config import get_settings
from groundsops.db import SessionLocal
from groundsops.estimates import calculate_material_estimate
from groundsops.models import (
    Customer,
    DesignProject,
    GenerationEvaluation,
    GenerationJob,
    GenerationMaterialEstimate,
    GenerationReview,
    Invoice,
    InvoiceItem,
    Organization,
    OrganizationUser,
    PriceListItem,
    Property,
    Quote,
    QuoteItem,
    SiteCapture,
    WorkOrder,
)
from groundsops.storage import get_object_storage, tenant_storage_key

DEMO_EMAIL = "demo@groundsops.ai"
DEMO_ORGANIZATION = "GroundsOps Demo Landscaping"
DEMO_ORGANIZATION_ID = "00000000-0000-4000-8000-000000000001"
ASSETS = Path(__file__).resolve().parent / "demo-assets"
# Price list used to pre-fill estimates: (unit price, waste %, depth in inches, supplier).
DEMO_PRICES = {
    "sod": ("0.85", "8", None, "Fraser Valley sod farm"),
    "pavers": ("6.50", "10", None, "Local stone supplier"),
    "mulch": ("55", "10", "3", None),
    "gravel": ("60", "10", "3", None),
    "topsoil": ("45", "10", "4", None),
}


def _seed_backyard_concept(db, organization: Organization, admin: OrganizationUser) -> None:
    """A real before/after: a bare-soil backyard and its approved AI lawn concept."""
    storage = get_object_storage()
    customer = Customer(
        organization_id=organization.id,
        name="Jordan Patel",
        email="jordan@example.com",
        phone="604-555-0142",
        address="Surrey, BC",
    )
    db.add(customer)
    db.flush()
    backyard = Property(
        organization_id=organization.id,
        customer_id=customer.id,
        name="Patel Backyard",
        location="Surrey, BC",
    )
    db.add(backyard)
    db.flush()
    design = DesignProject(
        organization_id=organization.id,
        property_id=backyard.id,
        name="Backyard lawn renovation",
        goal="Turn the bare soil left after new fencing into a full lawn.",
        status="accepted",
    )
    db.add(design)
    db.flush()

    before = (ASSETS / "backyard-before.jpg").read_bytes()
    capture = SiteCapture(
        organization_id=organization.id,
        design_project_id=design.id,
        uploaded_by_user_id=admin.id,
        original_filename="backyard-site.jpg",
        storage_key="",
        media_type="image/jpeg",
        byte_size=len(before),
        width=1360,
        height=1020,
        sha256=sha256(before).hexdigest(),
    )
    db.add(capture)
    db.flush()
    capture.storage_key = tenant_storage_key(
        organization.id, "captures", capture.id, "backyard-site.jpg"
    )
    storage.put(capture.storage_key, before, "image/jpeg")

    completed = datetime.now(UTC) - timedelta(days=1)
    job = GenerationJob(
        organization_id=organization.id,
        design_project_id=design.id,
        capture_id=capture.id,
        requested_by_user_id=admin.id,
        prompt="New sod lawn",
        provider="replicate",
        model_version="demo-concept-v1",
        status="succeeded",
        mask_storage_key="",
        measurement_method="reference_line",
        selected_pixel_count=489436,
        total_pixel_count=1360 * 1020,
        calibration_pixel_length=Decimal("428.8"),
        calibration_real_length=Decimal("8"),
        calibration_unit="ft",
        estimated_area=Decimal("171.3"),
        estimated_perimeter=Decimal("63.0"),
        measurement_confidence="photo_estimate",
        output_media_type="image/jpeg",
        latency_ms=31000,
        estimated_cost_usd=Decimal("0.0500"),
        created_at=completed - timedelta(seconds=40),
        started_at=completed - timedelta(seconds=35),
        completed_at=completed,
    )
    db.add(job)
    db.flush()
    job.mask_storage_key = tenant_storage_key(organization.id, "generations", job.id, "mask.png")
    job.output_storage_key = tenant_storage_key(
        organization.id, "generations", job.id, "output.jpg"
    )
    storage.put(job.mask_storage_key, (ASSETS / "backyard-mask.png").read_bytes(), "image/png")
    storage.put(
        job.output_storage_key, (ASSETS / "backyard-concept.jpg").read_bytes(), "image/jpeg"
    )
    db.add(
        GenerationEvaluation(
            organization_id=organization.id,
            generation_job_id=job.id,
            evaluator_version="pixel-change-v1",
            dimensions_match=True,
            masked_change_ratio=Decimal("0.950000"),
            protected_change_ratio=Decimal("0.000000"),
            masked_change_threshold=Decimal("0.200000"),
            protected_change_threshold=Decimal("0.080000"),
            pixel_change_threshold=Decimal("0.050000"),
            passed=True,
            failure_reasons=[],
            evaluation_latency_ms=120,
        )
    )
    # A saved estimate from the price list, so the PDF quote is one click away.
    price, waste, _depth, _supplier = DEMO_PRICES["sod"]
    inputs = {
        "material_type": "sod",
        "waste_percent": Decimal(waste),
        "depth": None,
        "unit_price": Decimal(price),
        "labour_rate": organization.estimate_labour_rate,
        "delivery_cost": organization.estimate_delivery_cost,
        "tax_rate": organization.estimate_tax_rate,
    }
    result = calculate_material_estimate(
        area=job.estimated_area,
        perimeter=job.estimated_perimeter,
        measurement_unit=job.calibration_unit,
        labour_hours=None,
        **inputs,
    )
    db.add(
        GenerationMaterialEstimate(
            organization_id=organization.id,
            generation_job_id=job.id,
            measurement_unit=job.calibration_unit,
            measured_area=job.estimated_area,
            measured_perimeter=job.estimated_perimeter,
            order_quantity=result.order_quantity,
            material_unit=result.material_unit,
            edging_quantity=result.edging_quantity,
            labour_hours=result.labour_hours,
            material_cost=result.material_cost,
            labour_cost=result.labour_cost,
            subtotal=result.subtotal,
            tax_amount=result.tax_amount,
            total=result.total,
            currency="CAD",
            assumptions=result.assumptions,
            **inputs,
        )
    )
    db.add(
        GenerationReview(
            organization_id=organization.id,
            generation_job_id=job.id,
            reviewer_user_id=admin.id,
            decision="approved",
            notes="Customer approved the full-lawn concept.",
        )
    )


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
        organization.contact_email = "office@groundsops-demo.ca"
        organization.contact_phone = "604-555-0100"
        organization.contact_address = "Surrey, BC"
        organization.estimate_labour_rate = Decimal("65")
        organization.estimate_delivery_cost = Decimal("150")
        organization.estimate_tax_rate = Decimal("5")
        logo = (ASSETS / "demo-logo.png").read_bytes()
        organization.logo_storage_key = tenant_storage_key(
            organization.id, "branding", "logo", "demo-logo.png"
        )
        organization.logo_media_type = "image/png"
        get_object_storage().put(organization.logo_storage_key, logo, "image/png")
        for material, (price, waste, depth, supplier) in DEMO_PRICES.items():
            db.add(
                PriceListItem(
                    organization_id=organization.id,
                    material_type=material,
                    unit_price=Decimal(price),
                    waste_percent=Decimal(waste),
                    depth=Decimal(depth) if depth else None,
                    supplier=supplier,
                )
            )
        # Seeded first so it leads the Design studio list.
        _seed_backyard_concept(db, organization, admin)
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
