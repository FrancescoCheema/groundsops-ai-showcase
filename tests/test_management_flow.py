def test_customer_property_design_and_quote_flow(client, create_identity):
    organization_id, auth_headers = create_identity("Green Horizon Landscaping")

    user_response = client.post(
        "/api/v1/users",
        headers=auth_headers,
        json={
            "email": "manager@example.com",
            "display_name": "Operations Manager",
            "role": "manager",
        },
    )
    assert user_response.status_code == 201
    assert user_response.json()["role"] == "manager"

    customer_response = client.post(
        "/api/v1/customers",
        headers=auth_headers,
        json={"name": "Avery Customer", "email": "avery@example.com"},
    )
    assert customer_response.status_code == 201
    customer_id = customer_response.json()["id"]

    property_response = client.post(
        "/api/v1/properties",
        headers=auth_headers,
        json={
            "customer_id": customer_id,
            "name": "Cedar Court",
            "location": "Burnaby, BC",
        },
    )
    assert property_response.status_code == 201
    property_id = property_response.json()["id"]

    design_response = client.post(
        "/api/v1/design-projects",
        headers=auth_headers,
        json={
            "property_id": property_id,
            "name": "Backyard paver concept",
            "goal": "Replace the worn lawn with a paver seating area.",
        },
    )
    assert design_response.status_code == 201
    assert design_response.json()["status"] == "draft"
    design_id = design_response.json()["id"]

    quote_response = client.post(
        "/api/v1/quotes",
        headers=auth_headers,
        json={
            "design_project_id": design_id,
            "title": "Preliminary material estimate",
            "items": [
                {
                    "description": "Concrete pavers",
                    "category": "material",
                    "quantity": "10",
                    "unit": "sq_ft",
                    "unit_price": "125.05",
                }
            ],
            "currency": "cad",
            "assumptions": "Customer-supplied dimensions; delivery and tax excluded.",
        },
    )
    assert quote_response.status_code == 201
    assert quote_response.json()["subtotal"] == "1250.50"
    assert quote_response.json()["total"] == "1250.50"
    assert quote_response.json()["currency"] == "CAD"
    assert quote_response.json()["status"] == "draft"


def test_material_and_variant_flow(client, create_identity):
    _, auth_headers = create_identity("Green Horizon Landscaping")
    material_response = client.post(
        "/api/v1/materials",
        headers=auth_headers,
        json={
            "name": "Concrete paver",
            "category": "paver",
            "description": "Controlled demonstration material.",
        },
    )
    assert material_response.status_code == 201

    variant_response = client.post(
        "/api/v1/material-variants",
        headers=auth_headers,
        json={
            "material_id": material_response.json()["id"],
            "name": "Charcoal rectangle",
            "colour": "charcoal",
            "unit": "square_metre",
            "default_waste_percent": "12.50",
        },
    )
    assert variant_response.status_code == 201
    assert variant_response.json()["default_waste_percent"] == "12.50"


def test_cross_organization_references_are_rejected(client, create_identity):
    _, first_headers = create_identity("First Landscaping")
    _, second_headers = create_identity("Second Landscaping")

    customer_response = client.post(
        "/api/v1/customers",
        headers=first_headers,
        json={"name": "First Customer"},
    )
    material_response = client.post(
        "/api/v1/materials",
        headers=first_headers,
        json={"name": "Premium sod", "category": "grass"},
    )

    property_response = client.post(
        "/api/v1/properties",
        headers=second_headers,
        json={
            "customer_id": customer_response.json()["id"],
            "name": "Unauthorized property",
        },
    )
    variant_response = client.post(
        "/api/v1/material-variants",
        headers=second_headers,
        json={
            "material_id": material_response.json()["id"],
            "name": "Unauthorized variant",
            "unit": "square_metre",
        },
    )

    assert property_response.status_code == 404
    assert variant_response.status_code == 404


def test_duplicate_user_in_same_organization_is_rejected(client, create_identity):
    _, auth_headers = create_identity("Green Horizon Landscaping")
    payload = {
        "email": "MANAGER@example.com",
        "display_name": "Operations Manager",
        "role": "manager",
    }

    first = client.post("/api/v1/users", headers=auth_headers, json=payload)
    second = client.post("/api/v1/users", headers=auth_headers, json=payload)

    assert first.status_code == 201
    assert second.status_code == 409
