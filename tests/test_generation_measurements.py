from io import BytesIO

from PIL import Image, ImageDraw

from groundsops.config import get_settings


def _png(color: str = "white") -> bytes:
    stream = BytesIO()
    Image.new("RGB", (32, 32), color).save(stream, format="PNG")
    return stream.getvalue()


def _mask() -> bytes:
    stream = BytesIO()
    image = Image.new("L", (32, 32), "black")
    ImageDraw.Draw(image).rectangle((4, 4, 20, 20), fill="white")
    image.save(stream, format="PNG")
    return stream.getvalue()


def test_generation_persists_calibrated_mask_measurement(
    client, create_identity, monkeypatch
):
    _, headers = create_identity("Measured Landscaping")
    customer = client.post(
        "/api/v1/customers", headers=headers, json={"name": "Measured Customer"}
    ).json()
    property_record = client.post(
        "/api/v1/properties",
        headers=headers,
        json={"name": "Measured Property", "customer_id": customer["id"]},
    ).json()
    design = client.post(
        "/api/v1/design-projects",
        headers=headers,
        json={"name": "Measured Design", "property_id": property_record["id"]},
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

    response = client.post(
        f"/api/v1/design-projects/{design['id']}/generations",
        headers=headers,
        data={
            "capture_id": capture["id"],
            "prompt": "Replace the selected lawn with healthy green sod.",
            "selected_pixel_count": "289",
            "total_pixel_count": "1024",
            "calibration_pixel_length": "16",
            "calibration_real_length": "4",
            "calibration_unit": "ft",
            "estimated_area": "18.0625",
            "estimated_perimeter": "17",
            "measurement_method": "camera_reference",
        },
        files={"mask": ("mask.png", _mask(), "image/png")},
    )

    assert response.status_code == 202
    result = response.json()
    assert result["measurement_method"] == "camera_reference"
    assert result["selected_pixel_count"] == 289
    assert result["calibration_unit"] == "ft"
    assert result["estimated_area"] == "18.0625"
    assert result["estimated_perimeter"] == "17.0000"
    assert result["measurement_confidence"] == "photo_estimate"
