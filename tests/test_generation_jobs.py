from io import BytesIO

from PIL import Image


def _png() -> bytes:
    stream = BytesIO()
    Image.new("RGB", (32, 32), "white").save(stream, format="PNG")
    return stream.getvalue()


def test_generation_is_disabled_without_provider_configuration(client, create_identity):
    _, headers = create_identity("Generation Landscaping")
    customer = client.post(
        "/api/v1/customers", headers=headers, json={"name": "Generation Customer"}
    ).json()
    property_record = client.post(
        "/api/v1/properties",
        headers=headers,
        json={"name": "Generation Property", "customer_id": customer["id"]},
    ).json()
    design = client.post(
        "/api/v1/design-projects",
        headers=headers,
        json={"name": "Generation Design", "property_id": property_record["id"]},
    ).json()
    capture = client.post(
        f"/api/v1/design-projects/{design['id']}/captures",
        headers=headers,
        files={"file": ("site.png", _png(), "image/png")},
    ).json()

    response = client.post(
        f"/api/v1/design-projects/{design['id']}/generations",
        headers=headers,
        data={
            "capture_id": capture["id"],
            "prompt": "Replace the selected lawn with charcoal concrete pavers.",
        },
        files={"mask": ("mask.png", _png(), "image/png")},
    )

    assert response.status_code == 503
    assert response.json() == {"detail": "Image generation is disabled"}
