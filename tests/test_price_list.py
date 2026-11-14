def test_price_list_starts_with_defaults_for_every_material(client, create_identity):
    _, headers = create_identity("Price Defaults")

    body = client.get("/api/v1/price-list", headers=headers).json()

    assert [item["material_type"] for item in body["items"]] == [
        "sod", "pavers", "mulch", "gravel", "topsoil"
    ]
    by_type = {item["material_type"]: item for item in body["items"]}
    assert float(by_type["sod"]["waste_percent"]) == 8
    assert by_type["sod"]["depth"] is None
    assert float(by_type["topsoil"]["depth"]) == 4
    assert float(body["tax_rate"]) == 12


def test_manager_saves_prices_and_they_stay_per_company(client, create_identity):
    _, headers = create_identity("Milan Landscaping", role="manager")
    _, other_headers = create_identity("Other Company")
    current = client.get("/api/v1/price-list", headers=headers).json()
    for item in current["items"]:
        if item["material_type"] == "sod":
            item.update(unit_price="1.35", supplier="Local sod farm")
        if item["material_type"] == "pavers":
            item["depth"] = "6"  # ignored: pavers are priced by area
    current.update(labour_rate="68", delivery_cost="95", tax_rate="5")

    saved = client.put("/api/v1/price-list", headers=headers, json=current)

    assert saved.status_code == 200
    by_type = {item["material_type"]: item for item in saved.json()["items"]}
    assert float(by_type["sod"]["unit_price"]) == 1.35
    assert by_type["sod"]["supplier"] == "Local sod farm"
    assert by_type["pavers"]["depth"] is None
    assert float(saved.json()["labour_rate"]) == 68
    other = client.get("/api/v1/price-list", headers=other_headers).json()
    assert float(other["items"][0]["unit_price"]) == 0


def test_crew_can_read_but_not_change_prices(client, create_identity):
    _, headers = create_identity("Crew Prices", role="crew")
    current = client.get("/api/v1/price-list", headers=headers)
    assert current.status_code == 200

    response = client.put("/api/v1/price-list", headers=headers, json=current.json())

    assert response.status_code == 403
