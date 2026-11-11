from decimal import Decimal


def test_completed_job_creates_one_invoice_and_tracks_payments(client, create_identity):
    _, headers = create_identity("Job billing")
    customer = client.post(
        "/api/v1/customers",
        headers=headers,
        json={"name": "Billing Customer", "email": "billing@example.com"},
    ).json()
    property_record = client.post(
        "/api/v1/properties",
        headers=headers,
        json={"customer_id": customer["id"], "name": "Billing property"},
    ).json()
    design = client.post(
        "/api/v1/design-projects",
        headers=headers,
        json={"property_id": property_record["id"], "name": "Billing design"},
    ).json()
    quote = client.post(
        "/api/v1/quotes",
        headers=headers,
        json={
            "design_project_id": design["id"],
            "title": "Install lawn",
            "items": [
                {
                    "description": "Sod",
                    "category": "material",
                    "quantity": "100",
                    "unit": "sq_ft",
                    "unit_price": "3",
                }
            ],
            "tax_rate": "5",
        },
    ).json()
    for status in ("sent", "approved"):
        response = client.patch(
            f"/api/v1/quotes/{quote['id']}/status",
            headers=headers,
            json={"status": status},
        )
        assert response.status_code == 200
    work_order = client.post(
        f"/api/v1/quotes/{quote['id']}/work-order",
        headers=headers,
        json={
            "scheduled_start": "2027-05-01T16:00:00Z",
            "scheduled_end": "2027-05-01T23:00:00Z",
        },
    ).json()
    completed = client.post(
        f"/api/v1/work-orders/{work_order['id']}/complete",
        headers=headers,
        json={
            "labour_hours": "5",
            "labour_rate": "60",
            "materials": [
                {
                    "description": "Actual sod",
                    "quantity": "110",
                    "unit": "sq_ft",
                    "unit_price": "3",
                }
            ],
            "notes": "Customer walkthrough completed.",
        },
    )
    assert completed.status_code == 200
    assert completed.json()["status"] == "completed"
    assert Decimal(completed.json()["actual_total"]) == Decimal("630.00")

    variance = client.get(
        f"/api/v1/work-orders/{work_order['id']}/variance",
        headers=headers,
    )
    assert variance.status_code == 200
    assert Decimal(variance.json()["actual_total"]) == Decimal("630.00")

    created = client.post(
        f"/api/v1/work-orders/{work_order['id']}/invoice",
        headers=headers,
    )
    assert created.status_code == 201
    invoice = created.json()
    assert invoice["work_order_id"] == work_order["id"]
    assert Decimal(invoice["total"]) == Decimal("661.50")
    assert Decimal(invoice["balance_due"]) == Decimal("661.50")
    assert client.post(
        f"/api/v1/work-orders/{work_order['id']}/invoice",
        headers=headers,
    ).status_code == 409

    partial = client.post(
        f"/api/v1/invoices/{invoice['id']}/payments",
        headers=headers,
        json={"amount": "300", "method": "etransfer", "reference": "DEMO-1"},
    )
    assert partial.status_code == 201
    refreshed = next(
        row
        for row in client.get("/api/v1/invoices", headers=headers).json()
        if row["id"] == invoice["id"]
    )
    assert refreshed["status"] == "sent"
    assert Decimal(refreshed["balance_due"]) == Decimal("361.50")
    final = client.post(
        f"/api/v1/invoices/{invoice['id']}/payments",
        headers=headers,
        json={"amount": "361.50", "method": "card"},
    )
    assert final.status_code == 201
    refreshed = next(
        row
        for row in client.get("/api/v1/invoices", headers=headers).json()
        if row["id"] == invoice["id"]
    )
    assert refreshed["status"] == "paid"
    assert Decimal(refreshed["balance_due"]) == Decimal("0.00")
