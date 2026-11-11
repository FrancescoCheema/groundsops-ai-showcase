from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

MATERIALS = {"sod", "pavers", "mulch", "gravel", "topsoil"}
AREA_MATERIALS = {"sod", "pavers"}
VOLUME_MATERIALS = {"mulch", "gravel", "topsoil"}

DEFAULT_WASTE = {
    "sod": Decimal("8"),
    "pavers": Decimal("10"),
    "mulch": Decimal("10"),
    "gravel": Decimal("10"),
    "topsoil": Decimal("10"),
}

PRODUCTIVITY_SQ_FT_PER_HOUR = {
    "sod": Decimal("100"),
    "pavers": Decimal("25"),
    "mulch": Decimal("120"),
    "gravel": Decimal("80"),
    "topsoil": Decimal("80"),
}


def money(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def quantity(value: Decimal) -> Decimal:
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


@dataclass(frozen=True)
class EstimateCalculation:
    order_quantity: Decimal
    material_unit: str
    edging_quantity: Decimal
    edging_unit: str
    labour_hours: Decimal
    material_cost: Decimal
    labour_cost: Decimal
    subtotal: Decimal
    tax_amount: Decimal
    total: Decimal
    assumptions: list[str]


def calculate_material_estimate(
    *,
    material_type: str,
    area: Decimal,
    perimeter: Decimal,
    measurement_unit: str,
    waste_percent: Decimal,
    depth: Decimal | None,
    unit_price: Decimal,
    labour_rate: Decimal,
    labour_hours: Decimal | None,
    delivery_cost: Decimal,
    tax_rate: Decimal,
) -> EstimateCalculation:
    if material_type not in MATERIALS:
        raise ValueError("Unsupported material type")
    if measurement_unit not in {"ft", "m"}:
        raise ValueError("Unsupported measurement unit")
    if area <= 0 or perimeter <= 0:
        raise ValueError("Measured area and perimeter must be positive")

    multiplier = Decimal("1") + waste_percent / Decimal("100")
    assumptions = [f"Includes {waste_percent}% material waste"]
    if material_type in AREA_MATERIALS:
        order_quantity = area * multiplier
        material_unit = f"sq {measurement_unit}"
    else:
        if depth is None or depth <= 0:
            raise ValueError("Depth is required for volume materials")
        if measurement_unit == "ft":
            order_quantity = area * (depth / Decimal("12")) / Decimal("27") * multiplier
            material_unit = "cu yd"
            assumptions.append(f"Uses a {depth}-inch installed depth")
        else:
            order_quantity = area * (depth / Decimal("100")) * multiplier
            material_unit = "m³"
            assumptions.append(f"Uses a {depth}-cm installed depth")

    if labour_hours is None:
        area_sq_ft = area if measurement_unit == "ft" else area * Decimal("10.7639104")
        labour_hours = area_sq_ft / PRODUCTIVITY_SQ_FT_PER_HOUR[material_type]
        assumptions.append("Labour hours use a planning productivity benchmark")

    order_quantity = quantity(order_quantity)
    labour_hours = quantity(labour_hours)
    material_cost = money(order_quantity * unit_price)
    labour_cost = money(labour_hours * labour_rate)
    subtotal = money(material_cost + labour_cost + delivery_cost)
    tax_amount = money(subtotal * tax_rate / Decimal("100"))
    return EstimateCalculation(
        order_quantity=order_quantity,
        material_unit=material_unit,
        edging_quantity=quantity(perimeter),
        edging_unit=measurement_unit,
        labour_hours=labour_hours,
        material_cost=material_cost,
        labour_cost=labour_cost,
        subtotal=subtotal,
        tax_amount=tax_amount,
        total=money(subtotal + tax_amount),
        assumptions=assumptions,
    )
