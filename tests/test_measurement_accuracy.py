from io import BytesIO

from PIL import Image, ImageDraw

from groundsops.config import get_settings


def _png() -> bytes:
    stream = BytesIO()
    Image.new("RGB", (32, 32), "white").save(stream, format="PNG")
    return stream.getvalue()


def _mask() -> bytes:
    stream = BytesIO()
    image = Image.new("L", (32, 32), "black")
    ImageDraw.Draw(image).rectangle((4, 4, 20, 20), fill="white")
    image.save(stream, format="PNG")
    return stream.getvalue()


def _generation(client, headers, monkeypatch, *, area: str | None, method="reference_object"):
    customer = client.post("/api/v1/customers", headers=headers, json={"name": "Tape Customer"})
    site = client.post(
        "/api/v1/properties",
        headers=headers,
        json={"name": "Tape Property", "customer_id": customer.json()["id"]},
    ).json()
    design = client.post(
        "/api/v1/design-projects",
        headers=headers,
        json={"name": "Tape Design", "property_id": site["id"]},
    ).json()
    capture = client.post(
        f"/api/v1/design-projects/{design['id']}/captures",
        headers=headers,
        files={"file": ("site.png", _png(), "image/png")},
    ).json()
    settings = get_settings()
    monkeypatch.setattr(settings, "inference_provider", "replicate")
    monkeypatch.setattr(settings, "replicate_model_version", "test-model")
    monkeypatch.setattr("groundsops.api.process_generation_job", lambda _job_id: None)
    data = {"capture_id": capture["id"], "prompt": "Replace the lawn with new sod."}
    if area:
        data |= {
            "selected_pixel_count": "289",
            "total_pixel_count": "1024",
            "calibration_pixel_length": "12",
            "calibration_real_length": "0.9167",
            "calibration_unit": "ft",
            "calibration_reference": "Letter paper (8.5 × 11 in)",
            "estimated_area": area,
            "estimated_perimeter": "66",
            "measurement_method": method,
        }
    response = client.post(
        f"/api/v1/design-projects/{design['id']}/generations",
        headers=headers,
        data=data,
        files={"mask": ("mask.png", _mask(), "image/png")},
    )
    assert response.status_code == 202
    return response.json()


def test_site_measurements_report_how_far_the_photo_measurement_was_off(
    client, create_identity, monkeypatch
):
    _, headers = create_identity("Tape Landscaping")
    first = _generation(client, headers, monkeypatch, area="208")
    second = _generation(client, headers, monkeypatch, area="180", method="reference_line")

    recorded = client.put(
        f"/api/v1/generations/{first['id']}/site-measurement",
        headers=headers,
        json={"area": "200", "perimeter": "64", "notes": " Tape, two people "},
    )
    assert recorded.status_code == 200
    body = recorded.json()
    assert body["area_error_percent"] == 4.0  # app said 208, tape said 200
    assert body["perimeter_error_percent"] == 3.13
    assert body["notes"] == "Tape, two people"
    assert body["unit"] == "ft"

    client.put(
        f"/api/v1/generations/{second['id']}/site-measurement",
        headers=headers,
        json={"area": "240"},
    )

    report = client.get("/api/v1/measurement-accuracy", headers=headers).json()
    summary = report["summary"]
    assert summary["count"] == 2
    assert summary["within_5_percent"] == 1  # 4% yes, -25% no
    assert summary["median_abs_error_percent"] == 14.5
    methods = {item["method"]: item for item in summary["by_method"]}
    assert methods["Known object"]["median_abs_error_percent"] == 4.0
    assert methods["Reference line"]["median_abs_error_percent"] == 25.0
    references = {check["reference"] for check in report["checks"]}
    assert references == {"Letter paper (8.5 × 11 in)", None}

    cleared = client.delete(f"/api/v1/generations/{second['id']}/site-measurement", headers=headers)
    assert cleared.status_code == 204
    assert client.get("/api/v1/measurement-accuracy", headers=headers).json()["summary"][
        "count"
    ] == 1


def test_site_measurements_stay_within_the_company_and_need_a_photo_measurement(
    client, create_identity, monkeypatch
):
    _, admin_headers = create_identity("Crew Tape Landscaping")
    measured = _generation(client, admin_headers, monkeypatch, area="150")
    unmeasured = _generation(client, admin_headers, monkeypatch, area=None)
    _, crew_headers = create_identity("Crew Tape Landscaping Two", role="crew")

    _, other_headers = create_identity("Other Tape Landscaping")
    assert client.put(
        f"/api/v1/generations/{measured['id']}/site-measurement",
        headers=other_headers,
        json={"area": "150"},
    ).status_code == 404
    assert client.put(
        f"/api/v1/generations/{unmeasured['id']}/site-measurement",
        headers=admin_headers,
        json={"area": "150"},
    ).status_code == 409
    # The accuracy report is for managers; crew only record measurements.
    assert client.get("/api/v1/measurement-accuracy", headers=crew_headers).status_code == 403
