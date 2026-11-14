"""Customer-facing quote PDF.

Markup is an internal number, so it is folded into the line prices: the customer sees
the selling price of each line and the lines add up to the quoted subtotal.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal
from io import BytesIO
from xml.sax.saxutils import escape

from PIL import Image as PILImage
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    Image,
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

INK = colors.HexColor("#13261a")
FOREST = colors.HexColor("#1f6b45")
MUTED = colors.HexColor("#5f6f64")
LINE = colors.HexColor("#dfe7e1")
TINT = colors.HexColor("#f2f7f3")
CENT = Decimal("0.01")
VALID_DAYS = 30


@dataclass(frozen=True)
class Party:
    name: str
    email: str | None = None
    phone: str | None = None
    address: str | None = None


@dataclass(frozen=True)
class QuoteLine:
    description: str
    quantity: Decimal
    unit: str
    unit_price: Decimal
    line_total: Decimal


@dataclass(frozen=True)
class QuoteDocument:
    number: str
    title: str
    created_at: datetime
    currency: str
    lines: list[QuoteLine]
    subtotal: Decimal
    markup_amount: Decimal
    discount_amount: Decimal
    tax_rate: Decimal
    tax_amount: Decimal
    total: Decimal
    assumptions: str | None
    company: Party
    customer: Party | None
    property_name: str | None
    property_location: str | None
    measurement: str | None = None
    logo: bytes | None = None
    before_photo: bytes | None = None
    concept_photo: bytes | None = None


def selling_lines(lines: list[QuoteLine], subtotal: Decimal, markup: Decimal) -> list[QuoteLine]:
    """Spread the markup across the lines in proportion to their cost.

    Line amounts are rounded to cents and the rounding difference goes on the largest
    line, so the printed lines always add up to subtotal + markup exactly.
    """
    if not lines or markup <= 0 or subtotal <= 0:
        return lines
    factor = (subtotal + markup) / subtotal
    adjusted = []
    for line in lines:
        amount = (line.line_total * factor).quantize(CENT, ROUND_HALF_UP)
        unit_price = (
            (amount / line.quantity).quantize(CENT, ROUND_HALF_UP) if line.quantity else amount
        )
        adjusted.append(
            QuoteLine(line.description, line.quantity, line.unit, unit_price, amount)
        )
    difference = (subtotal + markup) - sum(line.line_total for line in adjusted)
    if difference:
        index = max(range(len(adjusted)), key=lambda i: adjusted[i].line_total)
        line = adjusted[index]
        adjusted[index] = QuoteLine(
            line.description,
            line.quantity,
            line.unit,
            line.unit_price,
            line.line_total + difference,
        )
    return adjusted


def _money(value: Decimal, currency: str | None = None) -> str:
    text = f"${value.quantize(CENT, ROUND_HALF_UP):,.2f}"
    return f"{text} {currency}" if currency else text


def _quantity(value: Decimal) -> str:
    text = f"{value.normalize():f}"
    return text.rstrip("0").rstrip(".") if "." in text else text


def _date(value: datetime) -> str:
    return f"{value:%B} {value.day}, {value.year}"


def _image(data: bytes | None, max_width: float, max_height: float) -> Image | None:
    if not data:
        return None
    try:
        with PILImage.open(BytesIO(data)) as source:
            source.load()
            picture = source.convert("RGBA" if source.mode in {"RGBA", "LA", "P"} else "RGB")
    except Exception:
        return None
    width, height = picture.size
    scale = min(max_width / width, max_height / height)
    buffer = BytesIO()
    if picture.mode == "RGBA":
        picture.save(buffer, format="PNG")
    else:
        # Keep the PDF small enough to email: photos are re-encoded at print resolution.
        target = (min(width, round(max_width / inch * 200)), None)
        if target[0] < width:
            picture = picture.resize((target[0], round(height * target[0] / width)))
        picture.save(buffer, format="JPEG", quality=82)
    buffer.seek(0)
    return Image(buffer, width=width * scale, height=height * scale)


def _party_lines(party: Party, style: ParagraphStyle) -> list[Paragraph]:
    rows = [Paragraph(f"<b>{escape(party.name)}</b>", style)]
    for value in (party.address, party.phone, party.email):
        if value:
            rows.append(Paragraph(escape(value), style))
    return rows


def render_quote_pdf(document: QuoteDocument) -> bytes:
    buffer = BytesIO()
    margin = 0.7 * inch
    pdf = SimpleDocTemplate(
        buffer,
        pagesize=LETTER,
        leftMargin=margin,
        rightMargin=margin,
        topMargin=0.6 * inch,
        bottomMargin=0.7 * inch,
        title=f"Quote {document.number}",
        author=document.company.name,
        subject=document.title,
    )
    # Frames keep 6 pt of padding on each side.
    width = LETTER[0] - 2 * margin - 12
    body = ParagraphStyle("body", fontName="Helvetica", fontSize=9.5, leading=13, textColor=INK)
    small = ParagraphStyle("small", parent=body, fontSize=8.5, leading=11.5, textColor=MUTED)
    label = ParagraphStyle(
        "label", parent=body, fontName="Helvetica-Bold", fontSize=7.5, leading=10,
        textColor=FOREST, spaceAfter=3,
    )
    right = ParagraphStyle("right", parent=body, alignment=TA_RIGHT)
    heading = ParagraphStyle(
        "heading", parent=body, fontName="Helvetica-Bold", fontSize=22, leading=26,
        alignment=TA_RIGHT,
    )
    title_style = ParagraphStyle(
        "title", parent=body, fontName="Helvetica-Bold", fontSize=13, leading=17, spaceAfter=4
    )

    story: list = []
    issued = document.created_at
    valid_until = issued + timedelta(days=VALID_DAYS)
    logo = _image(document.logo, 2.0 * inch, 0.9 * inch)
    company_block = [logo] if logo else []
    company_block += _party_lines(document.company, small if logo else body)
    meta = [
        Paragraph("QUOTE", heading),
        Spacer(1, 4),
        Paragraph(f"<b>{escape(document.number)}</b>", right),
        Paragraph(f"Date: {_date(issued)}", right),
        Paragraph(f"Valid until: {_date(valid_until)}", right),
    ]
    header = Table([[company_block, meta]], colWidths=[width * 0.6, width * 0.4])
    header.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
    ]))
    story += [header, Spacer(1, 10)]

    prepared: list = [Paragraph("PREPARED FOR", label)]
    if document.customer:
        prepared += _party_lines(document.customer, body)
    else:
        prepared.append(Paragraph("—", body))
    site: list = [Paragraph("PROJECT SITE", label)]
    if document.property_name:
        site.append(Paragraph(f"<b>{escape(document.property_name)}</b>", body))
    if document.property_location:
        site.append(Paragraph(escape(document.property_location), body))
    parties = Table([[prepared, site]], colWidths=[width / 2, width / 2])
    parties.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BACKGROUND", (0, 0), (-1, -1), TINT),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
        ("LINEAFTER", (0, 0), (0, -1), 0.5, LINE),
    ]))
    story += [parties, Spacer(1, 12), Paragraph(escape(document.title), title_style)]

    half = (width - 12) / 2
    before = _image(document.before_photo, half, 2.1 * inch)
    after = _image(document.concept_photo, half, 2.1 * inch)
    if after:
        pictures = [[before or "", after]] if before else [[after]]
        caption = ParagraphStyle("caption", parent=small, alignment=TA_CENTER)
        captions = (
            [[Paragraph("Today", caption), Paragraph("Proposed design (AI concept)", caption)]]
            if before
            else [[Paragraph("Proposed design (AI concept)", caption)]]
        )
        gallery = Table(pictures + captions, colWidths=[half + 6, half + 6] if before else [width])
        gallery.setStyle(TableStyle([
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 0),
            ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ("TOPPADDING", (0, 1), (-1, 1), 3),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ]))
        story += [gallery, Spacer(1, 4)]
        if document.measurement:
            story.append(Paragraph(escape(document.measurement), small))
        story.append(Spacer(1, 8))

    lines = selling_lines(document.lines, document.subtotal, document.markup_amount)
    rows: list = [["Description", "Qty", "Unit", "Unit price", "Amount"]]
    for line in lines:
        rows.append([
            Paragraph(escape(line.description), body),
            _quantity(line.quantity),
            line.unit,
            _money(line.unit_price),
            _money(line.line_total),
        ])
    items = Table(
        rows,
        colWidths=[width * 0.44, width * 0.1, width * 0.12, width * 0.16, width * 0.18],
        repeatRows=1,
    )
    items.setStyle(TableStyle([
        ("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 8),
        ("TEXTCOLOR", (0, 0), (-1, 0), MUTED),
        ("FONT", (0, 1), (-1, -1), "Helvetica", 9.5),
        ("TEXTCOLOR", (0, 1), (-1, -1), INK),
        ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
        ("ALIGN", (2, 0), (2, -1), "LEFT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LINEBELOW", (0, 0), (-1, 0), 0.8, INK),
        ("LINEBELOW", (0, 1), (-1, -1), 0.4, LINE),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
    ]))
    story += [items, Spacer(1, 8)]

    subtotal = document.subtotal + document.markup_amount
    totals = [["Subtotal", _money(subtotal)]]
    if document.discount_amount > 0:
        totals.append(["Discount", f"-{_money(document.discount_amount)}"])
    totals.append([f"Tax ({_quantity(document.tax_rate)}%)", _money(document.tax_amount)])
    totals.append(["Total", _money(document.total, document.currency)])
    summary = Table(totals, colWidths=[width * 0.22, width * 0.2], hAlign="RIGHT")
    summary.setStyle(TableStyle([
        ("FONT", (0, 0), (-1, -1), "Helvetica", 9.5),
        ("TEXTCOLOR", (0, 0), (0, -2), MUTED),
        ("ALIGN", (0, 0), (-1, -1), "RIGHT"),
        ("FONT", (0, -1), (-1, -1), "Helvetica-Bold", 12),
        ("LINEABOVE", (0, -1), (-1, -1), 1.2, INK),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, -1), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
    ]))
    story += [summary, Spacer(1, 10)]

    if document.assumptions:
        notes = [Paragraph("NOTES", label)] + [
            Paragraph(escape(paragraph), small)
            for paragraph in document.assumptions.splitlines()
            if paragraph.strip()
        ]
        story += [*notes, Spacer(1, 12)]

    acceptance = Table(
        [
            [Paragraph("ACCEPTANCE", label), ""],
            [
                Paragraph(
                    f"To accept this quote, sign and return it before {_date(valid_until)}.",
                    small,
                ),
                "",
            ],
            ["", ""],
            [Paragraph("Signature", small), Paragraph("Date", small)],
        ],
        colWidths=[width * 0.6, width * 0.4],
        rowHeights=[None, None, 26, None],
    )
    acceptance.setStyle(TableStyle([
        ("SPAN", (0, 0), (1, 0)),
        ("SPAN", (0, 1), (1, 1)),
        ("LINEBELOW", (0, 2), (0, 2), 0.6, INK),
        ("LINEBELOW", (1, 2), (1, 2), 0.6, INK),
        ("LEFTPADDING", (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (0, -1), 18),
        ("TOPPADDING", (0, 0), (-1, -1), 1),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))
    story.append(KeepTogether([acceptance]))

    def footer(canvas, doc) -> None:
        canvas.saveState()
        canvas.setFont("Helvetica", 7.5)
        canvas.setFillColor(MUTED)
        canvas.drawString(margin, 0.42 * inch, f"{document.company.name} · Quote {document.number}")
        canvas.drawRightString(LETTER[0] - margin, 0.42 * inch, f"Page {doc.page}")
        canvas.restoreState()

    pdf.build(story, onFirstPage=footer, onLaterPages=footer)
    return buffer.getvalue()
