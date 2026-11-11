from datetime import UTC, datetime
from decimal import Decimal

from groundsops.db import SessionLocal
from groundsops.models import GenerationEvaluation, GenerationJob, GenerationStatus


def _create_design(client, headers):
    customer = client.post(
        "/api/v1/customers", headers=headers, json={"name": "Metrics Customer"}
    ).json()
    property_record = client.post(
        "/api/v1/properties",
        headers=headers,
        json={"name": "Metrics Property", "customer_id": customer["id"]},
    ).json()
    return client.post(
        "/api/v1/design-projects",
        headers=headers,
        json={"name": "Metrics Design", "property_id": property_record["id"]},
    ).json()


def _seed_evaluated_job(client, organization_id, headers, *, passed):
    design = _create_design(client, headers)
    user = client.get("/api/v1/auth/me", headers=headers).json()
    with SessionLocal() as db:
        job = GenerationJob(
            organization_id=organization_id,
            design_project_id=design["id"],
            capture_id="capture-for-metrics",
            requested_by_user_id=user["id"],
            prompt="Replace the selected lawn with charcoal concrete pavers.",
            provider="replicate",
            model_version="landscape-model-v1",
            status=GenerationStatus.SUCCEEDED.value,
            mask_storage_key=f"metrics/{organization_id}/{passed}/mask.png",
            output_storage_key=f"metrics/{organization_id}/{passed}/output.png",
            output_media_type="image/png",
            latency_ms=2400,
            estimated_cost_usd=Decimal("0.1250"),
            completed_at=datetime.now(UTC),
        )
        db.add(job)
        db.flush()
        evaluation = GenerationEvaluation(
            organization_id=organization_id,
            generation_job_id=job.id,
            evaluator_version="pixel-change-v1",
            dimensions_match=True,
            masked_change_ratio=Decimal("0.850000"),
            protected_change_ratio=Decimal("0.010000" if passed else "0.500000"),
            masked_change_threshold=Decimal("0.200000"),
            protected_change_threshold=Decimal("0.080000"),
            pixel_change_threshold=Decimal("0.050000"),
            passed=passed,
            failure_reasons=[] if passed else ["excessive_protected_change"],
            evaluation_latency_ms=12,
        )
        db.add(evaluation)
        db.commit()
        return job.id


def test_generation_metrics_aggregate_quality_results(client, create_identity):
    organization_id, headers = create_identity("Metrics Landscaping")
    _seed_evaluated_job(client, organization_id, headers, passed=True)
    _seed_evaluated_job(client, organization_id, headers, passed=False)

    response = client.get("/api/v1/generation-metrics", headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert body["total_generations"] == 2
    assert body["evaluated_generations"] == 2
    assert body["passed_generations"] == 1
    assert body["failed_evaluations"] == 1
    assert body["pass_rate"] == 50.0
    assert body["average_generation_latency_ms"] == 2400.0
    assert body["average_evaluation_latency_ms"] == 12.0
    assert body["estimated_cost_usd"] == "0.2500"
    assert body["failure_reasons"] == [
        {"reason": "excessive_protected_change", "count": 1}
    ]
    assert len(body["review_queue"]) == 1
    assert body["models"][0]["pass_rate"] == 50.0


def test_generation_metrics_require_management_role(client, create_identity):
    _, headers = create_identity("Crew Metrics Landscaping", role="crew")

    response = client.get("/api/v1/generation-metrics", headers=headers)

    assert response.status_code == 403


def test_generation_metrics_are_tenant_scoped(client, create_identity):
    first_id, first_headers = create_identity("First Metrics Landscaping")
    second_id, second_headers = create_identity("Second Metrics Landscaping")
    _seed_evaluated_job(client, first_id, first_headers, passed=False)

    response = client.get("/api/v1/generation-metrics", headers=second_headers)

    assert response.status_code == 200
    assert response.json()["total_generations"] == 0


def test_completed_human_review_removes_failed_job_from_queue(client, create_identity):
    organization_id, headers = create_identity("Reviewed Metrics Landscaping")
    job_id = _seed_evaluated_job(
        client, organization_id, headers, passed=False
    )

    review = client.post(
        f"/api/v1/generations/{job_id}/reviews",
        headers=headers,
        json={"decision": "approved", "notes": "Accepted after manual inspection."},
    )
    metrics = client.get("/api/v1/generation-metrics", headers=headers)

    assert review.status_code == 201
    assert metrics.status_code == 200
    assert metrics.json()["failed_evaluations"] == 1
    assert metrics.json()["review_queue"] == []
