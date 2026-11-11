import enum
import uuid
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from groundsops.db import Base


def new_id() -> str:
    return str(uuid.uuid4())


def utc_now() -> datetime:
    return datetime.now(UTC)


class WorkOrderStatus(enum.StrEnum):
    DRAFT = "draft"
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"


class OrganizationRole(enum.StrEnum):
    ADMIN = "admin"
    MANAGER = "manager"
    DESIGNER = "designer"
    CREW = "crew"


class DesignStatus(enum.StrEnum):
    DRAFT = "draft"
    GENERATING = "generating"
    REVIEW = "review"
    ACCEPTED = "accepted"
    REJECTED = "rejected"


class QuoteStatus(enum.StrEnum):
    DRAFT = "draft"
    SENT = "sent"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"


class MaterialCategory(enum.StrEnum):
    GRASS = "grass"
    ARTIFICIAL_TURF = "artificial_turf"
    PAVER = "paver"
    GRAVEL = "gravel"
    MULCH = "mulch"
    SOIL = "soil"
    PLANT = "plant"


class CaptureStatus(enum.StrEnum):
    READY = "ready"
    DELETED = "deleted"


class InvoiceStatus(enum.StrEnum):
    DRAFT = "draft"
    SENT = "sent"
    PAID = "paid"
    VOID = "void"


class TimesheetStatus(enum.StrEnum):
    RUNNING = "running"
    SUBMITTED = "submitted"
    APPROVED = "approved"


class GenerationStatus(enum.StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class GenerationReviewDecision(enum.StrEnum):
    APPROVED = "approved"
    REJECTED = "rejected"
    REVISION_REQUESTED = "revision_requested"


class VaultFile(Base):
    __tablename__ = "vault_files"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    organization_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.id"), index=True
    )
    uploaded_by_user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organization_users.id"), index=True
    )
    folder_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("vault_folders.id"), index=True, nullable=True
    )
    site_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("vault_sites.id"), index=True, nullable=True
    )
    original_filename: Mapped[str] = mapped_column(String(255))
    media_type: Mapped[str] = mapped_column(String(100))
    byte_size: Mapped[int] = mapped_column()
    storage_key: Mapped[str] = mapped_column(String(500), unique=True)
    access_scope: Mapped[str] = mapped_column(String(20), default="organization")
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class VaultShare(Base):
    __tablename__ = "vault_shares"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    file_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("vault_files.id", ondelete="CASCADE"), index=True
    )
    organization_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.id"), index=True
    )
    created_by_user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organization_users.id"), index=True
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class VaultFolder(Base):
    __tablename__ = "vault_folders"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    organization_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.id"), index=True
    )
    created_by_user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organization_users.id"), index=True
    )
    site_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("vault_sites.id"), index=True, nullable=True
    )
    name: Mapped[str] = mapped_column(String(200))
    access_scope: Mapped[str] = mapped_column(String(20), default="organization")
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class VaultSite(Base):
    __tablename__ = "vault_sites"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    organization_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.id"), index=True
    )
    created_by_user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organization_users.id"), index=True
    )
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    access_scope: Mapped[str] = mapped_column(String(20), default="organization")
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class VaultContainerShare(Base):
    __tablename__ = "vault_container_shares"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    organization_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.id"), index=True
    )
    created_by_user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organization_users.id"), index=True
    )
    container_type: Mapped[str] = mapped_column(String(10))
    container_id: Mapped[str] = mapped_column(String(36), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(200))
    logo_storage_key: Mapped[str | None] = mapped_column(String(500), nullable=True)
    logo_media_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    invoice_logo_storage_key: Mapped[str | None] = mapped_column(String(500), nullable=True)
    invoice_logo_media_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    subscription_status: Mapped[str] = mapped_column(
        String(30), default="trialing", server_default="trialing"
    )
    trial_ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    current_period_end: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    stripe_customer_id: Mapped[str | None] = mapped_column(
        String(100), nullable=True, unique=True, index=True
    )
    stripe_subscription_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    properties: Mapped[list["Property"]] = relationship(back_populates="organization")


class OrganizationUser(Base):
    __tablename__ = "organization_users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    organization_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.id"), index=True
    )
    email: Mapped[str] = mapped_column(String(320))
    cognito_subject: Mapped[str | None] = mapped_column(
        String(100), nullable=True, unique=True, index=True
    )
    display_name: Mapped[str] = mapped_column(String(200))
    role: Mapped[str] = mapped_column(String(20), default=OrganizationRole.CREW.value)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class OrganizationInvitation(Base):
    __tablename__ = "organization_invitations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    organization_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.id"), index=True
    )
    invited_by_user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organization_users.id"), index=True
    )
    email: Mapped[str] = mapped_column(String(320), index=True)
    role: Mapped[str] = mapped_column(String(20), default=OrganizationRole.CREW.value)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)


class Customer(Base):
    __tablename__ = "customers"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    organization_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.id"), index=True
    )
    name: Mapped[str] = mapped_column(String(200))
    email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(40), nullable=True)
    address: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    properties: Mapped[list["Property"]] = relationship(back_populates="customer")


class Property(Base):
    __tablename__ = "properties"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    organization_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.id"), index=True
    )
    customer_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("customers.id"), index=True, nullable=True
    )
    name: Mapped[str] = mapped_column(String(200))
    location: Mapped[str | None] = mapped_column(String(300), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    organization: Mapped[Organization] = relationship(back_populates="properties")
    customer: Mapped[Customer | None] = relationship(back_populates="properties")
    work_orders: Mapped[list["WorkOrder"]] = relationship(back_populates="property")
    design_projects: Mapped[list["DesignProject"]] = relationship(back_populates="property")


class WorkOrder(Base):
    __tablename__ = "work_orders"
    __table_args__ = (UniqueConstraint("quote_id", name="uq_work_order_quote_id"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    organization_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.id"), index=True
    )
    property_id: Mapped[str] = mapped_column(String(36), ForeignKey("properties.id"), index=True)
    quote_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("quotes.id", ondelete="SET NULL"), index=True, nullable=True
    )
    design_project_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("design_projects.id", ondelete="SET NULL"), index=True, nullable=True
    )
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default=WorkOrderStatus.DRAFT.value)
    assigned_user_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("organization_users.id"), index=True, nullable=True
    )
    scheduled_start: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), index=True, nullable=True
    )
    scheduled_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    priority: Mapped[str] = mapped_column(String(20), default="normal")
    quoted_total: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    quote_currency: Mapped[str | None] = mapped_column(String(3), nullable=True)
    material_checklist: Mapped[list[dict] | None] = mapped_column(JSON, nullable=True)
    customer_instructions: Mapped[str | None] = mapped_column(Text, nullable=True)
    actual_labour_hours: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    actual_labour_rate: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    actual_materials: Mapped[list[dict] | None] = mapped_column(JSON, nullable=True)
    actual_total: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)
    completion_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    property: Mapped[Property] = relationship(back_populates="work_orders")


class Material(Base):
    __tablename__ = "materials"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    organization_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.id"), index=True
    )
    name: Mapped[str] = mapped_column(String(200))
    category: Mapped[str] = mapped_column(String(30))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    variants: Mapped[list["MaterialVariant"]] = relationship(back_populates="material")


class MaterialVariant(Base):
    __tablename__ = "material_variants"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    organization_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.id"), index=True
    )
    material_id: Mapped[str] = mapped_column(String(36), ForeignKey("materials.id"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    colour: Mapped[str | None] = mapped_column(String(100), nullable=True)
    unit: Mapped[str] = mapped_column(String(30))
    default_waste_percent: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("10.00"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    material: Mapped[Material] = relationship(back_populates="variants")


class DesignProject(Base):
    __tablename__ = "design_projects"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    organization_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.id"), index=True
    )
    property_id: Mapped[str] = mapped_column(String(36), ForeignKey("properties.id"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    goal: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default=DesignStatus.DRAFT.value)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    property: Mapped[Property] = relationship(back_populates="design_projects")
    quotes: Mapped[list["Quote"]] = relationship(back_populates="design_project")
    captures: Mapped[list["SiteCapture"]] = relationship(back_populates="design_project")


class SiteCapture(Base):
    __tablename__ = "site_captures"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    organization_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.id"), index=True
    )
    design_project_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("design_projects.id"), index=True
    )
    uploaded_by_user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organization_users.id"), index=True
    )
    original_filename: Mapped[str] = mapped_column(String(255))
    storage_key: Mapped[str] = mapped_column(String(500), unique=True)
    media_type: Mapped[str] = mapped_column(String(50))
    byte_size: Mapped[int]
    width: Mapped[int]
    height: Mapped[int]
    sha256: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(20), default=CaptureStatus.READY.value)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    design_project: Mapped[DesignProject] = relationship(back_populates="captures")


class GenerationJob(Base):
    __tablename__ = "generation_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    organization_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.id"), index=True
    )
    design_project_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("design_projects.id"), index=True
    )
    capture_id: Mapped[str] = mapped_column(String(36), ForeignKey("site_captures.id"), index=True)
    requested_by_user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organization_users.id"), index=True
    )
    prompt: Mapped[str] = mapped_column(Text)
    provider: Mapped[str] = mapped_column(String(30))
    model_version: Mapped[str] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(
        String(20), default=GenerationStatus.QUEUED.value, index=True
    )
    mask_storage_key: Mapped[str] = mapped_column(String(500), unique=True)
    measurement_method: Mapped[str | None] = mapped_column(String(30), nullable=True)
    selected_pixel_count: Mapped[int | None] = mapped_column(nullable=True)
    total_pixel_count: Mapped[int | None] = mapped_column(nullable=True)
    calibration_pixel_length: Mapped[Decimal | None] = mapped_column(Numeric(12, 4), nullable=True)
    calibration_real_length: Mapped[Decimal | None] = mapped_column(Numeric(12, 4), nullable=True)
    calibration_unit: Mapped[str | None] = mapped_column(String(10), nullable=True)
    estimated_area: Mapped[Decimal | None] = mapped_column(Numeric(14, 4), nullable=True)
    estimated_perimeter: Mapped[Decimal | None] = mapped_column(Numeric(14, 4), nullable=True)
    measurement_confidence: Mapped[str | None] = mapped_column(String(30), nullable=True)
    output_storage_key: Mapped[str | None] = mapped_column(String(500), nullable=True)
    output_media_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    provider_prediction_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(nullable=True)
    estimated_cost_usd: Mapped[Decimal | None] = mapped_column(Numeric(10, 4), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    evaluation: Mapped["GenerationEvaluation | None"] = relationship(
        back_populates="generation_job",
        cascade="all, delete-orphan",
        uselist=False,
    )
    reviews: Mapped[list["GenerationReview"]] = relationship(
        back_populates="generation_job",
        cascade="all, delete-orphan",
        order_by="GenerationReview.created_at",
    )
    material_estimate: Mapped["GenerationMaterialEstimate | None"] = relationship(
        back_populates="generation_job",
        cascade="all, delete-orphan",
        uselist=False,
    )


class GenerationMaterialEstimate(Base):
    __tablename__ = "generation_material_estimates"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    organization_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.id"), index=True
    )
    generation_job_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("generation_jobs.id", ondelete="CASCADE"),
        unique=True,
        index=True,
    )
    material_type: Mapped[str] = mapped_column(String(30))
    measurement_unit: Mapped[str] = mapped_column(String(10))
    measured_area: Mapped[Decimal] = mapped_column(Numeric(14, 4))
    measured_perimeter: Mapped[Decimal] = mapped_column(Numeric(14, 4))
    waste_percent: Mapped[Decimal] = mapped_column(Numeric(6, 2))
    depth: Mapped[Decimal | None] = mapped_column(Numeric(8, 2), nullable=True)
    order_quantity: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    material_unit: Mapped[str] = mapped_column(String(20))
    edging_quantity: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    labour_hours: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    labour_rate: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    delivery_cost: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    material_cost: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    labour_cost: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    subtotal: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    tax_rate: Mapped[Decimal] = mapped_column(Numeric(6, 3))
    tax_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    total: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    currency: Mapped[str] = mapped_column(String(3), default="CAD")
    assumptions: Mapped[list[str]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )
    generation_job: Mapped[GenerationJob] = relationship(back_populates="material_estimate")


class GenerationEvaluation(Base):
    __tablename__ = "generation_evaluations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    organization_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.id"), index=True
    )
    generation_job_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("generation_jobs.id", ondelete="CASCADE"),
        unique=True,
        index=True,
    )
    evaluator_version: Mapped[str] = mapped_column(String(50))
    dimensions_match: Mapped[bool] = mapped_column(Boolean)
    masked_change_ratio: Mapped[Decimal] = mapped_column(Numeric(8, 6))
    protected_change_ratio: Mapped[Decimal] = mapped_column(Numeric(8, 6))
    masked_change_threshold: Mapped[Decimal] = mapped_column(Numeric(8, 6))
    protected_change_threshold: Mapped[Decimal] = mapped_column(Numeric(8, 6))
    pixel_change_threshold: Mapped[Decimal] = mapped_column(Numeric(8, 6))
    passed: Mapped[bool] = mapped_column(Boolean, index=True)
    failure_reasons: Mapped[list[str]] = mapped_column(JSON, default=list)
    evaluation_latency_ms: Mapped[int]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    generation_job: Mapped[GenerationJob] = relationship(back_populates="evaluation")


class GenerationReview(Base):
    __tablename__ = "generation_reviews"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    organization_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.id"), index=True
    )
    generation_job_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("generation_jobs.id", ondelete="CASCADE"),
        index=True,
    )
    reviewer_user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organization_users.id"), index=True
    )
    decision: Mapped[str] = mapped_column(String(30), index=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    generation_job: Mapped[GenerationJob] = relationship(back_populates="reviews")


class Quote(Base):
    __tablename__ = "quotes"
    __table_args__ = (UniqueConstraint("organization_id", "number", name="uq_quote_org_number"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    organization_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.id"), index=True
    )
    design_project_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("design_projects.id"), index=True
    )
    generation_job_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("generation_jobs.id", ondelete="SET NULL"), index=True, nullable=True
    )
    number: Mapped[str] = mapped_column(String(40))
    title: Mapped[str] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(20), default=QuoteStatus.DRAFT.value)
    subtotal: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    markup_rate: Mapped[Decimal] = mapped_column(Numeric(6, 3), default=Decimal("0.00"))
    markup_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    discount_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    tax_rate: Mapped[Decimal] = mapped_column(Numeric(6, 3), default=Decimal("0.00"))
    tax_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    total: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0.00"))
    currency: Mapped[str] = mapped_column(String(3), default="CAD")
    assumptions: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )
    design_project: Mapped[DesignProject] = relationship(back_populates="quotes")
    items: Mapped[list["QuoteItem"]] = relationship(
        back_populates="quote", cascade="all, delete-orphan", order_by="QuoteItem.position"
    )


class QuoteItem(Base):
    __tablename__ = "quote_items"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    quote_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("quotes.id", ondelete="CASCADE"), index=True
    )
    description: Mapped[str] = mapped_column(String(500))
    category: Mapped[str] = mapped_column(String(30), default="other")
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    unit: Mapped[str] = mapped_column(String(30), default="unit")
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    line_total: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    position: Mapped[int] = mapped_column(default=0)
    quote: Mapped[Quote] = relationship(back_populates="items")


class Invoice(Base):
    __tablename__ = "invoices"
    __table_args__ = (UniqueConstraint("organization_id", "number", name="uq_invoice_org_number"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    organization_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.id"), index=True
    )
    customer_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("customers.id"), index=True, nullable=True
    )
    work_order_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("work_orders.id", ondelete="SET NULL"), unique=True, nullable=True
    )
    number: Mapped[str] = mapped_column(String(40))
    description: Mapped[str] = mapped_column(String(500))
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    rate: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    subtotal: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    currency: Mapped[str] = mapped_column(String(3), default="CAD")
    status: Mapped[str] = mapped_column(String(20), default=InvoiceStatus.DRAFT.value)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    customer_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    customer_email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    customer_phone: Mapped[str | None] = mapped_column(String(40), nullable=True)
    customer_address: Mapped[str | None] = mapped_column(String(500), nullable=True)
    company_email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    company_phone: Mapped[str | None] = mapped_column(String(40), nullable=True)
    company_address: Mapped[str | None] = mapped_column(String(500), nullable=True)
    gst_rate: Mapped[Decimal] = mapped_column(Numeric(6, 3), default=Decimal("0"))
    pst_rate: Mapped[Decimal] = mapped_column(Numeric(6, 3), default=Decimal("0"))
    gst_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    pst_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    total: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    paid_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    items: Mapped[list["InvoiceItem"]] = relationship(
        back_populates="invoice", cascade="all, delete-orphan", lazy="selectin"
    )
    payments: Mapped[list["InvoicePayment"]] = relationship(
        back_populates="invoice", cascade="all, delete-orphan", lazy="selectin"
    )

    @property
    def balance_due(self) -> Decimal:
        return max(Decimal("0"), self.total - self.paid_amount)


class InvoiceItem(Base):
    __tablename__ = "invoice_items"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    invoice_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("invoices.id", ondelete="CASCADE"), index=True
    )
    description: Mapped[str] = mapped_column(String(500))
    quantity: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    rate: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    line_total: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    position: Mapped[int] = mapped_column(default=0)
    invoice: Mapped[Invoice] = relationship(back_populates="items")


class InvoicePayment(Base):
    __tablename__ = "invoice_payments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    organization_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.id"), index=True
    )
    invoice_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("invoices.id", ondelete="CASCADE"), index=True
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    method: Mapped[str] = mapped_column(String(30))
    reference: Mapped[str | None] = mapped_column(String(200), nullable=True)
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    invoice: Mapped[Invoice] = relationship(back_populates="payments")


class TimesheetEntry(Base):
    __tablename__ = "timesheet_entries"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    organization_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.id"), index=True
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organization_users.id"), index=True
    )
    property_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("properties.id"), index=True, nullable=True
    )
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default=TimesheetStatus.RUNNING.value)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
