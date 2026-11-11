def test_properties_are_scoped_to_organization(client, create_identity):
    first_org, first_headers = create_identity("First Landscaping")
    _, second_headers = create_identity("Second Landscaping")

    response = client.post(
        "/api/v1/properties",
        headers=first_headers,
        json={"name": "Cedar Court", "location": "Burnaby, BC"},
    )
    assert response.status_code == 201

    first_list = client.get("/api/v1/properties", headers=first_headers)
    second_list = client.get("/api/v1/properties", headers=second_headers)

    assert len(first_list.json()) == 1
    assert second_list.json() == []


def test_work_order_cannot_reference_another_organizations_property(client, create_identity):
    _, first_headers = create_identity("First Landscaping")
    _, second_headers = create_identity("Second Landscaping")
    property_response = client.post(
        "/api/v1/properties",
        headers=first_headers,
        json={"name": "Cedar Court"},
    )
    property_id = property_response.json()["id"]

    response = client.post(
        "/api/v1/work-orders",
        headers=second_headers,
        json={
            "property_id": property_id,
            "title": "Mow lawn",
            "description": "Complete weekly lawn maintenance.",
        },
    )

    assert response.status_code == 404
