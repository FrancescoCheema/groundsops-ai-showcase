from io import BytesIO

from PIL import Image

from groundsops.config import get_settings


def _design(client, headers, name="Capture design") -> str:
    customer = client.post("/api/v1/customers", headers=headers, json={"name": "Customer"})
    property_response = client.post(
        "/api/v1/properties",
        headers=headers,
        json={"name": "Backyard", "customer_id": customer.json()["id"]},
    )
    design = client.post(
        "/api/v1/design-projects",
        headers=headers,
        json={"name": name, "property_id": property_response.json()["id"]},
    )
    return design.json()["id"]


def _jpeg_with_exif() -> bytes:
    output = BytesIO()
    image = Image.new("RGB", (64, 48), "green")
    exif = Image.Exif()
    exif[270] = "private capture note"
    image.save(output, "JPEG", exif=exif)
    return output.getvalue()


def test_upload_sanitizes_and_privately_serves_image(client, create_identity):
    organization_id, headers = create_identity("Capture Landscaping")
    design_id = _design(client, headers)

    uploaded = client.post(
        f"/api/v1/design-projects/{design_id}/captures",
        headers=headers,
        files={"file": ("../yard.jpg", _jpeg_with_exif(), "image/jpeg")},
    )

    assert uploaded.status_code == 201
    body = uploaded.json()
    assert body["organization_id"] == organization_id
    assert body["original_filename"] == "yard.jpg"
    assert body["media_type"] == "image/jpeg"
    assert body["width"] == 64
    assert body["height"] == 48
    assert body["status"] == "ready"
    assert "storage_key" not in body

    content = client.get(f"/api/v1/captures/{body['id']}/content", headers=headers)
    assert content.status_code == 200
    assert content.headers["cache-control"] == "private, no-store"
    with Image.open(BytesIO(content.content)) as stored:
        assert not stored.getexif()


def test_rejects_non_image_content(client, create_identity):
    _, headers = create_identity("Invalid Upload Landscaping")
    design_id = _design(client, headers)
    response = client.post(
        f"/api/v1/design-projects/{design_id}/captures",
        headers=headers,
        files={"file": ("yard.jpg", b"not an image", "image/jpeg")},
    )
    assert response.status_code == 415


def test_rejects_oversized_upload(client, create_identity):
    _, headers = create_identity("Oversized Upload Landscaping")
    design_id = _design(client, headers)
    settings = get_settings()
    previous_limit = settings.image_max_bytes
    settings.image_max_bytes = 8
    try:
        response = client.post(
            f"/api/v1/design-projects/{design_id}/captures",
            headers=headers,
            files={"file": ("yard.jpg", _jpeg_with_exif(), "image/jpeg")},
        )
    finally:
        settings.image_max_bytes = previous_limit
    assert response.status_code == 413


def test_cannot_upload_to_another_tenants_design(client, create_identity):
    _, first_headers = create_identity("Owned Design Landscaping")
    _, second_headers = create_identity("Outside Design Landscaping")
    design_id = _design(client, first_headers)
    response = client.post(
        f"/api/v1/design-projects/{design_id}/captures",
        headers=second_headers,
        files={"file": ("yard.jpg", _jpeg_with_exif(), "image/jpeg")},
    )
    assert response.status_code == 404


def test_capture_is_tenant_isolated(client, create_identity):
    _, first_headers = create_identity("First Capture Landscaping")
    _, second_headers = create_identity("Second Capture Landscaping")
    design_id = _design(client, first_headers)
    uploaded = client.post(
        f"/api/v1/design-projects/{design_id}/captures",
        headers=first_headers,
        files={"file": ("yard.jpg", _jpeg_with_exif(), "image/jpeg")},
    )
    capture_id = uploaded.json()["id"]

    assert client.get(f"/api/v1/captures/{capture_id}", headers=second_headers).status_code == 404
    assert (
        client.get(f"/api/v1/captures/{capture_id}/content", headers=second_headers).status_code
        == 404
    )
    assert (
        client.delete(f"/api/v1/captures/{capture_id}", headers=second_headers).status_code == 404
    )


def test_delete_removes_content_and_hides_metadata(client, create_identity):
    _, headers = create_identity("Delete Capture Landscaping")
    design_id = _design(client, headers)
    uploaded = client.post(
        f"/api/v1/design-projects/{design_id}/captures",
        headers=headers,
        files={"file": ("yard.jpg", _jpeg_with_exif(), "image/jpeg")},
    )
    capture_id = uploaded.json()["id"]

    assert client.delete(f"/api/v1/captures/{capture_id}", headers=headers).status_code == 204
    assert client.get(f"/api/v1/captures/{capture_id}", headers=headers).status_code == 404
    listed = client.get(f"/api/v1/design-projects/{design_id}/captures", headers=headers)
    assert listed.status_code == 200
    assert listed.json() == []
