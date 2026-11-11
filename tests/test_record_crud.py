def test_customer_property_and_design_can_be_updated_and_deleted(client, create_identity):
    _, headers = create_identity("CRUD Landscaping")
    customer = client.post(
        "/api/v1/customers", headers=headers, json={"name": "Original Customer"}
    ).json()
    updated_customer = client.put(
        f"/api/v1/customers/{customer['id']}",
        headers=headers,
        json={"name": "Updated Customer", "email": "updated@example.com"},
    )
    assert updated_customer.status_code == 200
    assert updated_customer.json()["name"] == "Updated Customer"

    property_record = client.post(
        "/api/v1/properties",
        headers=headers,
        json={"name": "Original Property", "customer_id": customer["id"]},
    ).json()
    updated_property = client.put(
        f"/api/v1/properties/{property_record['id']}",
        headers=headers,
        json={
            "name": "Updated Property",
            "location": "Burnaby, BC",
            "customer_id": customer["id"],
        },
    )
    assert updated_property.status_code == 200
    assert updated_property.json()["location"] == "Burnaby, BC"

    design = client.post(
        "/api/v1/design-projects",
        headers=headers,
        json={"name": "Original Design", "property_id": property_record["id"]},
    ).json()
    updated_design = client.put(
        f"/api/v1/design-projects/{design['id']}",
        headers=headers,
        json={
            "name": "Updated Design",
            "goal": "A refined concept",
            "property_id": property_record["id"],
        },
    )
    assert updated_design.status_code == 200
    assert updated_design.json()["name"] == "Updated Design"

    assert client.delete(f"/api/v1/customers/{customer['id']}", headers=headers).status_code == 204
    assert client.get("/api/v1/customers", headers=headers).json() == []
    assert client.get("/api/v1/properties", headers=headers).json() == []
    assert client.get("/api/v1/design-projects", headers=headers).json() == []


def test_cross_tenant_update_and_delete_return_not_found(client, create_identity):
    _, owner_headers = create_identity("CRUD Owner")
    _, outside_headers = create_identity("CRUD Outsider")
    customer = client.post(
        "/api/v1/customers", headers=owner_headers, json={"name": "Private Customer"}
    ).json()

    assert (
        client.put(
            f"/api/v1/customers/{customer['id']}",
            headers=outside_headers,
            json={"name": "Spoofed Customer"},
        ).status_code
        == 404
    )
    assert (
        client.delete(f"/api/v1/customers/{customer['id']}", headers=outside_headers).status_code
        == 404
    )
