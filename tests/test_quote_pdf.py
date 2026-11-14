from decimal import Decimal

from groundsops.quote_pdf import QuoteLine, selling_lines


def _line(description: str, quantity: str, price: str) -> QuoteLine:
    q, p = Decimal(quantity), Decimal(price)
    return QuoteLine(description, q, "unit", p, (q * p).quantize(Decimal("0.01")))


def test_markup_is_folded_into_line_prices_and_still_adds_up():
    lines = [
        _line("Sod", "561.6", "0.85"),
        _line("Labour", "5.2", "65"),
        _line("Delivery", "1", "150"),
    ]
    subtotal = sum(line.line_total for line in lines)
    markup = (subtotal * Decimal("0.10")).quantize(Decimal("0.01"))

    selling = selling_lines(lines, subtotal, markup)

    assert sum(line.line_total for line in selling) == subtotal + markup
    assert all(new.line_total > old.line_total for new, old in zip(selling, lines, strict=True))
    assert selling_lines(lines, subtotal, Decimal("0")) == lines


def _quote(client, headers, customer_name: str) -> dict:
    customer = client.post(
        "/api/v1/customers",
        headers=headers,
        json={"name": customer_name, "email": "jo@example.com", "phone": "604-555-0100"},
    ).json()
    site = client.post(
        "/api/v1/properties",
        headers=headers,
        json={"name": "Front yard", "customer_id": customer["id"], "location": "Surrey, BC"},
    ).json()
    design = client.post(
        "/api/v1/design-projects",
        headers=headers,
        json={"name": "New lawn", "property_id": site["id"]},
    ).json()
    response = client.post(
        "/api/v1/quotes",
        headers=headers,
        json={
            "design_project_id": design["id"],
            "title": "Front lawn renovation",
            "items": [
                {"description": "Sod", "category": "material", "quantity": "561.6",
                 "unit": "sq ft", "unit_price": "0.85"},
                {"description": "Installation labour", "category": "labour",
                 "quantity": "5.2", "unit": "hour", "unit_price": "65"},
            ],
            "markup_rate": "10",
            "tax_rate": "5",
            "assumptions": "Includes removal of the existing turf.",
        },
    )
    assert response.status_code == 201
    return response.json()


def test_quote_pdf_downloads_for_its_company_only(client, create_identity):
    _, headers = create_identity("Pdf Landscaping")
    quote = _quote(client, headers, "Jo Customer")

    response = client.get(f"/api/v1/quotes/{quote['id']}/pdf", headers=headers)

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert f'filename="{quote["number"]}.pdf"' in response.headers["content-disposition"]
    assert response.content.startswith(b"%PDF")
    assert f"Quote {quote['number']}".encode() in response.content

    _, other_headers = create_identity("Other Pdf Landscaping")
    other = client.get(f"/api/v1/quotes/{quote['id']}/pdf", headers=other_headers)
    assert other.status_code == 404


def test_pdf_renders_logo_and_before_after_photos():
    from datetime import UTC, datetime
    from io import BytesIO

    from PIL import Image

    from groundsops.quote_pdf import Party, QuoteDocument, render_quote_pdf

    def picture(size, mode="RGB", fmt="JPEG"):
        out = BytesIO()
        Image.new(mode, size, (40, 120, 60, 255) if mode == "RGBA" else (40, 120, 60)).save(
            out, format=fmt
        )
        return out.getvalue()

    lines = [_line("Sod", "561.6", "0.85")]
    pdf = render_quote_pdf(
        QuoteDocument(
            number="Q-2026-0007",
            title="Backyard sod",
            created_at=datetime(2026, 11, 14, tzinfo=UTC),
            currency="CAD",
            lines=lines,
            subtotal=lines[0].line_total,
            markup_amount=Decimal("47.74"),
            discount_amount=Decimal("10"),
            tax_rate=Decimal("5"),
            tax_amount=Decimal("25.76"),
            total=Decimal("540.86"),
            assumptions="Includes removal of the existing turf.\nAccess through the side gate.",
            company=Party("Milan Landscaping", "office@example.com", "604-555-0100", "Surrey, BC"),
            customer=Party("Jordan Patel", "jordan@example.com"),
            property_name="Backyard",
            property_location="Surrey, BC",
            measurement="Measured area about 520 sq ft.",
            logo=picture((400, 160), "RGBA", "PNG"),
            before_photo=picture((2040, 1530)),
            concept_photo=picture((1024, 768), fmt="PNG"),
        )
    )
    assert pdf.startswith(b"%PDF")
    assert pdf.count(b"/Subtype /Image") >= 3
    # Photos are downscaled for email, so the file stays small.
    assert len(pdf) < 600_000


def test_company_contact_details_are_saved_and_used_on_quotes(client, create_identity, monkeypatch):
    import groundsops.api as api_module

    _, headers = create_identity("Contact Landscaping")
    saved = client.put(
        "/api/v1/organization",
        headers=headers,
        json={
            "name": "Contact Landscaping",
            "contact_email": " office@contact.example ",
            "contact_phone": "604-555-0199",
            "contact_address": "123 Example St, Surrey, BC",
        },
    )
    assert saved.status_code == 200
    assert saved.json()["contact_email"] == "office@contact.example"

    # Renaming without contact fields keeps them; an empty string clears one.
    renamed = client.put(
        "/api/v1/organization",
        headers=headers,
        json={"name": "Contact Landscaping Ltd", "contact_phone": ""},
    ).json()
    assert renamed["contact_email"] == "office@contact.example"
    assert renamed["contact_phone"] is None

    captured = {}
    original = api_module.render_quote_pdf

    def capture(document):
        captured["company"] = document.company
        return original(document)

    monkeypatch.setattr(api_module, "render_quote_pdf", capture)
    quote = _quote(client, headers, "Contact Customer")
    assert client.get(f"/api/v1/quotes/{quote['id']}/pdf", headers=headers).status_code == 200
    assert captured["company"].name == "Contact Landscaping Ltd"
    assert captured["company"].email == "office@contact.example"
    assert captured["company"].address == "123 Example St, Surrey, BC"
