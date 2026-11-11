from io import BytesIO

from PIL import Image


def _customer(client, headers, name="Invoice Customer") -> str:
    response = client.post("/api/v1/customers", headers=headers, json={"name": name})
    assert response.status_code == 201
    return response.json()["id"]


def _property(client, headers, customer_id: str) -> str:
    response = client.post(
        "/api/v1/properties",
        headers=headers,
        json={"name": "Cedar Court", "customer_id": customer_id},
    )
    assert response.status_code == 201
    return response.json()["id"]


def _logo() -> bytes:
    output = BytesIO()
    Image.new("RGB", (80, 40), "green").save(output, "PNG")
    return output.getvalue()


def test_invoice_is_saved_and_tenant_scoped(client, create_identity):
    organization_id, headers = create_identity("Invoice Landscaping")
    _, outside_headers = create_identity("Outside Invoice Landscaping")
    customer_id = _customer(client, headers)

    created = client.post(
        "/api/v1/invoices",
        headers=headers,
        json={
            "customer_id": customer_id,
            "items": [
                {
                    "description": "Paver installation",
                    "quantity": "2.00",
                    "rate": "125.50",
                },
                {
                    "description": "Delivery",
                    "quantity": "1.00",
                    "rate": "50.00",
                },
            ],
            "currency": "cad",
        },
    )

    assert created.status_code == 201
    assert created.json()["organization_id"] == organization_id
    assert created.json()["subtotal"] == "301.00"
    assert len(created.json()["items"]) == 2
    assert created.json()["status"] == "draft"
    assert len(client.get("/api/v1/invoices", headers=headers).json()) == 1
    assert client.get("/api/v1/invoices", headers=outside_headers).json() == []

    updated = client.put(
        f"/api/v1/invoices/{created.json()['id']}",
        headers=headers,
        json={
            "customer_id": customer_id,
            "items": [{"description": "Updated work", "quantity": "3", "rate": "100"}],
            "currency": "CAD",
            "status": "sent",
        },
    )
    assert updated.status_code == 200
    assert updated.json()["subtotal"] == "300.00"
    assert updated.json()["status"] == "sent"

    assert (
        client.delete(f"/api/v1/invoices/{created.json()['id']}", headers=headers).status_code
        == 204
    )
    assert client.get("/api/v1/invoices", headers=headers).json() == []


def test_company_logo_is_saved_and_private(client, create_identity):
    _, headers = create_identity("Branded Landscaping")
    _, outside_headers = create_identity("Outside Branding")

    uploaded = client.post(
        "/api/v1/organization/logo",
        headers=headers,
        files={"file": ("logo.png", _logo(), "image/png")},
    )

    assert uploaded.status_code == 200
    assert uploaded.json()["logo_media_type"] == "image/png"
    content = client.get("/api/v1/organization/logo/content", headers=headers)
    assert content.status_code == 200
    assert content.headers["content-type"] == "image/png"
    assert (
        client.get("/api/v1/organization/logo/content", headers=outside_headers).status_code == 404
    )


def test_clock_in_and_clock_out_are_persistent(client, create_identity):
    _, headers = create_identity("Timesheet Landscaping")
    customer_id = _customer(client, headers, "Timesheet Customer")
    property_id = _property(client, headers, customer_id)

    started = client.post(
        "/api/v1/timesheets/clock-in",
        headers=headers,
        json={"property_id": property_id},
    )
    assert started.status_code == 201
    assert started.json()["status"] == "running"
    assert started.json()["property_name"] == "Cedar Court"

    duplicate = client.post("/api/v1/timesheets/clock-in", headers=headers, json={})
    assert duplicate.status_code == 409

    ended = client.post(f"/api/v1/timesheets/{started.json()['id']}/clock-out", headers=headers)
    assert ended.status_code == 200
    assert ended.json()["status"] == "submitted"
    assert ended.json()["ended_at"] is not None
    assert len(client.get("/api/v1/timesheets", headers=headers).json()) == 1
