"""Check photo measurements against tape measurements taken on site.

Crews record what they measured with a tape on a generation; the company sees how
far the app was off, overall and per measuring method.
"""

from datetime import UTC, datetime
from decimal import ROUND_HALF_UP, Decimal
from statistics import median
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from groundsops.auth import CurrentPrincipal, ManagerPrincipal
from groundsops.db import get_db
from groundsops.models import DesignProject, GenerationJob

router = APIRouter(prefix="/api/v1", tags=["measurement accuracy"])
DbSession = Annotated[Session, Depends(get_db)]

METHOD_LABELS = {
    "reference_object": "Known object",
    "reference_line": "Reference line",
    "camera_reference": "Camera line",
}


class SiteMeasurementWrite(BaseModel):
    area: Decimal = Field(gt=0, le=10_000_000)
    perimeter: Decimal | None = Field(default=None, gt=0, le=1_000_000)
    notes: str | None = Field(default=None, max_length=500)


class SiteMeasurementRead(BaseModel):
    job_id: str
    unit: str
    estimated_area: Decimal
    site_area: Decimal
    area_error_percent: float
    estimated_perimeter: Decimal | None
    site_perimeter: Decimal | None
    perimeter_error_percent: float | None
    measured_at: datetime
    notes: str | None


class AccuracyCheck(SiteMeasurementRead):
    design_project_id: str
    design_name: str
    method: str
    reference: str | None


class MethodSummary(BaseModel):
    method: str
    count: int
    median_abs_error_percent: float
    within_5_percent: int
    within_10_percent: int


class AccuracySummary(BaseModel):
    count: int
    median_abs_error_percent: float | None
    mean_abs_error_percent: float | None
    within_5_percent: int
    within_10_percent: int
    by_method: list[MethodSummary]


class AccuracyReport(BaseModel):
    summary: AccuracySummary
    checks: list[AccuracyCheck]


def _error(estimated: Decimal | None, measured: Decimal | None) -> float | None:
    if estimated is None or measured is None or measured <= 0:
        return None
    # Half-up rounding, as people expect when reading a percentage (3.125 -> 3.13).
    return float(((estimated - measured) / measured * 100).quantize(Decimal("0.01"), ROUND_HALF_UP))


def _read(job: GenerationJob) -> SiteMeasurementRead:
    return SiteMeasurementRead(
        job_id=job.id,
        unit=job.calibration_unit or "",
        estimated_area=job.estimated_area,
        site_area=job.site_measured_area,
        area_error_percent=_error(job.estimated_area, job.site_measured_area),
        estimated_perimeter=job.estimated_perimeter,
        site_perimeter=job.site_measured_perimeter,
        perimeter_error_percent=_error(job.estimated_perimeter, job.site_measured_perimeter),
        measured_at=job.site_measured_at,
        notes=job.site_measurement_notes,
    )


def _job(job_id: str, organization_id: str, db: Session) -> GenerationJob:
    job = db.scalar(
        select(GenerationJob).where(
            GenerationJob.id == job_id, GenerationJob.organization_id == organization_id
        )
    )
    if job is None:
        raise HTTPException(status_code=404, detail="Generation job not found")
    return job


@router.put("/generations/{job_id}/site-measurement", response_model=SiteMeasurementRead)
def record_site_measurement(
    job_id: str, payload: SiteMeasurementWrite, principal: CurrentPrincipal, db: DbSession
) -> SiteMeasurementRead:
    """Any team member on site can record the tape-measured area for a concept."""
    job = _job(job_id, principal.organization_id, db)
    if not job.estimated_area or not job.calibration_unit:
        raise HTTPException(
            status_code=409, detail="This concept has no photo measurement to check"
        )
    job.site_measured_area = payload.area
    job.site_measured_perimeter = payload.perimeter
    job.site_measurement_notes = (payload.notes or "").strip() or None
    job.site_measured_at = datetime.now(UTC)
    db.commit()
    db.refresh(job)
    return _read(job)


@router.delete("/generations/{job_id}/site-measurement", status_code=204)
def clear_site_measurement(job_id: str, principal: CurrentPrincipal, db: DbSession) -> None:
    job = _job(job_id, principal.organization_id, db)
    job.site_measured_area = None
    job.site_measured_perimeter = None
    job.site_measurement_notes = None
    job.site_measured_at = None
    db.commit()


def _summarize(errors: list[float]) -> tuple[float, float, int, int]:
    absolute = [abs(value) for value in errors]
    return (
        float(Decimal(str(median(absolute))).quantize(Decimal("0.01"), ROUND_HALF_UP)),
        float(Decimal(str(sum(absolute) / len(absolute))).quantize(Decimal("0.01"), ROUND_HALF_UP)),
        sum(value <= 5 for value in absolute),
        sum(value <= 10 for value in absolute),
    )


@router.get("/measurement-accuracy", response_model=AccuracyReport)
def measurement_accuracy(principal: ManagerPrincipal, db: DbSession) -> AccuracyReport:
    rows = db.execute(
        select(GenerationJob, DesignProject.name)
        .join(DesignProject, DesignProject.id == GenerationJob.design_project_id)
        .where(
            GenerationJob.organization_id == principal.organization_id,
            GenerationJob.site_measured_area.is_not(None),
            GenerationJob.estimated_area.is_not(None),
        )
        .order_by(GenerationJob.site_measured_at.desc())
    ).all()
    checks = [
        AccuracyCheck(
            **_read(job).model_dump(),
            design_project_id=job.design_project_id,
            design_name=design_name,
            method=METHOD_LABELS.get(job.measurement_method or "", "Photo scale"),
            reference=job.calibration_reference,
        )
        for job, design_name in rows
    ]
    errors = [check.area_error_percent for check in checks]
    by_method = []
    for method in sorted({check.method for check in checks}):
        method_errors = [check.area_error_percent for check in checks if check.method == method]
        median_error, _, within_5, within_10 = _summarize(method_errors)
        by_method.append(
            MethodSummary(
                method=method,
                count=len(method_errors),
                median_abs_error_percent=median_error,
                within_5_percent=within_5,
                within_10_percent=within_10,
            )
        )
    if errors:
        median_error, mean_error, within_5, within_10 = _summarize(errors)
    else:
        median_error, mean_error, within_5, within_10 = None, None, 0, 0
    return AccuracyReport(
        summary=AccuracySummary(
            count=len(checks),
            median_abs_error_percent=median_error,
            mean_abs_error_percent=mean_error,
            within_5_percent=within_5,
            within_10_percent=within_10,
            by_method=by_method,
        ),
        checks=checks,
    )
