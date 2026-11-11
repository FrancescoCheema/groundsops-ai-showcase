from datetime import UTC, datetime
from decimal import Decimal

import pytest

from groundsops.db import SessionLocal
from groundsops.estimates import calculate_material_estimate
from groundsops.models import GenerationJob, GenerationStatus


def test_sod_estimate_applies_waste_labour_delivery_and_tax():
    result = calculate_material_estimate(
        material_type="sod",
        area=Decimal("1000"),
        perimeter=Decimal("140"),
        measurement_unit="ft",
        waste_percent=Decimal("8"),
        depth=None,
        unit_price=Decimal("0.55"),
        labour_rate=Decimal("60"),
        labour_hours=None,
        delivery_cost=Decimal("100"),
        tax_rate=Decimal("12"),
    )

    assert result.order_quantity == Decimal("1080.00")
    assert result.material_unit == "sq ft"
    assert result.labour_hours == Decimal("10.00")
    assert result.material_cost == Decimal("594.00")
    assert result.labour_cost == Decimal("600.00")
    assert result.total == Decimal("1449.28")


def test_mulch_estimate_converts_inches_to_cubic_yards():
    result = calculate_material_estimate(
        material_type="mulch",
        area=Decimal("1000"),
        perimeter=Decimal("140"),
        measurement_unit="ft",
        waste_percent=Decimal("10"),
        depth=Decimal("3"),
        unit_price=Decimal("45"),
        labour_rate=Decimal("0"),
        labour_hours=Decimal("1"),
        delivery_cost=Decimal("0"),
        tax_rate=Decimal("0"),
    )

    assert result.order_quantity == Decimal("10.19")
    assert result.material_unit == "cu yd"


def test_volume_material_requires_depth():
    with pytest.raises(ValueError, match="Depth is required"):
        calculate_material_estimate(
            material_type="gravel",
            area=Decimal("100"),
            perimeter=Decimal("40"),
            measurement_unit="ft",
            waste_percent=Decimal("10"),
            depth=None,
            unit_price=Decimal("0"),
            labour_rate=Decimal("0"),
            labour_hours=None,
            delivery_cost=Decimal("0"),
            tax_rate=Decimal("0"),
        )


def test_material_estimate_is_saved_and_tenant_scoped(client, create_identity):
    organization_id, headers = create_identity("Estimate Landscaping")
    other_organization_id, other_headers = create_identity("Other Estimate Landscaping")
    customer = client.post(
        "/api/v1/customers", headers=headers, json={"name": "Estimate Customer"}
    ).json()
    property_record = client.post(
        "/api/v1/properties",
        headers=headers,
        json={"name": "Estimate Property", "customer_id": customer["id"]},
    ).json()
    design = client.post(
        "/api/v1/design-projects",
        headers=headers,
        json={"name": "Estimate Design", "property_id": property_record["id"]},
    ).json()
    user = client.get("/api/v1/auth/me", headers=headers).json()
    with SessionLocal() as db:
        job = GenerationJob(
            organization_id=organization_id,
            design_project_id=design["id"],
            capture_id="estimate-capture",
            requested_by_user_id=user["id"],
            prompt="Install sod.",
            provider="replicate",
            model_version="test-model",
            status=GenerationStatus.SUCCEEDED.value,
            mask_storage_key=f"estimates/{organization_id}/mask.png",
            output_storage_key=f"estimates/{organization_id}/output.png",
            output_media_type="image/png",
            calibration_unit="ft",
            estimated_area=Decimal("1000"),
            estimated_perimeter=Decimal("140"),
            completed_at=datetime.now(UTC),
        )
        db.add(job)
        db.commit()
        job_id = job.id

    response = client.put(
        f"/api/v1/generations/{job_id}/material-estimate",
        headers=headers,
        json={
            "material_type": "sod",
            "waste_percent": 8,
            "unit_price": 0.55,
            "labour_rate": 60,
            "delivery_cost": 100,
            "tax_rate": 12,
        },
    )

    assert response.status_code == 200
    assert response.json()["order_quantity"] == "1080.00"
    assert response.json()["total"] == "1449.28"
    assert client.get(
        f"/api/v1/generations/{job_id}/material-estimate", headers=headers
    ).status_code == 200
    assert other_organization_id != organization_id
    assert client.get(
        f"/api/v1/generations/{job_id}/material-estimate", headers=other_headers
    ).status_code == 404
