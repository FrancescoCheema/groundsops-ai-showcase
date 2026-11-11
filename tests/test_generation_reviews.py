from datetime import UTC, datetime

from groundsops.db import SessionLocal
from groundsops.models import GenerationJob, GenerationStatus


def _design(client, headers):
    customer = client.post(
        "/api/v1/customers", headers=headers, json={"name": "Review Customer"}
    ).json()
    property_record = client.post(
        "/api/v1/properties",
        headers=headers,
        json={"name": "Review Property", "customer_id": customer["id"]},
    ).json()
    return client.post(
        "/api/v1/design-projects",
        headers=headers,
        json={"name": "Review Design", "property_id": property_record["id"]},
    ).json()


def _job(client, organization_id, headers, *, status="succeeded"):
    design = _design(client, headers)
    user = client.get("/api/v1/auth/me", headers=headers).json()
    with SessionLocal() as db:
        job = GenerationJob(
            organization_id=organization_id,
            design_project_id=design["id"],
            capture_id="review-capture",
            requested_by_user_id=user["id"],
            prompt="Replace the selected lawn with drought-tolerant landscaping.",
            provider="replicate",
            model_version="landscape-model-v1",
            status=status,
            mask_storage_key=f"reviews/{organization_id}/mask.png",
            output_storage_key=f"reviews/{organization_id}/output.png",
            output_media_type="image/png",
            completed_at=(
                datetime.now(UTC) if status == GenerationStatus.SUCCEEDED.value else None
            ),
        )
        db.add(job)
        db.commit()
        return job.id, design["id"]


def test_generation_review_preserves_audit_history(client, create_identity):
    organization_id, headers = create_identity("Review History Landscaping")
    job_id, design_id = _job(client, organization_id, headers)

    first = client.post(
        f"/api/v1/generations/{job_id}/reviews",
        headers=headers,
        json={"decision": "revision_requested", "notes": "Keep the patio edge."},
    )
    second = client.post(
        f"/api/v1/generations/{job_id}/reviews",
        headers=headers,
        json={"decision": "approved", "notes": "Customer-ready."},
    )

    assert first.status_code == 201
    assert second.status_code == 201
    response = client.get(f"/api/v1/generations/{job_id}/reviews", headers=headers)
    assert response.status_code == 200
    assert {item["decision"] for item in response.json()} == {
        "revision_requested",
        "approved",
    }
    designs = client.get("/api/v1/design-projects", headers=headers).json()
    assert next(item for item in designs if item["id"] == design_id)["status"] == "accepted"


def test_incomplete_generation_cannot_be_reviewed(client, create_identity):
    organization_id, headers = create_identity("Incomplete Review Landscaping")
    job_id, _ = _job(client, organization_id, headers, status="running")

    response = client.post(
        f"/api/v1/generations/{job_id}/reviews",
        headers=headers,
        json={"decision": "approved"},
    )

    assert response.status_code == 409


def test_generation_review_is_tenant_scoped(client, create_identity):
    first_id, first_headers = create_identity("First Review Landscaping")
    _, second_headers = create_identity("Second Review Landscaping")
    job_id, _ = _job(client, first_id, first_headers)

    response = client.post(
        f"/api/v1/generations/{job_id}/reviews",
        headers=second_headers,
        json={"decision": "approved"},
    )

    assert response.status_code == 404


def test_crew_cannot_create_generation_review(client, create_identity):
    organization_id, admin_headers = create_identity("Crew Review Landscaping")
    _, crew_headers = create_identity("Separate Crew Landscaping", role="crew")
    job_id, _ = _job(client, organization_id, admin_headers)

    response = client.post(
        f"/api/v1/generations/{job_id}/reviews",
        headers=crew_headers,
        json={"decision": "approved"},
    )

    assert response.status_code in {403, 404}
