"""Per-company price list used to pre-fill material estimates."""

from decimal import Decimal
from typing import Annotated, Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from groundsops.auth import CurrentPrincipal, ManagerPrincipal
from groundsops.db import get_db
from groundsops.estimates import DEFAULT_WASTE, MATERIALS, VOLUME_MATERIALS
from groundsops.models import Organization, PriceListItem

router = APIRouter(prefix="/api/v1", tags=["price list"])
DbSession = Annotated[Session, Depends(get_db)]

MaterialType = Literal["sod", "pavers", "mulch", "gravel", "topsoil"]
MATERIAL_ORDER: tuple[str, ...] = ("sod", "pavers", "mulch", "gravel", "topsoil")
DEFAULT_DEPTH_INCHES = {"mulch": Decimal("3"), "gravel": Decimal("3"), "topsoil": Decimal("4")}
assert set(MATERIAL_ORDER) == MATERIALS


class PriceListItemData(BaseModel):
    material_type: MaterialType
    unit_price: Decimal = Field(default=Decimal("0"), ge=0, le=100000)
    waste_percent: Decimal = Field(ge=0, le=50)
    depth: Decimal | None = Field(default=None, gt=0, le=36)
    supplier: str | None = Field(default=None, max_length=200)


class PriceListData(BaseModel):
    items: list[PriceListItemData]
    labour_rate: Decimal = Field(ge=0, le=10000)
    delivery_cost: Decimal = Field(ge=0, le=1000000)
    tax_rate: Decimal = Field(ge=0, le=100)


def _read(db: Session, organization_id: str) -> PriceListData:
    organization = db.get(Organization, organization_id)
    saved = {
        row.material_type: row
        for row in db.scalars(
            select(PriceListItem).where(PriceListItem.organization_id == organization_id)
        )
    }
    items = []
    for material in MATERIAL_ORDER:
        row = saved.get(material)
        items.append(
            PriceListItemData(
                material_type=material,
                unit_price=row.unit_price if row else Decimal("0"),
                waste_percent=row.waste_percent if row else DEFAULT_WASTE[material],
                depth=(row.depth if row else DEFAULT_DEPTH_INCHES.get(material))
                if material in VOLUME_MATERIALS
                else None,
                supplier=row.supplier if row else None,
            )
        )
    return PriceListData(
        items=items,
        labour_rate=organization.estimate_labour_rate,
        delivery_cost=organization.estimate_delivery_cost,
        tax_rate=organization.estimate_tax_rate,
    )


@router.get("/price-list", response_model=PriceListData)
def get_price_list(principal: CurrentPrincipal, db: DbSession) -> PriceListData:
    return _read(db, principal.organization_id)


@router.put("/price-list", response_model=PriceListData)
def save_price_list(
    payload: PriceListData, principal: ManagerPrincipal, db: DbSession
) -> PriceListData:
    organization = db.get(Organization, principal.organization_id)
    organization.estimate_labour_rate = payload.labour_rate
    organization.estimate_delivery_cost = payload.delivery_cost
    organization.estimate_tax_rate = payload.tax_rate
    existing = {
        row.material_type: row
        for row in db.scalars(
            select(PriceListItem).where(
                PriceListItem.organization_id == principal.organization_id
            )
        )
    }
    for item in payload.items:
        row = existing.get(item.material_type) or PriceListItem(
            organization_id=principal.organization_id, material_type=item.material_type
        )
        row.unit_price = item.unit_price
        row.waste_percent = item.waste_percent
        row.depth = item.depth if item.material_type in VOLUME_MATERIALS else None
        row.supplier = (item.supplier or "").strip() or None
        db.add(row)
    db.commit()
    return _read(db, principal.organization_id)
