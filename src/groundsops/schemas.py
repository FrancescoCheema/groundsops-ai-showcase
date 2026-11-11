from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from groundsops.models import (
    CaptureStatus,
    DesignStatus,
    InvoiceStatus,
    MaterialCategory,
    OrganizationRole,
    QuoteStatus,
    TimesheetStatus,
    WorkOrderStatus,
)


class OrganizationCreate(BaseModel):
    name: str = Field(min_length=2, max_length=200)


class OrganizationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    name: str
    logo_media_type: str | None
    invoice_logo_media_type: str | None
    created_at: datetime


class OrganizationUpdate(BaseModel):
    name: str = Field(min_length=2, max_length=200)


class DevelopmentTokenRequest(BaseModel):
    organization_id: str
    email: str = Field(min_length=3, max_length=320)


class DevelopmentSignupTokenRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    display_name: str = Field(min_length=2, max_length=200)


class DevelopmentBootstrapRequest(BaseModel):
    organization_name: str = Field(min_length=2, max_length=200)
    admin_email: str = Field(min_length=3, max_length=320)
    admin_display_name: str = Field(min_length=2, max_length=200)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class DevelopmentBootstrapResponse(TokenResponse):
    organization_id: str
    user_id: str


class PropertyCreate(BaseModel):
    customer_id: str | None = None
    name: str = Field(min_length=2, max_length=200)
    location: str | None = Field(default=None, max_length=300)


class PropertyUpdate(PropertyCreate):
    pass


class PropertyRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    organization_id: str
    customer_id: str | None
    name: str
    location: str | None
    created_at: datetime


class WorkOrderCreate(BaseModel):
    property_id: str
    title: str = Field(min_length=2, max_length=200)
    description: str = Field(min_length=2, max_length=5000)
    assigned_user_id: str | None = None
    scheduled_start: datetime | None = None
    scheduled_end: datetime | None = None
    priority: str = Field(default="normal", pattern="^(low|normal|high|urgent)$")


class WorkOrderUpdate(WorkOrderCreate):
    status: WorkOrderStatus = WorkOrderStatus.DRAFT


class WorkOrderRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    organization_id: str
    property_id: str
    quote_id: str | None
    design_project_id: str | None
    title: str
    description: str
    status: WorkOrderStatus
    assigned_user_id: str | None
    scheduled_start: datetime | None
    scheduled_end: datetime | None
    priority: str
    quoted_total: Decimal | None
    quote_currency: str | None
    material_checklist: list[dict] | None
    customer_instructions: str | None
    actual_labour_hours: Decimal | None
    actual_labour_rate: Decimal | None
    actual_materials: list[dict] | None
    actual_total: Decimal | None
    completion_notes: str | None
    completed_at: datetime | None
    created_at: datetime


class QuoteWorkOrderCreate(BaseModel):
    assigned_user_id: str | None = None
    scheduled_start: datetime
    scheduled_end: datetime
    priority: str = Field(default="normal", pattern="^(low|normal|high|urgent)$")
    customer_instructions: str | None = Field(default=None, max_length=5000)


class ActualMaterial(BaseModel):
    description: str = Field(min_length=2, max_length=500)
    quantity: Decimal = Field(gt=0, le=1000000)
    unit: str = Field(min_length=1, max_length=30)
    unit_price: Decimal = Field(ge=0, le=100000000)


class WorkOrderCompletionCreate(BaseModel):
    labour_hours: Decimal = Field(default=Decimal("0"), ge=0, le=100000)
    labour_rate: Decimal = Field(default=Decimal("0"), ge=0, le=10000)
    materials: list[ActualMaterial] = Field(default_factory=list, max_length=100)
    notes: str | None = Field(default=None, max_length=5000)


class WorkOrderVarianceRead(BaseModel):
    quoted_total: Decimal
    actual_total: Decimal
    variance_amount: Decimal
    variance_percent: Decimal | None


class OrganizationUserCreate(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    display_name: str = Field(min_length=2, max_length=200)
    role: OrganizationRole = OrganizationRole.CREW


class OrganizationUserRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    organization_id: str
    email: str
    display_name: str
    role: OrganizationRole
    active: bool
    created_at: datetime


class CurrentUserRead(BaseModel):
    id: str
    organization_id: str
    email: str
    role: OrganizationRole
    platform_admin: bool = False


class PlatformOrganizationRead(BaseModel):
    id: str
    name: str
    created_at: datetime
    user_count: int
    active_user_count: int
    subscription_status: str = "trialing"


class PlatformUserRead(OrganizationUserRead):
    organization_name: str


class OrganizationRegistrationCreate(BaseModel):
    organization_name: str = Field(min_length=2, max_length=200)
    display_name: str | None = Field(default=None, min_length=2, max_length=200)


class OrganizationRegistrationRead(BaseModel):
    organization: OrganizationRead
    user: OrganizationUserRead


class InvitationCreate(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    role: OrganizationRole = OrganizationRole.CREW
    expires_in_days: int = Field(default=7, ge=1, le=30)


class InvitationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    organization_id: str
    email: str
    role: OrganizationRole
    expires_at: datetime
    accepted_at: datetime | None
    revoked_at: datetime | None
    created_at: datetime


class InvitationCreated(InvitationRead):
    acceptance_token: str


class InvitationAccept(BaseModel):
    token: str = Field(min_length=20, max_length=500)
    display_name: str | None = Field(default=None, min_length=2, max_length=200)


class UserActiveUpdate(BaseModel):
    active: bool


class VaultFileRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    organization_id: str
    uploaded_by_user_id: str
    folder_id: str | None
    site_id: str | None
    original_filename: str
    media_type: str
    byte_size: int
    access_scope: str
    deleted_at: datetime | None
    created_at: datetime


class VaultFileRename(BaseModel):
    name: str = Field(min_length=1, max_length=255)


class VaultFileAccessUpdate(BaseModel):
    access_scope: str = Field(pattern="^(organization|management|private)$")


class VaultShareCreate(BaseModel):
    expires_in_hours: int | None = Field(default=168, ge=1, le=8760)


class VaultShareRead(BaseModel):
    id: str
    url_token: str
    expires_at: datetime | None


class VaultFolderCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    site_id: str | None = None


class VaultFolderRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    name: str
    site_id: str | None
    access_scope: str
    deleted_at: datetime | None
    created_by_user_id: str
    created_at: datetime


class VaultSiteCreate(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    description: str | None = Field(default=None, max_length=500)


class VaultSiteRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    name: str
    description: str | None
    access_scope: str
    deleted_at: datetime | None
    created_by_user_id: str
    created_at: datetime


class VaultStorageRead(BaseModel):
    used_bytes: int
    quota_bytes: int
    available_bytes: int


class CustomerCreate(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    email: str | None = Field(default=None, max_length=320)
    phone: str | None = Field(default=None, max_length=40)
    address: str | None = Field(default=None, max_length=500)


class CustomerUpdate(CustomerCreate):
    pass


class CustomerRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    organization_id: str
    name: str
    email: str | None
    phone: str | None
    address: str | None
    created_at: datetime


class MaterialCreate(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    category: MaterialCategory
    description: str | None = Field(default=None, max_length=5000)


class MaterialRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    organization_id: str
    name: str
    category: MaterialCategory
    description: str | None
    active: bool
    created_at: datetime


class MaterialVariantCreate(BaseModel):
    material_id: str
    name: str = Field(min_length=2, max_length=200)
    colour: str | None = Field(default=None, max_length=100)
    unit: str = Field(min_length=1, max_length=30)
    default_waste_percent: Decimal = Field(default=Decimal("10.00"), ge=0, le=100)


class MaterialVariantRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    organization_id: str
    material_id: str
    name: str
    colour: str | None
    unit: str
    default_waste_percent: Decimal
    created_at: datetime


class DesignProjectCreate(BaseModel):
    property_id: str
    name: str = Field(min_length=2, max_length=200)
    goal: str | None = Field(default=None, max_length=5000)


class DesignProjectUpdate(DesignProjectCreate):
    pass


class DesignProjectRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    organization_id: str
    property_id: str
    name: str
    goal: str | None
    status: DesignStatus
    created_at: datetime


class SiteCaptureRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    organization_id: str
    design_project_id: str
    uploaded_by_user_id: str
    original_filename: str
    media_type: str
    byte_size: int
    width: int
    height: int
    sha256: str
    status: CaptureStatus
    created_at: datetime
    deleted_at: datetime | None


class QuoteItemWrite(BaseModel):
    description: str = Field(min_length=2, max_length=500)
    category: Literal["material", "labour", "equipment", "delivery", "other"] = "other"
    quantity: Decimal = Field(gt=0, le=1000000)
    unit: str = Field(default="unit", min_length=1, max_length=30)
    unit_price: Decimal = Field(ge=0, le=100000000)


class QuoteItemRead(QuoteItemWrite):
    model_config = ConfigDict(from_attributes=True)
    id: str
    line_total: Decimal
    position: int


class QuoteCreate(BaseModel):
    design_project_id: str
    generation_job_id: str | None = None
    title: str = Field(min_length=2, max_length=200)
    items: list[QuoteItemWrite] = Field(min_length=1, max_length=100)
    markup_rate: Decimal = Field(default=Decimal("0"), ge=0, le=100)
    discount_amount: Decimal = Field(default=Decimal("0"), ge=0, le=100000000)
    tax_rate: Decimal = Field(default=Decimal("0"), ge=0, le=100)
    currency: str = Field(default="CAD", min_length=3, max_length=3)
    assumptions: str | None = Field(default=None, max_length=5000)


class QuoteStatusUpdate(BaseModel):
    status: QuoteStatus


class QuoteRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    organization_id: str
    design_project_id: str
    generation_job_id: str | None
    number: str
    title: str
    status: QuoteStatus
    subtotal: Decimal
    markup_rate: Decimal
    markup_amount: Decimal
    discount_amount: Decimal
    tax_rate: Decimal
    tax_amount: Decimal
    total: Decimal
    currency: str
    assumptions: str | None
    items: list[QuoteItemRead]
    created_at: datetime
    updated_at: datetime


class InvoiceItemWrite(BaseModel):
    description: str = Field(min_length=2, max_length=500)
    quantity: Decimal = Field(gt=0, le=1000000)
    rate: Decimal = Field(ge=0, le=100000000)


class InvoiceItemRead(InvoiceItemWrite):
    model_config = ConfigDict(from_attributes=True)
    id: str
    line_total: Decimal
    position: int


class InvoiceCreate(BaseModel):
    number: str | None = Field(default=None, min_length=1, max_length=40)
    customer_id: str | None = None
    customer_name: str | None = Field(default=None, min_length=2, max_length=200)
    customer_email: str | None = Field(default=None, max_length=320)
    customer_phone: str | None = Field(default=None, max_length=40)
    customer_address: str | None = Field(default=None, max_length=500)
    company_email: str | None = Field(default=None, max_length=320)
    company_phone: str | None = Field(default=None, max_length=40)
    company_address: str | None = Field(default=None, max_length=500)
    gst_rate: Decimal = Field(default=Decimal("0"), ge=0, le=100)
    pst_rate: Decimal = Field(default=Decimal("0"), ge=0, le=100)
    items: list[InvoiceItemWrite] = Field(min_length=1, max_length=100)
    currency: str = Field(default="CAD", min_length=3, max_length=3)
    notes: str | None = Field(default=None, max_length=5000)


class InvoiceUpdate(InvoiceCreate):
    status: InvoiceStatus = InvoiceStatus.DRAFT


class InvoiceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    organization_id: str
    customer_id: str | None
    work_order_id: str | None
    number: str
    description: str
    quantity: Decimal
    rate: Decimal
    subtotal: Decimal
    currency: str
    status: InvoiceStatus
    notes: str | None
    customer_name: str | None
    customer_email: str | None
    customer_phone: str | None
    customer_address: str | None
    company_email: str | None
    company_phone: str | None
    company_address: str | None
    gst_rate: Decimal
    pst_rate: Decimal
    gst_amount: Decimal
    pst_amount: Decimal
    total: Decimal
    paid_amount: Decimal
    balance_due: Decimal
    items: list[InvoiceItemRead]
    payments: list["InvoicePaymentRead"]
    created_at: datetime
    updated_at: datetime


class InvoicePaymentCreate(BaseModel):
    amount: Decimal = Field(gt=0, le=100000000)
    method: Literal["cash", "card", "etransfer", "cheque", "bank", "other"]
    reference: str | None = Field(default=None, max_length=200)
    received_at: datetime | None = None


class InvoicePaymentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    invoice_id: str
    amount: Decimal
    method: str
    reference: str | None
    received_at: datetime
    created_at: datetime


class TimesheetStart(BaseModel):
    property_id: str | None = None
    notes: str | None = Field(default=None, max_length=2000)
    started_at: datetime | None = None


class TimesheetStop(BaseModel):
    ended_at: datetime | None = None


class TimesheetRead(BaseModel):
    id: str
    organization_id: str
    user_id: str
    employee_name: str
    property_id: str | None
    property_name: str | None
    started_at: datetime
    ended_at: datetime | None
    status: TimesheetStatus
    notes: str | None
    created_at: datetime


class GenerationJobRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    organization_id: str
    design_project_id: str
    capture_id: str
    prompt: str
    provider: str
    model_version: str
    status: str
    measurement_method: str | None
    selected_pixel_count: int | None
    total_pixel_count: int | None
    calibration_pixel_length: Decimal | None
    calibration_real_length: Decimal | None
    calibration_unit: str | None
    estimated_area: Decimal | None
    estimated_perimeter: Decimal | None
    measurement_confidence: str | None
    latency_ms: int | None
    estimated_cost_usd: Decimal | None
    error_message: str | None
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None


class GenerationMaterialEstimateCreate(BaseModel):
    material_type: Literal["sod", "pavers", "mulch", "gravel", "topsoil"]
    waste_percent: Decimal = Field(ge=0, le=50)
    depth: Decimal | None = Field(default=None, gt=0, le=36)
    unit_price: Decimal = Field(default=Decimal("0"), ge=0, le=100000)
    labour_rate: Decimal = Field(default=Decimal("0"), ge=0, le=10000)
    labour_hours: Decimal | None = Field(default=None, gt=0, le=100000)
    delivery_cost: Decimal = Field(default=Decimal("0"), ge=0, le=1000000)
    tax_rate: Decimal = Field(default=Decimal("0"), ge=0, le=100)


class GenerationMaterialEstimateRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    organization_id: str
    generation_job_id: str
    material_type: str
    measurement_unit: str
    measured_area: Decimal
    measured_perimeter: Decimal
    waste_percent: Decimal
    depth: Decimal | None
    order_quantity: Decimal
    material_unit: str
    edging_quantity: Decimal
    labour_hours: Decimal
    unit_price: Decimal
    labour_rate: Decimal
    delivery_cost: Decimal
    material_cost: Decimal
    labour_cost: Decimal
    subtotal: Decimal
    tax_rate: Decimal
    tax_amount: Decimal
    total: Decimal
    currency: str
    assumptions: list[str]
    created_at: datetime
    updated_at: datetime


class GenerationEvaluationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    organization_id: str
    generation_job_id: str
    evaluator_version: str
    dimensions_match: bool
    masked_change_ratio: Decimal
    protected_change_ratio: Decimal
    masked_change_threshold: Decimal
    protected_change_threshold: Decimal
    pixel_change_threshold: Decimal
    passed: bool
    failure_reasons: list[str]
    evaluation_latency_ms: int
    created_at: datetime


class GenerationReviewCreate(BaseModel):
    decision: Literal["approved", "rejected", "revision_requested"]
    notes: str | None = Field(default=None, max_length=2000)


class GenerationReviewRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    organization_id: str
    generation_job_id: str
    reviewer_user_id: str
    decision: str
    notes: str | None
    created_at: datetime


class GenerationFailureMetric(BaseModel):
    reason: str
    count: int


class GenerationModelMetric(BaseModel):
    model_version: str
    total: int
    evaluated: int
    passed: int
    pass_rate: float | None
    average_latency_ms: float | None
    estimated_cost_usd: Decimal


class GenerationTrendMetric(BaseModel):
    date: str
    total: int
    evaluated: int
    passed: int
    failed: int
    pass_rate: float | None


class GenerationReviewItem(BaseModel):
    job_id: str
    design_project_id: str
    prompt: str
    model_version: str
    created_at: datetime
    evaluation_id: str
    masked_change_ratio: Decimal
    protected_change_ratio: Decimal
    failure_reasons: list[str]
    latest_review_decision: str | None = None


class GenerationMetricsRead(BaseModel):
    total_generations: int
    completed_generations: int
    evaluated_generations: int
    passed_generations: int
    failed_evaluations: int
    unevaluated_generations: int
    pass_rate: float | None
    average_generation_latency_ms: float | None
    average_evaluation_latency_ms: float | None
    estimated_cost_usd: Decimal
    failure_reasons: list[GenerationFailureMetric]
    models: list[GenerationModelMetric]
    trends: list[GenerationTrendMetric]
    review_queue: list[GenerationReviewItem]


class SignedObjectUrlRead(BaseModel):
    url: str
    expires_in: int
