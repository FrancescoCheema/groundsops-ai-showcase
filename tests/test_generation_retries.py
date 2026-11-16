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
                      prompt_override=None, mask_override=None):
        calls.append({"image": image_override, "prompt": prompt_override, "mask": mask_override})
        full_passes = [call for call in calls if call["mask"] is None]
        # The whole first attempt (including its bare-ground repair) stays gravel-grey and
        # is rejected; the retry returns grass.
        image = _png(Image.new("RGB", (64, 64), (128, 128, 128))) if len(full_passes) == 1 \
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
    full_passes = [call for call in calls if call["mask"] is None]
    assert len(full_passes) == 2
    assert full_passes[1]["image"] == full_passes[0]["image"], (
        "retry must start from the original photo"
    )
    assert "Thick, uniformly green grass" in full_passes[1]["prompt"]

    output = client.get(f"/api/v1/generations/{job['id']}/output", headers=headers)
    result = Image.open(BytesIO(output.content)).convert("RGB")
    assert result.getpixel((2, 2)) == (120, 90, 60)
    assert result.getpixel((32, 32)) != (120, 90, 60)


def test_generation_mask_is_served_only_to_its_company(client, create_identity, monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "inference_provider", "mock")
    _, headers = create_identity("Mask Owner")
    _, other_headers = create_identity("Mask Stranger")
    customer = client.post(
        "/api/v1/customers", headers=headers, json={"name": "Mask Customer"}
    ).json()
    prop = client.post("/api/v1/properties", headers=headers,
                       json={"name": "Yard", "customer_id": customer["id"]}).json()
    design = client.post("/api/v1/design-projects", headers=headers,
                         json={"name": "Mask Design", "property_id": prop["id"]}).json()
    capture = client.post(
        f"/api/v1/design-projects/{design['id']}/captures", headers=headers,
        files={"file": ("site.png", _png(Image.new("RGB", (64, 64), (120, 90, 60))), "image/png")},
    ).json()
    mask = Image.new("L", (64, 64), 0)
    ImageDraw.Draw(mask).rectangle((16, 16, 47, 47), fill=255)
    job = client.post(
        f"/api/v1/design-projects/{design['id']}/generations", headers=headers,
        data={"capture_id": capture["id"], "prompt": "Lay fresh sod"},
        files={"mask": ("mask.png", _png(mask), "image/png")},
    ).json()

    own = client.get(f"/api/v1/generations/{job['id']}/mask", headers=headers)
    other = client.get(f"/api/v1/generations/{job['id']}/mask", headers=other_headers)

    assert own.status_code == 200
    assert own.headers["content-type"] == "image/png"
    assert Image.open(BytesIO(own.content)).convert("L").getpixel((32, 32)) == 255
    assert other.status_code == 404


def test_bare_ground_left_inside_a_lawn_is_repainted(client, create_identity, monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "inference_provider", "mock")
    monkeypatch.setattr(settings, "inference_max_attempts", 1)
    _, headers = create_identity("Island Landscaping")
    customer = client.post("/api/v1/customers", headers=headers, json={"name": "Island"}).json()
    property_record = client.post(
        "/api/v1/properties",
        headers=headers,
        json={"name": "Island Yard", "customer_id": customer["id"]},
    ).json()
    design = client.post(
        "/api/v1/design-projects",
        headers=headers,
        json={"name": "Island Design", "property_id": property_record["id"]},
    ).json()
    soil = (120, 90, 60)
    capture = client.post(
        f"/api/v1/design-projects/{design['id']}/captures",
        headers=headers,
        files={"file": ("site.png", _png(Image.new("RGB", (96, 96), soil)), "image/png")},
    ).json()
    mask = Image.new("L", (96, 96), 0)
    ImageDraw.Draw(mask).rectangle((8, 8, 87, 87), fill=255)

    calls: list[dict] = []

    def fake_provider(job, *, image_override=None, image_media_type_override=None,
                      prompt_override=None, mask_override=None):
        calls.append({"image": image_override, "mask": mask_override})
        if mask_override is None:
            # First pass: an island of lawn in the middle, soil left around it.
            island = Image.new("RGB", (96, 96), soil)
            island.paste(Image.open(BytesIO(_grass((40, 40)))).convert("RGB"), (28, 28))
            image = _png(island)
        else:
            image = _grass((96, 96))
        return ImageGenerationResult(
            image=image, media_type="image/png", prediction_id=f"call-{len(calls)}",
            latency_ms=10, estimated_cost_usd=Decimal("0.05"),
        )

    monkeypatch.setattr(inference, "_run_provider", fake_provider)
    response = client.post(
        f"/api/v1/design-projects/{design['id']}/generations",
        headers=headers,
        data={"capture_id": capture["id"], "prompt": "New sod lawn"},
        files={"mask": ("mask.png", _png(mask), "image/png")},
    )
    job = client.get(f"/api/v1/generations/{response.json()['id']}", headers=headers).json()

    assert job["status"] == "succeeded", job
    assert len(calls) == 2 and calls[1]["mask"] is not None, "bare ground gets a second pass"
    assert calls[1]["image"] is not None, "the repair starts from the first result"
    assert job["estimated_cost_usd"] == "0.1000"
    output = client.get(f"/api/v1/generations/{job['id']}/output", headers=headers)
    result = Image.open(BytesIO(output.content)).convert("RGB")
    corner_red, corner_green, _ = result.getpixel((14, 14))
    assert corner_green > corner_red, "the soil band inside the selection is now lawn"
    assert result.getpixel((2, 2)) == soil, "outside the selection never changes"
