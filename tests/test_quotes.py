from decimal import Decimal


def _design(client, headers, name="Quote Landscaping"):
    customer = client.post("/api/v1/customers", headers=headers, json={"name": name}).json()
    property_record = client.post(
        "/api/v1/properties",
        headers=headers,
        json={"customer_id": customer["id"], "name": "Test property"},
    ).json()
    return client.post(
        "/api/v1/design-projects",
        headers=headers,
        json={"property_id": property_record["id"], "name": "Approved concept"},
    ).json()


def test_quote_totals_are_calculated_by_server(client, create_identity):
    _, headers = create_identity("Quote totals")
    design = _design(client, headers)
    response = client.post(
        "/api/v1/quotes",
        headers=headers,
        json={
            "design_project_id": design["id"],
            "title": "Backyard installation",
            "items": [
                {
                    "description": "Sod",
                    "category": "material",
                    "quantity": "100",
                    "unit": "sq_ft",
                    "unit_price": "2.50",
                },
                {
                    "description": "Installation",
                    "category": "labour",
                    "quantity": "8",
                    "unit": "hour",
                    "unit_price": "50",
                },
            ],
            "markup_rate": "10",
            "discount_amount": "25",
            "tax_rate": "5",
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert Decimal(body["subtotal"]) == Decimal("650.00")
    assert Decimal(body["markup_amount"]) == Decimal("65.00")
    assert Decimal(body["tax_amount"]) == Decimal("34.50")
    assert Decimal(body["total"]) == Decimal("724.50")
    assert body["number"].startswith("Q-")
    assert len(body["items"]) == 2


def test_quote_tenant_isolation_and_status_transitions(client, create_identity):
    _, first = create_identity("First quote org")
    _, second = create_identity("Second quote org")
    design = _design(client, first)
    created = client.post(
        "/api/v1/quotes",
        headers=first,
        json={
            "design_project_id": design["id"],
            "title": "Private quote",
            "items": [
                {
                    "description": "Labour",
                    "category": "labour",
                    "quantity": 1,
                    "unit": "hour",
                    "unit_price": 100,
                }
            ],
        },
    ).json()
    assert client.get(f"/api/v1/quotes/{created['id']}", headers=second).status_code == 404
    assert (
        client.patch(
            f"/api/v1/quotes/{created['id']}/status", headers=first, json={"status": "approved"}
        ).status_code
        == 409
    )
    sent = client.patch(
        f"/api/v1/quotes/{created['id']}/status", headers=first, json={"status": "sent"}
    )
    assert sent.status_code == 200
    approved = client.patch(
        f"/api/v1/quotes/{created['id']}/status", headers=first, json={"status": "approved"}
    )
    assert approved.status_code == 200
    assert approved.json()["status"] == "approved"


def test_approved_quote_converts_to_one_scheduled_work_order(client, create_identity):
    _, headers = create_identity("Quote scheduling")
    design = _design(client, headers)
    quote = client.post(
        "/api/v1/quotes",
        headers=headers,
        json={
            "design_project_id": design["id"],
            "title": "Install front lawn",
            "items": [
                {
                    "description": "Premium sod",
                    "category": "material",
                    "quantity": "450",
                    "unit": "sq_ft",
                    "unit_price": "2.25",
                },
                {
                    "description": "Installation labour",
                    "category": "labour",
                    "quantity": "12",
                    "unit": "hour",
                    "unit_price": "55",
                },
            ],
            "tax_rate": "5",
        },
    ).json()
    not_approved = client.post(
        f"/api/v1/quotes/{quote['id']}/work-order",
        headers=headers,
        json={
            "scheduled_start": "2027-04-15T16:00:00Z",
            "scheduled_end": "2027-04-15T23:00:00Z",
        },
    )
    assert not_approved.status_code == 409
    client.patch(
        f"/api/v1/quotes/{quote['id']}/status",
        headers=headers,
        json={"status": "sent"},
    )
    client.patch(
        f"/api/v1/quotes/{quote['id']}/status",
        headers=headers,
        json={"status": "approved"},
    )

    created = client.post(
        f"/api/v1/quotes/{quote['id']}/work-order",
        headers=headers,
        json={
            "scheduled_start": "2027-04-15T16:00:00Z",
            "scheduled_end": "2027-04-15T23:00:00Z",
            "priority": "high",
            "customer_instructions": "Use the side gate and protect the driveway.",
        },
    )
    assert created.status_code == 201
    body = created.json()
    assert body["status"] == "scheduled"
    assert body["quote_id"] == quote["id"]
    assert body["design_project_id"] == design["id"]
    assert body["property_id"] == design["property_id"]
    assert body["priority"] == "high"
    assert body["quoted_total"] == quote["total"]
    assert body["quote_currency"] == "CAD"
    assert body["material_checklist"] == [
        {
            "description": "Premium sod",
            "category": "material",
            "quantity": "450.00",
            "unit": "sq_ft",
        }
    ]
    duplicate = client.post(
        f"/api/v1/quotes/{quote['id']}/work-order",
        headers=headers,
        json={
            "scheduled_start": "2027-04-16T16:00:00Z",
            "scheduled_end": "2027-04-16T23:00:00Z",
        },
    )
    assert duplicate.status_code == 409


def test_quote_work_order_conversion_is_tenant_scoped(client, create_identity):
    _, first = create_identity("Quote owner")
    _, second = create_identity("Other quote org")
    design = _design(client, first)
    quote = client.post(
        "/api/v1/quotes",
        headers=first,
        json={
            "design_project_id": design["id"],
            "title": "Private scheduled installation",
            "items": [
                {
                    "description": "Pavers",
                    "category": "material",
                    "quantity": 25,
                    "unit": "sq_ft",
                    "unit_price": 8,
                }
            ],
        },
    ).json()
    response = client.post(
        f"/api/v1/quotes/{quote['id']}/work-order",
        headers=second,
        json={
            "scheduled_start": "2027-04-15T16:00:00Z",
            "scheduled_end": "2027-04-15T23:00:00Z",
        },
    )
    assert response.status_code == 404
