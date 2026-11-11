from decimal import Decimal
from io import BytesIO

from PIL import Image, ImageDraw

import groundsops.inference as inference
from groundsops.config import get_settings
from groundsops.inference_providers import ImageGenerationResult


def _png(image: Image.Image) -> bytes:
    stream = BytesIO()
    image.save(stream, format="PNG")
    return stream.getvalue()


def _grass(size: tuple[int, int]) -> bytes:
    image = Image.new("RGB", size)
    pixels = image.load()
    for x in range(size[0]):
        for y in range(size[1]):
            pixels[x, y] = (40 + (x * 7 + y * 3) % 30, 150 + (x * 5 + y * 11) % 60, 45)
    return _png(image)


def test_retries_start_from_the_original_photo_and_keep_outside_pixels(
    client, create_identity, monkeypatch
):
    settings = get_settings()
    monkeypatch.setattr(settings, "inference_provider", "mock")
    monkeypatch.setattr(settings, "inference_max_attempts", 2)
    _, headers = create_identity("Retry Landscaping")
    customer = client.post("/api/v1/customers", headers=headers, json={"name": "Retry"}).json()
    property_record = client.post(
        "/api/v1/properties",
        headers=headers,
        json={"name": "Retry Yard", "customer_id": customer["id"]},
    ).json()
    design = client.post(
        "/api/v1/design-projects",
        headers=headers,
        json={"name": "Retry Design", "property_id": property_record["id"]},
    ).json()
    source = Image.new("RGB", (64, 64), (120, 90, 60))
    capture = client.post(
        f"/api/v1/design-projects/{design['id']}/captures",
        headers=headers,
        files={"file": ("site.png", _png(source), "image/png")},
    ).json()
    mask = Image.new("L", (64, 64), 0)
    ImageDraw.Draw(mask).rectangle((16, 16, 47, 47), fill=255)

    calls: list[dict] = []

    def fake_provider(job, *, image_override=None, image_media_type_override=None,
                      prompt_override=None):
        calls.append({"image": image_override, "prompt": prompt_override})
        # First attempt returns gravel-grey (rejected), the retry returns grass.
        image = _png(Image.new("RGB", (64, 64), (128, 128, 128))) if len(calls) == 1 \
            else _grass((64, 64))
        return ImageGenerationResult(
            image=image,
            media_type="image/png",
            prediction_id=f"attempt-{len(calls)}",
            latency_ms=10,
            estimated_cost_usd=Decimal("0.05"),
        )

    monkeypatch.setattr(inference, "_run_provider", fake_provider)

    response = client.post(
        f"/api/v1/design-projects/{design['id']}/generations",
        headers=headers,
        data={"capture_id": capture["id"], "prompt": "Lay fresh sod"},
        files={"mask": ("mask.png", _png(mask), "image/png")},
    )
    assert response.status_code in {200, 201, 202}, response.text
    job = client.get(f"/api/v1/generations/{response.json()['id']}", headers=headers).json()

    assert job["status"] == "succeeded", job
    assert len(calls) == 2
    assert calls[1]["image"] == calls[0]["image"], "retry must start from the original photo"
    assert "Thick, uniformly green grass" in calls[1]["prompt"]

    output = client.get(f"/api/v1/generations/{job['id']}/output", headers=headers)
    result = Image.open(BytesIO(output.content)).convert("RGB")
    assert result.getpixel((2, 2)) == (120, 90, 60)
    assert result.getpixel((32, 32)) != (120, 90, 60)
