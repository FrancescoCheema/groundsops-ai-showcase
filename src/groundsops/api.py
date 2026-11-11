import hashlib
import secrets
import zipfile
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from io import BytesIO
from pathlib import Path
from typing import Annotated
from urllib.parse import quote
from uuid import uuid4

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    HTTPException,
    Response,
    UploadFile,
    status,
)
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from groundsops.auth import (
    AdminPrincipal,
    CurrentPrincipal,
    DesignerPrincipal,
    ManagerPrincipal,
    PlatformPrincipal,
    SignupIdentity,
    create_development_signup_token,
    create_development_token,
    ensure_development_auth,
)
from groundsops.config import get_settings
from groundsops.db import get_db
from groundsops.estimates import calculate_material_estimate
from groundsops.images import InvalidImage, normalize_edit_mask, sanitize_image
from groundsops.inference import process_generation_job
from groundsops.malware import MalwareDetected, MalwareScannerUnavailable, scan_bytes
from groundsops.models import (
    Customer,
    DesignProject,
    GenerationEvaluation,
    GenerationJob,
    GenerationMaterialEstimate,
    GenerationReview,
    GenerationStatus,
    Invoice,
    InvoiceItem,
    InvoicePayment,
    Material,
    MaterialVariant,
    Organization,
    OrganizationInvitation,
    OrganizationRole,
    OrganizationUser,
    Property,
    Quote,
    QuoteItem,
    QuoteStatus,
    SiteCapture,
    TimesheetEntry,
    VaultContainerShare,
    VaultFile,
    VaultFolder,
    VaultShare,
    VaultSite,
    WorkOrder,
    WorkOrderStatus,
)
from groundsops.schemas import (
    CurrentUserRead,
    CustomerCreate,
    CustomerRead,
    CustomerUpdate,
    DesignProjectCreate,
    DesignProjectRead,
    DesignProjectUpdate,
    DevelopmentBootstrapRequest,
    DevelopmentBootstrapResponse,
    DevelopmentSignupTokenRequest,
    DevelopmentTokenRequest,
    GenerationEvaluationRead,
    GenerationJobRead,
    GenerationMaterialEstimateCreate,
    GenerationMaterialEstimateRead,
    GenerationMetricsRead,
    GenerationReviewCreate,
    GenerationReviewRead,
    InvitationAccept,
    InvitationCreate,
    InvitationCreated,
    InvitationRead,
    InvoiceCreate,
    InvoicePaymentCreate,
    InvoicePaymentRead,
    InvoiceRead,
    InvoiceUpdate,
    MaterialCreate,
    MaterialRead,
    MaterialVariantCreate,
    MaterialVariantRead,
    OrganizationRead,
    OrganizationRegistrationCreate,
    OrganizationRegistrationRead,
    OrganizationUpdate,
    OrganizationUserCreate,
    OrganizationUserRead,
    PlatformOrganizationRead,
    PlatformUserRead,
    PlatformWorkspaceCreate,
    PlatformWorkspaceCreated,
    PropertyCreate,
    PropertyRead,
    PropertyUpdate,
    QuoteCreate,
    QuoteRead,
    QuoteStatusUpdate,
    QuoteWorkOrderCreate,
    SignedObjectUrlRead,
    SiteCaptureRead,
    TimesheetRead,
    TimesheetStart,
    TimesheetStop,
    TokenResponse,
    UserActiveUpdate,
    VaultFileAccessUpdate,
    VaultFileRead,
    VaultFileRename,
    VaultFolderCreate,
    VaultFolderRead,
    VaultShareCreate,
    VaultShareRead,
    VaultSiteCreate,
    VaultSiteRead,
    VaultStorageRead,
    WorkOrderCompletionCreate,
    WorkOrderCreate,
    WorkOrderRead,
    WorkOrderUpdate,
    WorkOrderVarianceRead,
)
from groundsops.storage import get_object_storage, tenant_storage_key

router = APIRouter(prefix="/api/v1")
DbSession = Annotated[Session, Depends(get_db)]


@router.get("/auth/me", response_model=CurrentUserRead)
def current_user(principal: CurrentPrincipal) -> dict:
    return {
        "id": principal.user_id,
        "organization_id": principal.organization_id,
        "email": principal.email,
        "role": principal.role,
        "platform_admin": principal.platform_admin,
    }


@router.get("/vault/files", response_model=list[VaultFileRead])
def list_vault_files(
    principal: CurrentPrincipal,
    db: DbSession,
    recycle_bin: bool = False,
    folder_id: str | None = None,
    site_id: str | None = None,
) -> list[VaultFile]:
    manager = principal.role in {OrganizationRole.ADMIN, OrganizationRole.MANAGER}
    query = (
        select(VaultFile)
        .where(
            VaultFile.organization_id == principal.organization_id,
            VaultFile.deleted_at.is_not(None) if recycle_bin else VaultFile.deleted_at.is_(None),
        )
        .order_by(VaultFile.created_at.desc())
    )
    if not manager:
        query = query.where(
            or_(
                VaultFile.access_scope == "organization",
                VaultFile.uploaded_by_user_id == principal.user_id,
            )
        )
    if folder_id:
        query = query.where(VaultFile.folder_id == folder_id)
    elif site_id:
        query = query.where(
            VaultFile.site_id == site_id,
            VaultFile.folder_id.is_(None),
        )
    else:
        query = query.where(VaultFile.folder_id.is_(None), VaultFile.site_id.is_(None))
    return list(db.scalars(query))


@router.get("/vault/storage", response_model=VaultStorageRead)
def vault_storage(principal: CurrentPrincipal, db: DbSession) -> dict:
    used = db.scalar(
        select(func.coalesce(func.sum(VaultFile.byte_size), 0)).where(
            VaultFile.organization_id == principal.organization_id,
            VaultFile.deleted_at.is_(None),
        )
    )
    quota = get_settings().vault_quota_bytes
    return {
        "used_bytes": int(used or 0),
        "quota_bytes": quota,
        "available_bytes": max(0, quota - int(used or 0)),
    }


@router.get("/vault/folders", response_model=list[VaultFolderRead])
def list_vault_folders(
    principal: CurrentPrincipal,
    db: DbSession,
    site_id: str | None = None,
    recycle_bin: bool = False,
) -> list[VaultFolder]:
    query = select(VaultFolder).where(
        VaultFolder.organization_id == principal.organization_id,
        VaultFolder.site_id == site_id if site_id else VaultFolder.site_id.is_(None),
        VaultFolder.deleted_at.is_not(None) if recycle_bin else VaultFolder.deleted_at.is_(None),
    )
    if principal.role not in {OrganizationRole.ADMIN, OrganizationRole.MANAGER}:
        query = query.where(
            or_(
                VaultFolder.access_scope == "organization",
                VaultFolder.created_by_user_id == principal.user_id,
            )
        )
    return list(db.scalars(query.order_by(VaultFolder.name)))


@router.post(
    "/vault/folders",
    response_model=VaultFolderRead,
    status_code=status.HTTP_201_CREATED,
)
def create_vault_folder(
    payload: VaultFolderCreate,
    principal: CurrentPrincipal,
    db: DbSession,
) -> VaultFolder:
    if payload.site_id:
        site = db.scalar(
            select(VaultSite).where(
                VaultSite.id == payload.site_id,
                VaultSite.organization_id == principal.organization_id,
            )
        )
        if site is None:
            raise HTTPException(status_code=404, detail="Site not found")
    folder = VaultFolder(
        organization_id=principal.organization_id,
        created_by_user_id=principal.user_id,
        name=payload.name.strip(),
        site_id=payload.site_id,
    )
    db.add(folder)
    db.commit()
    db.refresh(folder)
    return folder


@router.get("/vault/sites", response_model=list[VaultSiteRead])
def list_vault_sites(
    principal: CurrentPrincipal, db: DbSession, recycle_bin: bool = False
) -> list[VaultSite]:
    query = select(VaultSite).where(
        VaultSite.organization_id == principal.organization_id,
        VaultSite.deleted_at.is_not(None) if recycle_bin else VaultSite.deleted_at.is_(None),
    )
    if principal.role not in {OrganizationRole.ADMIN, OrganizationRole.MANAGER}:
        query = query.where(
            or_(
                VaultSite.access_scope == "organization",
                VaultSite.created_by_user_id == principal.user_id,
            )
        )
    return list(db.scalars(query.order_by(VaultSite.name)))


@router.post(
    "/vault/sites",
    response_model=VaultSiteRead,
    status_code=status.HTTP_201_CREATED,
)
def create_vault_site(
    payload: VaultSiteCreate,
    principal: ManagerPrincipal,
    db: DbSession,
) -> VaultSite:
    site = VaultSite(
        organization_id=principal.organization_id,
        created_by_user_id=principal.user_id,
        name=payload.name.strip(),
        description=payload.description,
    )
    db.add(site)
    db.commit()
    db.refresh(site)
    return site


def _vault_container(
    kind: str, container_id: str, principal: CurrentPrincipal, db: Session
) -> VaultFolder | VaultSite:
    model = VaultFolder if kind == "folders" else VaultSite
    record = db.scalar(
        select(model).where(
            model.id == container_id,
            model.organization_id == principal.organization_id,
        )
    )
    if record is None:
        raise HTTPException(status_code=404, detail="Container not found")
    manager = principal.role in {OrganizationRole.ADMIN, OrganizationRole.MANAGER}
    if (
        not manager
        and record.created_by_user_id != principal.user_id
        and record.access_scope != "organization"
    ):
        raise HTTPException(status_code=404, detail="Container not found")
    return record


def _container_zip(kind: str, container_id: str, db: Session) -> bytes:
    condition = (
        VaultFile.folder_id == container_id
        if kind == "folders"
        else VaultFile.site_id == container_id
    )
    files = db.scalars(select(VaultFile).where(condition, VaultFile.deleted_at.is_(None)))
    output = BytesIO()
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        for record in files:
            archive.writestr(
                f"{record.id[:8]}-{record.original_filename}",
                get_object_storage().get(record.storage_key),
            )
    return output.getvalue()


@router.put("/vault/containers/{kind}/{container_id}/name")
def rename_vault_container(
    kind: str,
    container_id: str,
    payload: VaultFileRename,
    principal: ManagerPrincipal,
    db: DbSession,
) -> dict:
    if kind not in {"folders", "sites"}:
        raise HTTPException(status_code=404, detail="Container not found")
    record = _vault_container(kind, container_id, principal, db)
    record.name = payload.name.strip()
    db.commit()
    return {"id": record.id, "name": record.name}


@router.put("/vault/containers/{kind}/{container_id}/access")
def update_vault_container_access(
    kind: str,
    container_id: str,
    payload: VaultFileAccessUpdate,
    principal: ManagerPrincipal,
    db: DbSession,
) -> dict:
    if kind not in {"folders", "sites"}:
        raise HTTPException(status_code=404, detail="Container not found")
    record = _vault_container(kind, container_id, principal, db)
    record.access_scope = payload.access_scope
    db.commit()
    return {"id": record.id, "access_scope": record.access_scope}


@router.get("/vault/containers/{kind}/{container_id}/download", response_class=Response)
def download_vault_container(
    kind: str, container_id: str, principal: CurrentPrincipal, db: DbSession
) -> Response:
    if kind not in {"folders", "sites"}:
        raise HTTPException(status_code=404, detail="Container not found")
    record = _vault_container(kind, container_id, principal, db)
    return Response(
        content=_container_zip(kind, container_id, db),
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(record.name)}.zip"},
    )


@router.post("/vault/containers/{kind}/{container_id}/shares", response_model=VaultShareRead)
def share_vault_container(
    kind: str,
    container_id: str,
    payload: VaultShareCreate,
    principal: ManagerPrincipal,
    db: DbSession,
) -> dict:
    if kind not in {"folders", "sites"}:
        raise HTTPException(status_code=404, detail="Container not found")
    _vault_container(kind, container_id, principal, db)
    token = secrets.token_urlsafe(32)
    expires_at = datetime.now(UTC) + timedelta(hours=payload.expires_in_hours or 168)
    share = VaultContainerShare(
        organization_id=principal.organization_id,
        created_by_user_id=principal.user_id,
        container_type=kind,
        container_id=container_id,
        token_hash=hashlib.sha256(token.encode()).hexdigest(),
        expires_at=expires_at,
    )
    db.add(share)
    db.commit()
    db.refresh(share)
    return {"id": share.id, "url_token": token, "expires_at": expires_at}


@router.get("/vault/shared-container/{token}", response_class=Response)
def open_shared_container(token: str, db: DbSession) -> Response:
    share = db.scalar(
        select(VaultContainerShare).where(
            VaultContainerShare.token_hash == hashlib.sha256(token.encode()).hexdigest(),
            VaultContainerShare.expires_at > datetime.now(UTC),
        )
    )
    if share is None:
        raise HTTPException(status_code=404, detail="Share link not found or expired")
    model = VaultFolder if share.container_type == "folders" else VaultSite
    container = db.scalar(
        select(model).where(model.id == share.container_id, model.deleted_at.is_(None))
    )
    if container is None:
        raise HTTPException(status_code=404, detail="Share link not found or expired")
    return Response(
        content=_container_zip(share.container_type, share.container_id, db),
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=shared-files.zip"},
    )


@router.delete(
    "/vault/containers/{kind}/{container_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def recycle_vault_container(
    kind: str,
    container_id: str,
    principal: ManagerPrincipal,
    db: DbSession,
) -> Response:
    if kind not in {"folders", "sites"}:
        raise HTTPException(status_code=404, detail="Container not found")
    record = _vault_container(kind, container_id, principal, db)
    record.deleted_at = datetime.now(UTC)
    condition = (
        VaultFile.folder_id == container_id
        if kind == "folders"
        else VaultFile.site_id == container_id
    )
    for file_record in db.scalars(select(VaultFile).where(condition)):
        file_record.deleted_at = record.deleted_at
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/vault/containers/{kind}/{container_id}/restore",
    status_code=status.HTTP_204_NO_CONTENT,
)
def restore_vault_container(
    kind: str,
    container_id: str,
    principal: ManagerPrincipal,
    db: DbSession,
) -> Response:
    if kind not in {"folders", "sites"}:
        raise HTTPException(status_code=404, detail="Container not found")
    record = _vault_container(kind, container_id, principal, db)
    record.deleted_at = None
    condition = (
        VaultFile.folder_id == container_id
        if kind == "folders"
        else VaultFile.site_id == container_id
    )
    for file_record in db.scalars(select(VaultFile).where(condition)):
        file_record.deleted_at = None
    if kind == "sites":
        for folder in db.scalars(select(VaultFolder).where(VaultFolder.site_id == container_id)):
            folder.deleted_at = None
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete(
    "/vault/containers/{kind}/{container_id}/permanent",
    status_code=status.HTTP_204_NO_CONTENT,
)
def permanently_delete_vault_container(
    kind: str,
    container_id: str,
    principal: ManagerPrincipal,
    db: DbSession,
) -> Response:
    if kind not in {"folders", "sites"}:
        raise HTTPException(status_code=404, detail="Container not found")
    record = _vault_container(kind, container_id, principal, db)
    if record.deleted_at is None:
        raise HTTPException(status_code=409, detail="Move the container to recycle bin first")
    condition = (
        VaultFile.folder_id == container_id
        if kind == "folders"
        else VaultFile.site_id == container_id
    )
    storage = get_object_storage()
    for file_record in db.scalars(select(VaultFile).where(condition)):
        storage.delete(file_record.storage_key)
        db.delete(file_record)
    if kind == "sites":
        for folder in db.scalars(select(VaultFolder).where(VaultFolder.site_id == container_id)):
            db.delete(folder)
    for share in db.scalars(
        select(VaultContainerShare).where(
            VaultContainerShare.container_type == kind,
            VaultContainerShare.container_id == container_id,
        )
    ):
        db.delete(share)
    db.delete(record)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/vault/files", response_model=VaultFileRead, status_code=status.HTTP_201_CREATED)
async def upload_vault_file(
    principal: CurrentPrincipal,
    db: DbSession,
    file: Annotated[UploadFile, File()],
    folder_id: Annotated[str | None, Form()] = None,
    site_id: Annotated[str | None, Form()] = None,
) -> VaultFile:
    settings = get_settings()
    raw = await file.read(settings.vault_max_bytes + 1)
    await file.close()
    if not raw or len(raw) > settings.vault_max_bytes:
        raise HTTPException(status_code=413, detail="File is empty or exceeds 25 MB")
    safe_name = Path(file.filename or "file").name[:255]
    try:
        scan_bytes(raw, safe_name, settings)
    except MalwareDetected as exc:
        raise HTTPException(status_code=422, detail="Uploaded file was rejected") from exc
    except MalwareScannerUnavailable as exc:
        raise HTTPException(
            status_code=503, detail="File scanning is temporarily unavailable"
        ) from exc
    file_id = str(uuid4())
    key = tenant_storage_key(principal.organization_id, "vault", file_id, safe_name)
    if folder_id:
        folder = db.scalar(
            select(VaultFolder).where(
                VaultFolder.id == folder_id,
                VaultFolder.organization_id == principal.organization_id,
            )
        )
        if folder is None:
            raise HTTPException(status_code=404, detail="Folder not found")
    if site_id:
        site = db.scalar(
            select(VaultSite).where(
                VaultSite.id == site_id,
                VaultSite.organization_id == principal.organization_id,
            )
        )
        if site is None:
            raise HTTPException(status_code=404, detail="Site not found")
    get_object_storage().put(key, raw, file.content_type)
    record = VaultFile(
        id=file_id,
        organization_id=principal.organization_id,
        uploaded_by_user_id=principal.user_id,
        folder_id=folder_id,
        site_id=site_id,
        original_filename=safe_name,
        media_type=file.content_type or "application/octet-stream",
        byte_size=len(raw),
        storage_key=key,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def _vault_record(
    file_id: str,
    principal: CurrentPrincipal,
    db: Session,
    include_deleted: bool = False,
) -> VaultFile:
    filters = [
        VaultFile.id == file_id,
        VaultFile.organization_id == principal.organization_id,
    ]
    if not include_deleted:
        filters.append(VaultFile.deleted_at.is_(None))
    record = db.scalar(select(VaultFile).where(*filters))
    if record is None:
        raise HTTPException(status_code=404, detail="File not found")
    manager = principal.role in {OrganizationRole.ADMIN, OrganizationRole.MANAGER}
    restricted = record.access_scope in {"private", "management"}
    if restricted and record.uploaded_by_user_id != principal.user_id and not manager:
        raise HTTPException(status_code=404, detail="File not found")
    return record


def _require_vault_manager(record: VaultFile, principal: CurrentPrincipal) -> None:
    manager = principal.role in {OrganizationRole.ADMIN, OrganizationRole.MANAGER}
    if record.uploaded_by_user_id != principal.user_id and not manager:
        raise HTTPException(status_code=403, detail="Insufficient permission")


def _vault_content_response(record: VaultFile, inline: bool) -> Response:
    content = get_object_storage().get(record.storage_key)
    safe_preview = record.media_type in {"application/pdf", "text/plain"} or (
        record.media_type.startswith("image/") and record.media_type != "image/svg+xml"
    )
    disposition = "inline" if inline and safe_preview else "attachment"
    return Response(
        content=content,
        media_type=record.media_type,
        headers={
            "Content-Disposition": (
                f"{disposition}; filename*=UTF-8''{quote(record.original_filename)}"
            ),
            "Content-Security-Policy": "default-src 'none'; img-src 'self' data:",
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.get("/vault/files/{file_id}/content", response_class=Response)
def download_vault_file(
    file_id: str,
    principal: CurrentPrincipal,
    db: DbSession,
    preview: bool = False,
) -> Response:
    return _vault_content_response(_vault_record(file_id, principal, db), preview)


@router.get("/vault/files/{file_id}/signed-url", response_model=SignedObjectUrlRead)
def get_vault_file_signed_url(
    file_id: str,
    principal: CurrentPrincipal,
    db: DbSession,
    response: Response,
    preview: bool = False,
) -> dict:
    record = _vault_record(file_id, principal, db)
    settings = get_settings()
    url = get_object_storage().signed_get_url(
        record.storage_key,
        filename=record.original_filename,
        content_type=record.media_type,
        inline=preview,
    )
    if url is None:
        raise HTTPException(
            status_code=409,
            detail="Signed URLs are available when S3 storage is enabled",
        )
    response.headers["Cache-Control"] = "private, no-store"
    return {"url": url, "expires_in": settings.storage_signed_url_ttl_seconds}


@router.put("/vault/files/{file_id}/name", response_model=VaultFileRead)
def rename_vault_file(
    file_id: str,
    payload: VaultFileRename,
    principal: CurrentPrincipal,
    db: DbSession,
) -> VaultFile:
    record = _vault_record(file_id, principal, db)
    _require_vault_manager(record, principal)
    safe_name = payload.name.replace("\\", "/").split("/")[-1].strip()
    if safe_name in {"", ".", ".."}:
        raise HTTPException(status_code=422, detail="Invalid file name")
    record.original_filename = safe_name
    db.commit()
    db.refresh(record)
    return record


@router.put("/vault/files/{file_id}/access", response_model=VaultFileRead)
def change_vault_access(
    file_id: str,
    payload: VaultFileAccessUpdate,
    principal: CurrentPrincipal,
    db: DbSession,
) -> VaultFile:
    record = _vault_record(file_id, principal, db)
    _require_vault_manager(record, principal)
    record.access_scope = payload.access_scope
    db.commit()
    db.refresh(record)
    return record


@router.post("/vault/files/{file_id}/shares", response_model=VaultShareRead)
def create_vault_share(
    file_id: str,
    payload: VaultShareCreate,
    principal: CurrentPrincipal,
    db: DbSession,
) -> dict:
    record = _vault_record(file_id, principal, db)
    _require_vault_manager(record, principal)
    raw_token = secrets.token_urlsafe(32)
    expires_at = (
        datetime.now(UTC) + timedelta(hours=payload.expires_in_hours)
        if payload.expires_in_hours
        else None
    )
    share = VaultShare(
        file_id=record.id,
        organization_id=principal.organization_id,
        created_by_user_id=principal.user_id,
        token_hash=hashlib.sha256(raw_token.encode()).hexdigest(),
        expires_at=expires_at,
    )
    db.add(share)
    db.commit()
    db.refresh(share)
    return {"id": share.id, "url_token": raw_token, "expires_at": expires_at}


@router.get("/vault/shared/{token}", response_class=Response)
def open_vault_share(token: str, db: DbSession) -> Response:
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    now = datetime.now(UTC)
    share = db.scalar(
        select(VaultShare).where(
            VaultShare.token_hash == token_hash,
            VaultShare.revoked_at.is_(None),
            or_(VaultShare.expires_at.is_(None), VaultShare.expires_at > now),
        )
    )
    if share is None:
        raise HTTPException(status_code=404, detail="Share link not found or expired")
    record = db.get(VaultFile, share.file_id)
    if record is None or record.deleted_at is not None:
        raise HTTPException(status_code=404, detail="File not found")
    return _vault_content_response(record, inline=True)


@router.delete("/vault/files/{file_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_vault_file(file_id: str, principal: CurrentPrincipal, db: DbSession) -> Response:
    record = _vault_record(file_id, principal, db)
    _require_vault_manager(record, principal)
    record.deleted_at = datetime.now(UTC)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/vault/files/{file_id}/restore", response_model=VaultFileRead)
def restore_vault_file(file_id: str, principal: CurrentPrincipal, db: DbSession) -> VaultFile:
    record = _vault_record(file_id, principal, db, include_deleted=True)
    _require_vault_manager(record, principal)
    record.deleted_at = None
    db.commit()
    db.refresh(record)
    return record


@router.delete("/vault/files/{file_id}/permanent", status_code=status.HTTP_204_NO_CONTENT)
def permanently_delete_vault_file(
    file_id: str, principal: CurrentPrincipal, db: DbSession
) -> Response:
    record = _vault_record(file_id, principal, db, include_deleted=True)
    _require_vault_manager(record, principal)
    if record.deleted_at is None:
        raise HTTPException(status_code=409, detail="Move the file to recycle bin first")
    get_object_storage().delete(record.storage_key)
    db.delete(record)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def _cascade_delete_design(design: DesignProject, db: Session) -> None:
    storage = get_object_storage()
    jobs = list(
        db.scalars(select(GenerationJob).where(GenerationJob.design_project_id == design.id))
    )
    for job in jobs:
        storage.delete(job.mask_storage_key)
        if job.output_storage_key:
            storage.delete(job.output_storage_key)
        db.delete(job)
    captures = list(
        db.scalars(select(SiteCapture).where(SiteCapture.design_project_id == design.id))
    )
    for capture in captures:
        storage.delete(capture.storage_key)
        db.delete(capture)
    for quote_record in db.scalars(select(Quote).where(Quote.design_project_id == design.id)):
        db.delete(quote_record)
    db.delete(design)


def _cascade_delete_property(property_record: Property, db: Session) -> None:
    for entry in db.scalars(
        select(TimesheetEntry).where(TimesheetEntry.property_id == property_record.id)
    ):
        entry.property_id = None
    for work_order in db.scalars(
        select(WorkOrder).where(WorkOrder.property_id == property_record.id)
    ):
        db.delete(work_order)
    designs = list(
        db.scalars(select(DesignProject).where(DesignProject.property_id == property_record.id))
    )
    for design in designs:
        _cascade_delete_design(design, db)
    db.delete(property_record)


@router.get("/organization", response_model=OrganizationRead)
def get_current_organization(principal: CurrentPrincipal, db: DbSession) -> Organization:
    organization = db.scalar(
        select(Organization).where(Organization.id == principal.organization_id)
    )
    if organization is None:
        raise HTTPException(status_code=404, detail="Organization not found")
    return organization


@router.put("/organization", response_model=OrganizationRead)
def update_current_organization(
    payload: OrganizationUpdate, principal: ManagerPrincipal, db: DbSession
) -> Organization:
    organization = db.scalar(
        select(Organization).where(Organization.id == principal.organization_id)
    )
    if organization is None:
        raise HTTPException(status_code=404, detail="Organization not found")
    organization.name = payload.name
    db.commit()
    db.refresh(organization)
    return organization


@router.post("/organization/logo", response_model=OrganizationRead)
async def upload_organization_logo(
    principal: ManagerPrincipal,
    db: DbSession,
    file: Annotated[UploadFile, File(description="JPEG, PNG or WebP company logo")],
) -> Organization:
    organization = db.scalar(
        select(Organization).where(Organization.id == principal.organization_id)
    )
    if organization is None:
        raise HTTPException(status_code=404, detail="Organization not found")
    settings = get_settings()
    raw = await file.read(settings.image_max_bytes + 1)
    await file.close()
    if len(raw) > settings.image_max_bytes:
        raise HTTPException(status_code=413, detail="Logo exceeds maximum size")
    try:
        image = sanitize_image(raw, settings.image_max_pixels)
    except InvalidImage as exc:
        raise HTTPException(status_code=415, detail=str(exc)) from exc
    key = tenant_storage_key(
        principal.organization_id,
        "branding",
        "company-logo",
        f"logo.{image.extension}",
    )
    storage = get_object_storage()
    old_key = organization.logo_storage_key
    storage.put(key, image.data, image.media_type)
    organization.logo_storage_key = key
    organization.logo_media_type = image.media_type
    try:
        db.commit()
        db.refresh(organization)
    except Exception:
        db.rollback()
        raise
    if old_key and old_key != key:
        storage.delete(old_key)
    return organization


@router.get("/organization/logo/content", response_class=Response)
def get_organization_logo(principal: CurrentPrincipal, db: DbSession) -> Response:
    organization = db.scalar(
        select(Organization).where(Organization.id == principal.organization_id)
    )
    if organization is None or not organization.logo_storage_key:
        raise HTTPException(status_code=404, detail="Company logo not found")
    try:
        content = get_object_storage().get(organization.logo_storage_key)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Company logo not found") from exc
    return Response(content=content, media_type=organization.logo_media_type)


@router.post("/organization/invoice-logo", response_model=OrganizationRead)
async def upload_invoice_logo(
    principal: ManagerPrincipal,
    db: DbSession,
    file: Annotated[UploadFile, File(description="Cropped invoice logo")],
) -> Organization:
    organization = db.scalar(
        select(Organization).where(Organization.id == principal.organization_id)
    )
    if organization is None:
        raise HTTPException(status_code=404, detail="Organization not found")
    settings = get_settings()
    raw = await file.read(settings.image_max_bytes + 1)
    await file.close()
    if len(raw) > settings.image_max_bytes:
        raise HTTPException(status_code=413, detail="Logo exceeds maximum size")
    try:
        image = sanitize_image(raw, settings.image_max_pixels)
    except InvalidImage as exc:
        raise HTTPException(status_code=415, detail=str(exc)) from exc
    key = tenant_storage_key(
        principal.organization_id,
        "branding",
        "invoice-logo",
        f"logo.{image.extension}",
    )
    storage = get_object_storage()
    old_key = organization.invoice_logo_storage_key
    storage.put(key, image.data, image.media_type)
    organization.invoice_logo_storage_key = key
    organization.invoice_logo_media_type = image.media_type
    try:
        db.commit()
        db.refresh(organization)
    except Exception:
        db.rollback()
        raise
    if old_key and old_key != key:
        storage.delete(old_key)
    return organization


@router.get("/organization/invoice-logo/content", response_class=Response)
def get_invoice_logo(principal: CurrentPrincipal, db: DbSession) -> Response:
    organization = db.scalar(
        select(Organization).where(Organization.id == principal.organization_id)
    )
    if organization is None or not organization.invoice_logo_storage_key:
        raise HTTPException(status_code=404, detail="Invoice logo not found")
    try:
        content = get_object_storage().get(organization.invoice_logo_storage_key)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Invoice logo not found") from exc
    return Response(content=content, media_type=organization.invoice_logo_media_type)


@router.post(
    "/auth/development-bootstrap",
    response_model=DevelopmentBootstrapResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(ensure_development_auth)],
)
def bootstrap_development_tenant(
    payload: DevelopmentBootstrapRequest, db: DbSession
) -> DevelopmentBootstrapResponse:
    organization = Organization(name=payload.organization_name)
    db.add(organization)
    db.flush()
    user = OrganizationUser(
        organization_id=organization.id,
        email=payload.admin_email.lower(),
        display_name=payload.admin_display_name,
        role="admin",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    token, expires_in = create_development_token(user)
    return DevelopmentBootstrapResponse(
        organization_id=organization.id,
        user_id=user.id,
        access_token=token,
        expires_in=expires_in,
    )


@router.post(
    "/auth/development-token",
    response_model=TokenResponse,
    dependencies=[Depends(ensure_development_auth)],
)
def issue_development_token(payload: DevelopmentTokenRequest, db: DbSession) -> TokenResponse:
    user = db.scalar(
        select(OrganizationUser).where(
            OrganizationUser.organization_id == payload.organization_id,
            OrganizationUser.email == payload.email.lower(),
            OrganizationUser.active.is_(True),
        )
    )
    if user is None:
        raise HTTPException(status_code=404, detail="Active user not found")
    token, expires_in = create_development_token(user)
    return TokenResponse(access_token=token, expires_in=expires_in)


@router.post(
    "/auth/development-signup-token",
    response_model=TokenResponse,
    dependencies=[Depends(ensure_development_auth)],
)
def issue_development_signup_token(
    payload: DevelopmentSignupTokenRequest,
) -> TokenResponse:
    token, expires_in = create_development_signup_token(payload.email.lower(), payload.display_name)
    return TokenResponse(access_token=token, expires_in=expires_in)


@router.post(
    "/onboarding/register",
    response_model=OrganizationRegistrationRead,
    status_code=status.HTTP_201_CREATED,
)
def register_organization(
    payload: OrganizationRegistrationCreate,
    identity: SignupIdentity,
    db: DbSession,
) -> dict:
    if not get_settings().self_service_signup_enabled:
        raise HTTPException(
            status_code=403,
            detail="New workspaces are set up by invitation. Contact GroundsOps to get started.",
        )
    existing = db.scalar(
        select(OrganizationUser).where(
            or_(
                OrganizationUser.cognito_subject == identity.subject,
                OrganizationUser.email == identity.email,
            )
        )
    )
    if existing is not None:
        raise HTTPException(
            status_code=409,
            detail="This identity already belongs to an organization",
        )
    organization = Organization(name=payload.organization_name.strip())
    db.add(organization)
    db.flush()
    user = OrganizationUser(
        organization_id=organization.id,
        email=identity.email,
        cognito_subject=identity.subject,
        display_name=(payload.display_name or identity.display_name).strip(),
        role=OrganizationRole.ADMIN.value,
    )
    db.add(user)
    db.commit()
    db.refresh(organization)
    db.refresh(user)
    return {"organization": organization, "user": user}


@router.get("/invitations", response_model=list[InvitationRead])
def list_invitations(principal: AdminPrincipal, db: DbSession) -> list[OrganizationInvitation]:
    return list(
        db.scalars(
            select(OrganizationInvitation)
            .where(OrganizationInvitation.organization_id == principal.organization_id)
            .order_by(OrganizationInvitation.created_at.desc())
        )
    )


@router.post(
    "/invitations",
    response_model=InvitationCreated,
    status_code=status.HTTP_201_CREATED,
)
def create_invitation(
    payload: InvitationCreate,
    principal: AdminPrincipal,
    db: DbSession,
) -> dict:
    email = payload.email.lower().strip()
    existing_user = db.scalar(
        select(OrganizationUser).where(
            OrganizationUser.organization_id == principal.organization_id,
            OrganizationUser.email == email,
        )
    )
    if existing_user is not None:
        raise HTTPException(status_code=409, detail="User already belongs to this organization")
    active_invite = db.scalar(
        select(OrganizationInvitation).where(
            OrganizationInvitation.organization_id == principal.organization_id,
            OrganizationInvitation.email == email,
            OrganizationInvitation.accepted_at.is_(None),
            OrganizationInvitation.revoked_at.is_(None),
            OrganizationInvitation.expires_at > datetime.now(UTC),
        )
    )
    if active_invite is not None:
        raise HTTPException(status_code=409, detail="An active invitation already exists")
    token = secrets.token_urlsafe(32)
    invitation = OrganizationInvitation(
        organization_id=principal.organization_id,
        invited_by_user_id=principal.user_id,
        email=email,
        role=payload.role.value,
        token_hash=hashlib.sha256(token.encode()).hexdigest(),
        expires_at=datetime.now(UTC) + timedelta(days=payload.expires_in_days),
    )
    db.add(invitation)
    db.commit()
    db.refresh(invitation)
    result = InvitationRead.model_validate(invitation).model_dump()
    result["acceptance_token"] = token
    return result


@router.post(
    "/invitations/accept",
    response_model=OrganizationUserRead,
    status_code=status.HTTP_201_CREATED,
)
def accept_invitation(
    payload: InvitationAccept,
    identity: SignupIdentity,
    db: DbSession,
) -> OrganizationUser:
    invitation = db.scalar(
        select(OrganizationInvitation).where(
            OrganizationInvitation.token_hash == hashlib.sha256(payload.token.encode()).hexdigest(),
            OrganizationInvitation.accepted_at.is_(None),
            OrganizationInvitation.revoked_at.is_(None),
            OrganizationInvitation.expires_at > datetime.now(UTC),
        )
    )
    if invitation is None:
        raise HTTPException(status_code=404, detail="Invitation not found or expired")
    if invitation.email != identity.email:
        raise HTTPException(status_code=403, detail="Invitation belongs to another email")
    existing = db.scalar(
        select(OrganizationUser).where(
            or_(
                OrganizationUser.cognito_subject == identity.subject,
                OrganizationUser.email == identity.email,
            )
        )
    )
    if existing is not None:
        raise HTTPException(status_code=409, detail="Identity already has a membership")
    user = OrganizationUser(
        organization_id=invitation.organization_id,
        email=identity.email,
        cognito_subject=identity.subject,
        display_name=(payload.display_name or identity.display_name).strip(),
        role=invitation.role,
    )
    invitation.accepted_at = datetime.now(UTC)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.delete(
    "/invitations/{invitation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def revoke_invitation(
    invitation_id: str,
    principal: AdminPrincipal,
    db: DbSession,
) -> Response:
    invitation = db.scalar(
        select(OrganizationInvitation).where(
            OrganizationInvitation.id == invitation_id,
            OrganizationInvitation.organization_id == principal.organization_id,
        )
    )
    if invitation is None:
        raise HTTPException(status_code=404, detail="Invitation not found")
    if invitation.accepted_at is not None:
        raise HTTPException(status_code=409, detail="Accepted invitations cannot be revoked")
    invitation.revoked_at = datetime.now(UTC)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/properties", response_model=PropertyRead, status_code=status.HTTP_201_CREATED)
def create_property(
    payload: PropertyCreate, principal: ManagerPrincipal, db: DbSession
) -> Property:
    organization_id = principal.organization_id
    if db.get(Organization, organization_id) is None:
        raise HTTPException(status_code=404, detail="Organization not found")
    if payload.customer_id is not None:
        customer = db.scalar(
            select(Customer).where(
                Customer.id == payload.customer_id,
                Customer.organization_id == organization_id,
            )
        )
        if customer is None:
            raise HTTPException(status_code=404, detail="Customer not found")
    property_record = Property(organization_id=organization_id, **payload.model_dump())
    db.add(property_record)
    db.commit()
    db.refresh(property_record)
    return property_record


@router.get("/properties", response_model=list[PropertyRead])
def list_properties(principal: CurrentPrincipal, db: DbSession) -> list[Property]:
    organization_id = principal.organization_id
    statement = select(Property).where(Property.organization_id == organization_id)
    return list(db.scalars(statement))


@router.put("/properties/{property_id}", response_model=PropertyRead)
def update_property(
    property_id: str,
    payload: PropertyUpdate,
    principal: ManagerPrincipal,
    db: DbSession,
) -> Property:
    property_record = db.scalar(
        select(Property).where(
            Property.id == property_id,
            Property.organization_id == principal.organization_id,
        )
    )
    if property_record is None:
        raise HTTPException(status_code=404, detail="Property not found")
    if payload.customer_id:
        customer = db.scalar(
            select(Customer).where(
                Customer.id == payload.customer_id,
                Customer.organization_id == principal.organization_id,
            )
        )
        if customer is None:
            raise HTTPException(status_code=404, detail="Customer not found")
    for field, value in payload.model_dump().items():
        setattr(property_record, field, value)
    db.commit()
    db.refresh(property_record)
    return property_record


@router.delete("/properties/{property_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_property(property_id: str, principal: ManagerPrincipal, db: DbSession) -> Response:
    property_record = db.scalar(
        select(Property).where(
            Property.id == property_id,
            Property.organization_id == principal.organization_id,
        )
    )
    if property_record is None:
        raise HTTPException(status_code=404, detail="Property not found")
    _cascade_delete_property(property_record, db)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/work-orders", response_model=WorkOrderRead, status_code=status.HTTP_201_CREATED)
def create_work_order(
    payload: WorkOrderCreate, principal: ManagerPrincipal, db: DbSession
) -> WorkOrder:
    organization_id = principal.organization_id
    property_record = db.scalar(
        select(Property).where(
            Property.id == payload.property_id,
            Property.organization_id == organization_id,
        )
    )
    if property_record is None:
        raise HTTPException(status_code=404, detail="Property not found")
    if payload.assigned_user_id:
        assignee = db.scalar(
            select(OrganizationUser).where(
                OrganizationUser.id == payload.assigned_user_id,
                OrganizationUser.organization_id == organization_id,
                OrganizationUser.active.is_(True),
            )
        )
        if assignee is None:
            raise HTTPException(status_code=404, detail="Assigned user not found")
    if payload.scheduled_end and payload.scheduled_start:
        if payload.scheduled_end <= payload.scheduled_start:
            raise HTTPException(status_code=422, detail="End time must be after start time")

    work_order = WorkOrder(organization_id=organization_id, **payload.model_dump())
    db.add(work_order)
    db.commit()
    db.refresh(work_order)
    return work_order


@router.get("/work-orders", response_model=list[WorkOrderRead])
def list_work_orders(principal: CurrentPrincipal, db: DbSession) -> list[WorkOrder]:
    organization_id = principal.organization_id
    statement = select(WorkOrder).where(WorkOrder.organization_id == organization_id)
    if principal.role == OrganizationRole.CREW:
        statement = statement.where(WorkOrder.assigned_user_id == principal.user_id)
    return list(db.scalars(statement.order_by(WorkOrder.scheduled_start, WorkOrder.created_at)))


@router.put("/work-orders/{work_order_id}", response_model=WorkOrderRead)
def update_work_order(
    work_order_id: str,
    payload: WorkOrderUpdate,
    principal: ManagerPrincipal,
    db: DbSession,
) -> WorkOrder:
    work_order = db.scalar(
        select(WorkOrder).where(
            WorkOrder.id == work_order_id,
            WorkOrder.organization_id == principal.organization_id,
        )
    )
    if work_order is None:
        raise HTTPException(status_code=404, detail="Work order not found")
    property_record = db.scalar(
        select(Property).where(
            Property.id == payload.property_id,
            Property.organization_id == principal.organization_id,
        )
    )
    if property_record is None:
        raise HTTPException(status_code=404, detail="Property not found")
    if payload.assigned_user_id:
        assignee = db.scalar(
            select(OrganizationUser).where(
                OrganizationUser.id == payload.assigned_user_id,
                OrganizationUser.organization_id == principal.organization_id,
                OrganizationUser.active.is_(True),
                OrganizationUser.deleted_at.is_(None),
            )
        )
        if assignee is None:
            raise HTTPException(status_code=404, detail="Assigned user not found")
    if payload.scheduled_end and payload.scheduled_start:
        if payload.scheduled_end <= payload.scheduled_start:
            raise HTTPException(status_code=422, detail="End time must be after start time")
    for field, value in payload.model_dump().items():
        setattr(work_order, field, value)
    db.commit()
    db.refresh(work_order)
    return work_order


@router.get("/users", response_model=list[OrganizationUserRead])
def list_users(
    principal: ManagerPrincipal,
    db: DbSession,
    include_inactive: bool = False,
) -> list[OrganizationUser]:
    filters = [
        OrganizationUser.organization_id == principal.organization_id,
        OrganizationUser.deleted_at.is_(None),
    ]
    if not include_inactive:
        filters.append(OrganizationUser.active.is_(True))
    return list(
        db.scalars(select(OrganizationUser).where(*filters).order_by(OrganizationUser.display_name))
    )


@router.get(
    "/platform/organizations",
    response_model=list[PlatformOrganizationRead],
)
def list_platform_organizations(
    principal: PlatformPrincipal,
    db: DbSession,
) -> list[dict]:
    organizations = list(db.scalars(select(Organization).order_by(Organization.name)))
    result = []
    for organization in organizations:
        user_count = db.scalar(
            select(func.count(OrganizationUser.id)).where(
                OrganizationUser.organization_id == organization.id
            )
        )
        active_user_count = db.scalar(
            select(func.count(OrganizationUser.id)).where(
                OrganizationUser.organization_id == organization.id,
                OrganizationUser.active.is_(True),
            )
        )
        result.append(
            {
                "id": organization.id,
                "name": organization.name,
                "created_at": organization.created_at,
                "user_count": user_count or 0,
                "active_user_count": active_user_count or 0,
                "subscription_status": organization.subscription_status or "trialing",
            }
        )
    return result


@router.post(
    "/platform/organizations",
    response_model=PlatformWorkspaceCreated,
    status_code=status.HTTP_201_CREATED,
)
def create_platform_workspace(
    payload: PlatformWorkspaceCreate,
    principal: PlatformPrincipal,
    db: DbSession,
) -> dict:
    """Create a company workspace and invite its first administrator."""
    email = payload.admin_email.lower().strip()
    if db.scalar(select(OrganizationUser).where(OrganizationUser.email == email)) is not None:
        raise HTTPException(status_code=409, detail="That email already belongs to a workspace")
    organization = Organization(name=payload.organization_name.strip())
    db.add(organization)
    db.flush()
    token = secrets.token_urlsafe(32)
    invitation = OrganizationInvitation(
        organization_id=organization.id,
        invited_by_user_id=principal.user_id,
        email=email,
        role=OrganizationRole.ADMIN.value,
        token_hash=hashlib.sha256(token.encode()).hexdigest(),
        expires_at=datetime.now(UTC) + timedelta(days=payload.expires_in_days),
    )
    db.add(invitation)
    db.commit()
    db.refresh(organization)
    db.refresh(invitation)
    created = InvitationRead.model_validate(invitation).model_dump()
    created["acceptance_token"] = token
    return {"organization": organization, "invitation": created}


@router.get("/platform/users", response_model=list[PlatformUserRead])
def list_platform_users(
    principal: PlatformPrincipal,
    db: DbSession,
    include_inactive: bool = True,
) -> list[dict]:
    query = (
        select(OrganizationUser, Organization.name)
        .join(Organization, Organization.id == OrganizationUser.organization_id)
        .where(OrganizationUser.deleted_at.is_(None))
        .order_by(Organization.name, OrganizationUser.display_name)
    )
    if not include_inactive:
        query = query.where(OrganizationUser.active.is_(True))
    return [
        {
            **OrganizationUserRead.model_validate(user).model_dump(),
            "organization_name": organization_name,
        }
        for user, organization_name in db.execute(query).all()
    ]


@router.patch(
    "/platform/users/{user_id}/active",
    response_model=PlatformUserRead,
)
def set_platform_user_active(
    user_id: str,
    payload: UserActiveUpdate,
    principal: PlatformPrincipal,
    db: DbSession,
) -> dict:
    row = db.execute(
        select(OrganizationUser, Organization.name)
        .join(Organization, Organization.id == OrganizationUser.organization_id)
        .where(OrganizationUser.id == user_id)
    ).one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="User not found")
    user, organization_name = row
    if user.id == principal.user_id and not payload.active:
        raise HTTPException(status_code=409, detail="You cannot deactivate your own account")
    if user.role == OrganizationRole.ADMIN.value and not payload.active:
        active_admins = db.scalar(
            select(func.count(OrganizationUser.id)).where(
                OrganizationUser.organization_id == user.organization_id,
                OrganizationUser.role == OrganizationRole.ADMIN.value,
                OrganizationUser.active.is_(True),
                OrganizationUser.deleted_at.is_(None),
            )
        )
        if (active_admins or 0) <= 1:
            raise HTTPException(
                status_code=409,
                detail="At least one active administrator is required",
            )
    user.active = payload.active
    db.commit()
    db.refresh(user)
    return {
        **OrganizationUserRead.model_validate(user).model_dump(),
        "organization_name": organization_name,
    }


@router.delete(
    "/platform/users/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_platform_user(
    user_id: str,
    principal: PlatformPrincipal,
    db: DbSession,
) -> Response:
    user = db.scalar(
        select(OrganizationUser).where(
            OrganizationUser.id == user_id,
            OrganizationUser.deleted_at.is_(None),
        )
    )
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    if user.id == principal.user_id:
        raise HTTPException(status_code=409, detail="You cannot delete your own account")
    if user.role == OrganizationRole.ADMIN.value and user.active:
        active_admins = db.scalar(
            select(func.count(OrganizationUser.id)).where(
                OrganizationUser.organization_id == user.organization_id,
                OrganizationUser.role == OrganizationRole.ADMIN.value,
                OrganizationUser.active.is_(True),
                OrganizationUser.deleted_at.is_(None),
            )
        )
        if (active_admins or 0) <= 1:
            raise HTTPException(
                status_code=409,
                detail="At least one active administrator is required",
            )
    user.active = False
    user.deleted_at = datetime.now(UTC)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/users", response_model=OrganizationUserRead, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: OrganizationUserCreate, principal: AdminPrincipal, db: DbSession
) -> OrganizationUser:
    organization_id = principal.organization_id
    if db.get(Organization, organization_id) is None:
        raise HTTPException(status_code=404, detail="Organization not found")
    existing = db.scalar(
        select(OrganizationUser).where(
            OrganizationUser.organization_id == organization_id,
            OrganizationUser.email == payload.email.lower(),
        )
    )
    if existing is not None:
        raise HTTPException(status_code=409, detail="User already exists")
    user = OrganizationUser(
        organization_id=organization_id,
        email=payload.email.lower(),
        display_name=payload.display_name,
        role=payload.role.value,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.patch("/users/{user_id}/active", response_model=OrganizationUserRead)
def set_user_active(
    user_id: str,
    payload: UserActiveUpdate,
    principal: AdminPrincipal,
    db: DbSession,
) -> OrganizationUser:
    user = db.scalar(
        select(OrganizationUser).where(
            OrganizationUser.id == user_id,
            OrganizationUser.organization_id == principal.organization_id,
        )
    )
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    if user.id == principal.user_id and not payload.active:
        raise HTTPException(status_code=409, detail="You cannot deactivate your own account")
    if user.role == OrganizationRole.ADMIN.value and not payload.active:
        active_admins = db.scalar(
            select(func.count(OrganizationUser.id)).where(
                OrganizationUser.organization_id == principal.organization_id,
                OrganizationUser.role == OrganizationRole.ADMIN.value,
                OrganizationUser.active.is_(True),
            )
        )
        if (active_admins or 0) <= 1:
            raise HTTPException(
                status_code=409,
                detail="At least one active administrator is required",
            )
    user.active = payload.active
    db.commit()
    db.refresh(user)
    return user


@router.post("/customers", response_model=CustomerRead, status_code=status.HTTP_201_CREATED)
def create_customer(
    payload: CustomerCreate, principal: ManagerPrincipal, db: DbSession
) -> Customer:
    organization_id = principal.organization_id
    customer = Customer(organization_id=organization_id, **payload.model_dump())
    db.add(customer)
    db.commit()
    db.refresh(customer)
    return customer


@router.get("/customers", response_model=list[CustomerRead])
def list_customers(principal: CurrentPrincipal, db: DbSession) -> list[Customer]:
    organization_id = principal.organization_id
    return list(db.scalars(select(Customer).where(Customer.organization_id == organization_id)))


@router.put("/customers/{customer_id}", response_model=CustomerRead)
def update_customer(
    customer_id: str,
    payload: CustomerUpdate,
    principal: ManagerPrincipal,
    db: DbSession,
) -> Customer:
    customer = db.scalar(
        select(Customer).where(
            Customer.id == customer_id,
            Customer.organization_id == principal.organization_id,
        )
    )
    if customer is None:
        raise HTTPException(status_code=404, detail="Customer not found")
    for field, value in payload.model_dump().items():
        setattr(customer, field, value)
    db.commit()
    db.refresh(customer)
    return customer


@router.delete("/customers/{customer_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_customer(customer_id: str, principal: ManagerPrincipal, db: DbSession) -> Response:
    customer = db.scalar(
        select(Customer).where(
            Customer.id == customer_id,
            Customer.organization_id == principal.organization_id,
        )
    )
    if customer is None:
        raise HTTPException(status_code=404, detail="Customer not found")
    invoices = list(db.scalars(select(Invoice).where(Invoice.customer_id == customer_id)))
    for invoice in invoices:
        db.delete(invoice)
    properties = list(db.scalars(select(Property).where(Property.customer_id == customer_id)))
    for property_record in properties:
        _cascade_delete_property(property_record, db)
    db.delete(customer)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/materials", response_model=MaterialRead, status_code=status.HTTP_201_CREATED)
def create_material(
    payload: MaterialCreate, principal: DesignerPrincipal, db: DbSession
) -> Material:
    organization_id = principal.organization_id
    material = Material(
        organization_id=organization_id,
        name=payload.name,
        category=payload.category.value,
        description=payload.description,
    )
    db.add(material)
    db.commit()
    db.refresh(material)
    return material


@router.get("/materials", response_model=list[MaterialRead])
def list_materials(principal: CurrentPrincipal, db: DbSession) -> list[Material]:
    organization_id = principal.organization_id
    return list(db.scalars(select(Material).where(Material.organization_id == organization_id)))


@router.post(
    "/material-variants",
    response_model=MaterialVariantRead,
    status_code=status.HTTP_201_CREATED,
)
def create_material_variant(
    payload: MaterialVariantCreate, principal: DesignerPrincipal, db: DbSession
) -> MaterialVariant:
    organization_id = principal.organization_id
    material = db.scalar(
        select(Material).where(
            Material.id == payload.material_id,
            Material.organization_id == organization_id,
        )
    )
    if material is None:
        raise HTTPException(status_code=404, detail="Material not found")
    variant = MaterialVariant(organization_id=organization_id, **payload.model_dump())
    db.add(variant)
    db.commit()
    db.refresh(variant)
    return variant


@router.post(
    "/design-projects", response_model=DesignProjectRead, status_code=status.HTTP_201_CREATED
)
def create_design_project(
    payload: DesignProjectCreate, principal: DesignerPrincipal, db: DbSession
) -> DesignProject:
    organization_id = principal.organization_id
    property_record = db.scalar(
        select(Property).where(
            Property.id == payload.property_id,
            Property.organization_id == organization_id,
        )
    )
    if property_record is None:
        raise HTTPException(status_code=404, detail="Property not found")
    design = DesignProject(organization_id=organization_id, **payload.model_dump())
    db.add(design)
    db.commit()
    db.refresh(design)
    return design


@router.get("/design-projects", response_model=list[DesignProjectRead])
def list_design_projects(principal: CurrentPrincipal, db: DbSession) -> list[DesignProject]:
    organization_id = principal.organization_id
    return list(
        db.scalars(select(DesignProject).where(DesignProject.organization_id == organization_id))
    )


@router.put("/design-projects/{design_id}", response_model=DesignProjectRead)
def update_design_project(
    design_id: str,
    payload: DesignProjectUpdate,
    principal: DesignerPrincipal,
    db: DbSession,
) -> DesignProject:
    design = db.scalar(
        select(DesignProject).where(
            DesignProject.id == design_id,
            DesignProject.organization_id == principal.organization_id,
        )
    )
    if design is None:
        raise HTTPException(status_code=404, detail="Design project not found")
    property_record = db.scalar(
        select(Property).where(
            Property.id == payload.property_id,
            Property.organization_id == principal.organization_id,
        )
    )
    if property_record is None:
        raise HTTPException(status_code=404, detail="Property not found")
    for field, value in payload.model_dump().items():
        setattr(design, field, value)
    db.commit()
    db.refresh(design)
    return design


@router.delete("/design-projects/{design_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_design_project(design_id: str, principal: DesignerPrincipal, db: DbSession) -> Response:
    design = db.scalar(
        select(DesignProject).where(
            DesignProject.id == design_id,
            DesignProject.organization_id == principal.organization_id,
        )
    )
    if design is None:
        raise HTTPException(status_code=404, detail="Design project not found")
    _cascade_delete_design(design, db)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def _capture_for_tenant(capture_id: str, organization_id: str, db: Session) -> SiteCapture:
    capture = db.scalar(
        select(SiteCapture).where(
            SiteCapture.id == capture_id,
            SiteCapture.organization_id == organization_id,
            SiteCapture.status != "deleted",
        )
    )
    if capture is None:
        raise HTTPException(status_code=404, detail="Site capture not found")
    return capture


@router.post(
    "/design-projects/{design_project_id}/captures",
    response_model=SiteCaptureRead,
    status_code=status.HTTP_201_CREATED,
)
async def upload_site_capture(
    design_project_id: str,
    principal: DesignerPrincipal,
    db: DbSession,
    file: Annotated[UploadFile, File(description="JPEG, PNG or WebP site photo")],
) -> SiteCapture:
    design = db.scalar(
        select(DesignProject).where(
            DesignProject.id == design_project_id,
            DesignProject.organization_id == principal.organization_id,
        )
    )
    if design is None:
        raise HTTPException(status_code=404, detail="Design project not found")

    settings = get_settings()
    raw = await file.read(settings.image_max_bytes + 1)
    await file.close()
    if len(raw) > settings.image_max_bytes:
        raise HTTPException(status_code=413, detail="Image exceeds maximum size")
    if not raw:
        raise HTTPException(status_code=400, detail="Image is empty")
    try:
        image = sanitize_image(raw, settings.image_max_pixels)
    except InvalidImage as exc:
        raise HTTPException(status_code=415, detail=str(exc)) from exc

    capture_id = str(uuid4())
    key = tenant_storage_key(
        principal.organization_id,
        "captures",
        capture_id,
        f"original.{image.extension}",
    )
    filename = Path(file.filename or "capture").name[:255]
    storage = get_object_storage()
    storage.put(key, image.data, image.media_type)
    capture = SiteCapture(
        id=capture_id,
        organization_id=principal.organization_id,
        design_project_id=design_project_id,
        uploaded_by_user_id=principal.user_id,
        original_filename=filename,
        storage_key=key,
        media_type=image.media_type,
        byte_size=len(image.data),
        width=image.width,
        height=image.height,
        sha256=image.sha256,
    )
    try:
        db.add(capture)
        db.commit()
        db.refresh(capture)
    except Exception:
        db.rollback()
        storage.delete(key)
        raise
    return capture


@router.get(
    "/design-projects/{design_project_id}/captures",
    response_model=list[SiteCaptureRead],
)
def list_site_captures(
    design_project_id: str, principal: CurrentPrincipal, db: DbSession
) -> list[SiteCapture]:
    design = db.scalar(
        select(DesignProject.id).where(
            DesignProject.id == design_project_id,
            DesignProject.organization_id == principal.organization_id,
        )
    )
    if design is None:
        raise HTTPException(status_code=404, detail="Design project not found")
    return list(
        db.scalars(
            select(SiteCapture).where(
                SiteCapture.design_project_id == design_project_id,
                SiteCapture.organization_id == principal.organization_id,
                SiteCapture.status != "deleted",
            )
        )
    )


@router.get("/captures/{capture_id}", response_model=SiteCaptureRead)
def get_site_capture(capture_id: str, principal: CurrentPrincipal, db: DbSession) -> SiteCapture:
    return _capture_for_tenant(capture_id, principal.organization_id, db)


@router.get("/captures/{capture_id}/content", response_class=Response)
def get_site_capture_content(
    capture_id: str, principal: CurrentPrincipal, db: DbSession
) -> Response:
    capture = _capture_for_tenant(capture_id, principal.organization_id, db)
    try:
        content = get_object_storage().get(capture.storage_key)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Site capture content not found") from exc
    return Response(
        content=content,
        media_type=capture.media_type,
        headers={
            "Cache-Control": "private, no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.get("/captures/{capture_id}/signed-url", response_model=SignedObjectUrlRead)
def get_site_capture_signed_url(
    capture_id: str,
    principal: CurrentPrincipal,
    db: DbSession,
    response: Response,
) -> dict:
    capture = _capture_for_tenant(capture_id, principal.organization_id, db)
    settings = get_settings()
    url = get_object_storage().signed_get_url(
        capture.storage_key,
        filename=capture.original_filename,
        content_type=capture.media_type,
        inline=True,
    )
    if url is None:
        raise HTTPException(
            status_code=409,
            detail="Signed URLs are available when S3 storage is enabled",
        )
    response.headers["Cache-Control"] = "private, no-store"
    return {"url": url, "expires_in": settings.storage_signed_url_ttl_seconds}


@router.delete("/captures/{capture_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_site_capture(capture_id: str, principal: DesignerPrincipal, db: DbSession) -> Response:
    capture = _capture_for_tenant(capture_id, principal.organization_id, db)
    get_object_storage().delete(capture.storage_key)
    capture.status = "deleted"
    capture.deleted_at = datetime.now(UTC)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def _generation_for_tenant(job_id: str, organization_id: str, db: Session) -> GenerationJob:
    job = db.scalar(
        select(GenerationJob).where(
            GenerationJob.id == job_id,
            GenerationJob.organization_id == organization_id,
        )
    )
    if job is None:
        raise HTTPException(status_code=404, detail="Generation job not found")
    return job


@router.post(
    "/design-projects/{design_project_id}/generations",
    response_model=GenerationJobRead,
    status_code=status.HTTP_202_ACCEPTED,
)
async def create_generation_job(
    design_project_id: str,
    background_tasks: BackgroundTasks,
    principal: DesignerPrincipal,
    db: DbSession,
    capture_id: Annotated[str, Form()],
    prompt: Annotated[str, Form(min_length=2, max_length=2000)],
    mask: Annotated[UploadFile, File(description="Black and white PNG edit mask")],
    selected_pixel_count: Annotated[int | None, Form(ge=1)] = None,
    total_pixel_count: Annotated[int | None, Form(ge=1)] = None,
    calibration_pixel_length: Annotated[Decimal | None, Form(gt=0)] = None,
    calibration_real_length: Annotated[Decimal | None, Form(gt=0)] = None,
    calibration_unit: Annotated[str | None, Form(pattern="^(ft|m)$")] = None,
    estimated_area: Annotated[Decimal | None, Form(gt=0)] = None,
    estimated_perimeter: Annotated[Decimal | None, Form(gt=0)] = None,
    measurement_method: Annotated[
        str | None, Form(pattern="^(mask_pixels|reference_line|camera_reference)$")
    ] = None,
) -> GenerationJob:
    settings = get_settings()
    if settings.inference_provider not in {"replicate", "mock"}:
        raise HTTPException(status_code=503, detail="Image generation is disabled")
    capture = _capture_for_tenant(capture_id, principal.organization_id, db)
    if capture.design_project_id != design_project_id:
        raise HTTPException(status_code=404, detail="Site capture not found")
    raw_mask = await mask.read(settings.image_max_bytes + 1)
    await mask.close()
    if not raw_mask or len(raw_mask) > settings.image_max_bytes:
        raise HTTPException(status_code=413, detail="Mask is empty or too large")
    try:
        normalized_mask = normalize_edit_mask(
            raw_mask,
            (capture.width, capture.height),
            settings.image_max_pixels,
        )
    except InvalidImage as exc:
        raise HTTPException(status_code=415, detail=str(exc)) from exc
    month_start = datetime.now(UTC).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    spent = db.scalar(
        select(func.coalesce(func.sum(GenerationJob.estimated_cost_usd), 0)).where(
            GenerationJob.organization_id == principal.organization_id,
            GenerationJob.created_at >= month_start,
        )
    )
    projected_spend = float(spent or 0) + settings.inference_estimated_job_cost_usd
    if projected_spend > settings.inference_monthly_budget_usd:
        raise HTTPException(status_code=429, detail="Monthly AI generation budget reached")
    job_id = str(uuid4())
    key = tenant_storage_key(principal.organization_id, "generations", job_id, "mask.png")
    get_object_storage().put(key, normalized_mask, "image/png")
    calibrated = all(
        value is not None
        for value in (
            calibration_pixel_length,
            calibration_real_length,
            calibration_unit,
            estimated_area,
            estimated_perimeter,
        )
    )
    job = GenerationJob(
        id=job_id,
        organization_id=principal.organization_id,
        design_project_id=design_project_id,
        capture_id=capture_id,
        requested_by_user_id=principal.user_id,
        prompt=prompt,
        provider=settings.inference_provider,
        model_version=(
            settings.replicate_model_version
            if settings.inference_provider == "replicate"
            else "mock-landscape-v1"
        )
        or "unconfigured",
        mask_storage_key=key,
        measurement_method=(
            (measurement_method or "reference_line") if calibrated else "mask_pixels"
        ),
        selected_pixel_count=selected_pixel_count,
        total_pixel_count=total_pixel_count,
        calibration_pixel_length=calibration_pixel_length if calibrated else None,
        calibration_real_length=calibration_real_length if calibrated else None,
        calibration_unit=calibration_unit if calibrated else None,
        estimated_area=estimated_area if calibrated else None,
        estimated_perimeter=estimated_perimeter if calibrated else None,
        measurement_confidence="photo_estimate" if calibrated else "uncalibrated",
        estimated_cost_usd=(
            Decimal(str(settings.inference_estimated_job_cost_usd))
            if settings.inference_provider == "replicate"
            else Decimal("0")
        ),
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    background_tasks.add_task(process_generation_job, job.id)
    return job


@router.get(
    "/design-projects/{design_project_id}/generations",
    response_model=list[GenerationJobRead],
)
def list_generation_jobs(
    design_project_id: str, principal: CurrentPrincipal, db: DbSession
) -> list[GenerationJob]:
    return list(
        db.scalars(
            select(GenerationJob)
            .where(
                GenerationJob.design_project_id == design_project_id,
                GenerationJob.organization_id == principal.organization_id,
            )
            .order_by(GenerationJob.created_at.desc())
        )
    )


@router.get(
    "/generations/{job_id}/material-estimate",
    response_model=GenerationMaterialEstimateRead,
)
def get_generation_material_estimate(
    job_id: str, principal: CurrentPrincipal, db: DbSession
) -> GenerationMaterialEstimate:
    _generation_for_tenant(job_id, principal.organization_id, db)
    estimate = db.scalar(
        select(GenerationMaterialEstimate).where(
            GenerationMaterialEstimate.generation_job_id == job_id,
            GenerationMaterialEstimate.organization_id == principal.organization_id,
        )
    )
    if estimate is None:
        raise HTTPException(status_code=404, detail="Material estimate not found")
    return estimate


@router.put(
    "/generations/{job_id}/material-estimate",
    response_model=GenerationMaterialEstimateRead,
)
def upsert_generation_material_estimate(
    job_id: str,
    payload: GenerationMaterialEstimateCreate,
    principal: DesignerPrincipal,
    db: DbSession,
) -> GenerationMaterialEstimate:
    job = _generation_for_tenant(job_id, principal.organization_id, db)
    if job.status != GenerationStatus.SUCCEEDED.value:
        raise HTTPException(status_code=409, detail="Generation must succeed before estimating")
    if not job.estimated_area or not job.estimated_perimeter or not job.calibration_unit:
        raise HTTPException(
            status_code=409,
            detail="Calibrate the photo measurement before estimating materials",
        )
    try:
        result = calculate_material_estimate(
            material_type=payload.material_type,
            area=job.estimated_area,
            perimeter=job.estimated_perimeter,
            measurement_unit=job.calibration_unit,
            waste_percent=payload.waste_percent,
            depth=payload.depth,
            unit_price=payload.unit_price,
            labour_rate=payload.labour_rate,
            labour_hours=payload.labour_hours,
            delivery_cost=payload.delivery_cost,
            tax_rate=payload.tax_rate,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    estimate = db.scalar(
        select(GenerationMaterialEstimate).where(
            GenerationMaterialEstimate.generation_job_id == job_id,
            GenerationMaterialEstimate.organization_id == principal.organization_id,
        )
    )
    values = {
        "material_type": payload.material_type,
        "measurement_unit": job.calibration_unit,
        "measured_area": job.estimated_area,
        "measured_perimeter": job.estimated_perimeter,
        "waste_percent": payload.waste_percent,
        "depth": payload.depth,
        "order_quantity": result.order_quantity,
        "material_unit": result.material_unit,
        "edging_quantity": result.edging_quantity,
        "labour_hours": result.labour_hours,
        "unit_price": payload.unit_price,
        "labour_rate": payload.labour_rate,
        "delivery_cost": payload.delivery_cost,
        "material_cost": result.material_cost,
        "labour_cost": result.labour_cost,
        "subtotal": result.subtotal,
        "tax_rate": payload.tax_rate,
        "tax_amount": result.tax_amount,
        "total": result.total,
        "currency": "CAD",
        "assumptions": result.assumptions,
    }
    if estimate is None:
        estimate = GenerationMaterialEstimate(
            organization_id=principal.organization_id,
            generation_job_id=job_id,
            **values,
        )
        db.add(estimate)
    else:
        for field, value in values.items():
            setattr(estimate, field, value)
    db.commit()
    db.refresh(estimate)
    return estimate


@router.get("/generations/{job_id}", response_model=GenerationJobRead)
def get_generation_job(job_id: str, principal: CurrentPrincipal, db: DbSession) -> GenerationJob:
    return _generation_for_tenant(job_id, principal.organization_id, db)


@router.get(
    "/generations/{job_id}/evaluation",
    response_model=GenerationEvaluationRead,
)
def get_generation_evaluation(
    job_id: str, principal: CurrentPrincipal, db: DbSession
) -> GenerationEvaluation:
    _generation_for_tenant(job_id, principal.organization_id, db)
    evaluation = db.scalar(
        select(GenerationEvaluation).where(
            GenerationEvaluation.generation_job_id == job_id,
            GenerationEvaluation.organization_id == principal.organization_id,
        )
    )
    if evaluation is None:
        raise HTTPException(status_code=404, detail="Generation evaluation not found")
    return evaluation


@router.get(
    "/generations/{job_id}/reviews",
    response_model=list[GenerationReviewRead],
)
def list_generation_reviews(
    job_id: str, principal: CurrentPrincipal, db: DbSession
) -> list[GenerationReview]:
    _generation_for_tenant(job_id, principal.organization_id, db)
    return list(
        db.scalars(
            select(GenerationReview)
            .where(
                GenerationReview.generation_job_id == job_id,
                GenerationReview.organization_id == principal.organization_id,
            )
            .order_by(GenerationReview.created_at.desc())
        )
    )


@router.post(
    "/generations/{job_id}/reviews",
    response_model=GenerationReviewRead,
    status_code=status.HTTP_201_CREATED,
)
def create_generation_review(
    job_id: str,
    payload: GenerationReviewCreate,
    principal: DesignerPrincipal,
    db: DbSession,
) -> GenerationReview:
    job = _generation_for_tenant(job_id, principal.organization_id, db)
    if job.status != GenerationStatus.SUCCEEDED.value:
        raise HTTPException(
            status_code=409,
            detail="Only completed generations can be reviewed",
        )
    review = GenerationReview(
        organization_id=principal.organization_id,
        generation_job_id=job.id,
        reviewer_user_id=principal.user_id,
        decision=payload.decision,
        notes=payload.notes.strip() if payload.notes else None,
    )
    db.add(review)
    design = db.scalar(
        select(DesignProject).where(
            DesignProject.id == job.design_project_id,
            DesignProject.organization_id == principal.organization_id,
        )
    )
    if design is not None:
        design.status = {
            "approved": "accepted",
            "rejected": "rejected",
            "revision_requested": "review",
        }[payload.decision]
    db.commit()
    db.refresh(review)
    return review


@router.get("/generations/{job_id}/output", response_class=Response)
def get_generation_output(job_id: str, principal: CurrentPrincipal, db: DbSession) -> Response:
    job = _generation_for_tenant(job_id, principal.organization_id, db)
    if not job.output_storage_key or not job.output_media_type:
        raise HTTPException(status_code=404, detail="Generation output not found")
    return Response(
        content=get_object_storage().get(job.output_storage_key),
        media_type=job.output_media_type,
        headers={
            "Cache-Control": "private, no-store",
            "X-Content-Type-Options": "nosniff",
        },
    )


@router.get("/generation-metrics", response_model=GenerationMetricsRead)
def get_generation_metrics(principal: ManagerPrincipal, db: DbSession) -> dict:
    rows = db.execute(
        select(GenerationJob, GenerationEvaluation)
        .outerjoin(
            GenerationEvaluation,
            GenerationEvaluation.generation_job_id == GenerationJob.id,
        )
        .where(GenerationJob.organization_id == principal.organization_id)
        .order_by(GenerationJob.created_at.desc())
    ).all()
    total = len(rows)
    completed = sum(
        job.status in {GenerationStatus.SUCCEEDED.value, GenerationStatus.FAILED.value}
        for job, _ in rows
    )
    evaluated = sum(evaluation is not None for _, evaluation in rows)
    passed = sum(bool(evaluation and evaluation.passed) for _, evaluation in rows)
    failed = evaluated - passed
    generation_latencies = [job.latency_ms for job, _ in rows if job.latency_ms is not None]
    evaluation_latencies = [
        evaluation.evaluation_latency_ms for _, evaluation in rows if evaluation is not None
    ]
    cost = sum((job.estimated_cost_usd or Decimal("0")) for job, _ in rows)

    failure_counts: dict[str, int] = {}
    model_rows: dict[str, list[tuple[GenerationJob, GenerationEvaluation | None]]] = {}
    trend_rows: dict[str, list[tuple[GenerationJob, GenerationEvaluation | None]]] = {}
    latest_reviews = {
        review.generation_job_id: review
        for review in db.scalars(
            select(GenerationReview)
            .where(GenerationReview.organization_id == principal.organization_id)
            .order_by(GenerationReview.created_at)
        )
    }
    review_queue: list[dict] = []
    for job, evaluation in rows:
        model_rows.setdefault(job.model_version, []).append((job, evaluation))
        day = job.created_at.date().isoformat()
        trend_rows.setdefault(day, []).append((job, evaluation))
        latest_review = latest_reviews.get(job.id)
        if evaluation and not evaluation.passed:
            for reason in evaluation.failure_reasons:
                failure_counts[reason] = failure_counts.get(reason, 0) + 1
            if (latest_review is None or latest_review.decision == "revision_requested") and len(
                review_queue
            ) < 20:
                review_queue.append(
                    {
                        "job_id": job.id,
                        "design_project_id": job.design_project_id,
                        "prompt": job.prompt,
                        "model_version": job.model_version,
                        "created_at": job.created_at,
                        "evaluation_id": evaluation.id,
                        "masked_change_ratio": evaluation.masked_change_ratio,
                        "protected_change_ratio": evaluation.protected_change_ratio,
                        "failure_reasons": evaluation.failure_reasons,
                        "latest_review_decision": (
                            latest_review.decision if latest_review else None
                        ),
                    }
                )

    models = []
    for model_version, model_entries in sorted(model_rows.items()):
        model_evaluations = [evaluation for _, evaluation in model_entries if evaluation]
        model_passed = sum(evaluation.passed for evaluation in model_evaluations)
        latencies = [job.latency_ms for job, _ in model_entries if job.latency_ms is not None]
        models.append(
            {
                "model_version": model_version,
                "total": len(model_entries),
                "evaluated": len(model_evaluations),
                "passed": model_passed,
                "pass_rate": (
                    round(model_passed / len(model_evaluations) * 100, 1)
                    if model_evaluations
                    else None
                ),
                "average_latency_ms": round(sum(latencies) / len(latencies), 1)
                if latencies
                else None,
                "estimated_cost_usd": sum(
                    (job.estimated_cost_usd or Decimal("0")) for job, _ in model_entries
                ),
            }
        )

    trends = []
    for day, day_entries in sorted(trend_rows.items())[-30:]:
        day_evaluations = [evaluation for _, evaluation in day_entries if evaluation]
        day_passed = sum(evaluation.passed for evaluation in day_evaluations)
        trends.append(
            {
                "date": day,
                "total": len(day_entries),
                "evaluated": len(day_evaluations),
                "passed": day_passed,
                "failed": len(day_evaluations) - day_passed,
                "pass_rate": round(day_passed / len(day_evaluations) * 100, 1)
                if day_evaluations
                else None,
            }
        )

    return {
        "total_generations": total,
        "completed_generations": completed,
        "evaluated_generations": evaluated,
        "passed_generations": passed,
        "failed_evaluations": failed,
        "unevaluated_generations": total - evaluated,
        "pass_rate": round(passed / evaluated * 100, 1) if evaluated else None,
        "average_generation_latency_ms": round(
            sum(generation_latencies) / len(generation_latencies), 1
        )
        if generation_latencies
        else None,
        "average_evaluation_latency_ms": round(
            sum(evaluation_latencies) / len(evaluation_latencies), 1
        )
        if evaluation_latencies
        else None,
        "estimated_cost_usd": cost,
        "failure_reasons": [
            {"reason": reason, "count": count}
            for reason, count in sorted(
                failure_counts.items(), key=lambda entry: (-entry[1], entry[0])
            )
        ],
        "models": models,
        "trends": trends,
        "review_queue": review_queue,
    }


@router.get("/generations/{job_id}/content", response_class=Response)
def get_generation_content(job_id: str, principal: CurrentPrincipal, db: DbSession) -> Response:
    job = _generation_for_tenant(job_id, principal.organization_id, db)
    if job.status != GenerationStatus.SUCCEEDED.value or not job.output_storage_key:
        raise HTTPException(status_code=409, detail="Generated image is not ready")
    return Response(
        content=get_object_storage().get(job.output_storage_key),
        media_type=job.output_media_type or "image/png",
        headers={"Cache-Control": "private, no-store"},
    )


@router.get("/generations/{job_id}/signed-url", response_model=SignedObjectUrlRead)
def get_generation_signed_url(
    job_id: str,
    principal: CurrentPrincipal,
    db: DbSession,
    response: Response,
) -> dict:
    job = _generation_for_tenant(job_id, principal.organization_id, db)
    if job.status != GenerationStatus.SUCCEEDED.value or not job.output_storage_key:
        raise HTTPException(status_code=409, detail="Generated image is not ready")
    settings = get_settings()
    content_type = job.output_media_type or "image/png"
    extension = "jpg" if "jpeg" in content_type else "png"
    url = get_object_storage().signed_get_url(
        job.output_storage_key,
        filename=f"generated-landscape.{extension}",
        content_type=content_type,
        inline=True,
    )
    if url is None:
        raise HTTPException(
            status_code=409,
            detail="Signed URLs are available when S3 storage is enabled",
        )
    response.headers["Cache-Control"] = "private, no-store"
    return {"url": url, "expires_in": settings.storage_signed_url_ttl_seconds}


@router.post("/quotes", response_model=QuoteRead, status_code=status.HTTP_201_CREATED)
def create_quote(payload: QuoteCreate, principal: ManagerPrincipal, db: DbSession) -> Quote:
    organization_id = principal.organization_id
    design = db.scalar(
        select(DesignProject).where(
            DesignProject.id == payload.design_project_id,
            DesignProject.organization_id == organization_id,
        )
    )
    if design is None:
        raise HTTPException(status_code=404, detail="Design project not found")
    if payload.generation_job_id:
        job = _generation_for_tenant(payload.generation_job_id, organization_id, db)
        if job.design_project_id != design.id:
            raise HTTPException(status_code=422, detail="Generation does not belong to design")
        approved = db.scalar(
            select(GenerationReview.id).where(
                GenerationReview.generation_job_id == job.id,
                GenerationReview.organization_id == organization_id,
                GenerationReview.decision == "approved",
            )
        )
        if approved is None:
            raise HTTPException(status_code=409, detail="Approve the concept before quoting")

    subtotal = sum((item.quantity * item.unit_price for item in payload.items), Decimal("0"))
    subtotal = subtotal.quantize(Decimal("0.01"))
    markup_amount = (subtotal * payload.markup_rate / Decimal("100")).quantize(Decimal("0.01"))
    taxable = subtotal + markup_amount - payload.discount_amount
    if taxable < 0:
        raise HTTPException(status_code=422, detail="Discount cannot exceed subtotal and markup")
    tax_amount = (taxable * payload.tax_rate / Decimal("100")).quantize(Decimal("0.01"))
    total = (taxable + tax_amount).quantize(Decimal("0.01"))
    count = (
        db.scalar(select(func.count(Quote.id)).where(Quote.organization_id == organization_id)) or 0
    )
    quote = Quote(
        organization_id=organization_id,
        design_project_id=payload.design_project_id,
        generation_job_id=payload.generation_job_id,
        number=f"Q-{datetime.now(UTC).year}-{count + 1:04d}",
        title=payload.title,
        subtotal=subtotal,
        markup_rate=payload.markup_rate,
        markup_amount=markup_amount,
        discount_amount=payload.discount_amount,
        tax_rate=payload.tax_rate,
        tax_amount=tax_amount,
        total=total,
        currency=payload.currency.upper(),
        assumptions=payload.assumptions,
    )
    quote.items = [
        QuoteItem(
            description=item.description,
            category=item.category,
            quantity=item.quantity,
            unit=item.unit,
            unit_price=item.unit_price,
            line_total=(item.quantity * item.unit_price).quantize(Decimal("0.01")),
            position=position,
        )
        for position, item in enumerate(payload.items)
    ]
    db.add(quote)
    db.commit()
    db.refresh(quote)
    return quote


@router.get("/quotes", response_model=list[QuoteRead])
def list_quotes(principal: CurrentPrincipal, db: DbSession) -> list[Quote]:
    organization_id = principal.organization_id
    return list(
        db.scalars(
            select(Quote)
            .where(Quote.organization_id == organization_id)
            .order_by(Quote.created_at.desc())
        )
    )


@router.get("/quotes/{quote_id}", response_model=QuoteRead)
def get_quote(quote_id: str, principal: CurrentPrincipal, db: DbSession) -> Quote:
    record = db.scalar(
        select(Quote).where(
            Quote.id == quote_id, Quote.organization_id == principal.organization_id
        )
    )
    if record is None:
        raise HTTPException(status_code=404, detail="Quote not found")
    return record


@router.patch("/quotes/{quote_id}/status", response_model=QuoteRead)
def update_quote_status(
    quote_id: str, payload: QuoteStatusUpdate, principal: ManagerPrincipal, db: DbSession
) -> Quote:
    record = db.scalar(
        select(Quote).where(
            Quote.id == quote_id, Quote.organization_id == principal.organization_id
        )
    )
    if record is None:
        raise HTTPException(status_code=404, detail="Quote not found")
    allowed = {
        "draft": {"sent"},
        "sent": {"approved", "rejected", "expired"},
        "approved": set(),
        "rejected": set(),
        "expired": set(),
    }
    if payload.status.value not in allowed.get(record.status, set()):
        raise HTTPException(status_code=409, detail="Invalid quote status transition")
    record.status = payload.status.value
    db.commit()
    db.refresh(record)
    return record


@router.post(
    "/quotes/{quote_id}/work-order",
    response_model=WorkOrderRead,
    status_code=status.HTTP_201_CREATED,
)
def convert_quote_to_work_order(
    quote_id: str,
    payload: QuoteWorkOrderCreate,
    principal: ManagerPrincipal,
    db: DbSession,
) -> WorkOrder:
    organization_id = principal.organization_id
    quote_record = db.scalar(
        select(Quote).where(
            Quote.id == quote_id,
            Quote.organization_id == organization_id,
        )
    )
    if quote_record is None:
        raise HTTPException(status_code=404, detail="Quote not found")
    if quote_record.status != QuoteStatus.APPROVED.value:
        raise HTTPException(status_code=409, detail="Approve the quote before scheduling work")
    existing = db.scalar(
        select(WorkOrder).where(
            WorkOrder.quote_id == quote_record.id,
            WorkOrder.organization_id == organization_id,
        )
    )
    if existing is not None:
        raise HTTPException(status_code=409, detail="This quote already has a work order")
    if payload.scheduled_end <= payload.scheduled_start:
        raise HTTPException(status_code=422, detail="End time must be after start time")
    design = db.scalar(
        select(DesignProject).where(
            DesignProject.id == quote_record.design_project_id,
            DesignProject.organization_id == organization_id,
        )
    )
    if design is None:
        raise HTTPException(status_code=404, detail="Design project not found")
    if payload.assigned_user_id:
        assignee = db.scalar(
            select(OrganizationUser).where(
                OrganizationUser.id == payload.assigned_user_id,
                OrganizationUser.organization_id == organization_id,
                OrganizationUser.active.is_(True),
                OrganizationUser.deleted_at.is_(None),
            )
        )
        if assignee is None:
            raise HTTPException(status_code=404, detail="Assigned user not found")

    checklist = [
        {
            "description": item.description,
            "category": item.category,
            "quantity": str(item.quantity),
            "unit": item.unit,
        }
        for item in quote_record.items
        if item.category in {"material", "equipment", "delivery"}
    ]
    description_parts = [f"Created from approved quote {quote_record.number}."]
    if quote_record.assumptions:
        description_parts.append(quote_record.assumptions)
    work_order = WorkOrder(
        organization_id=organization_id,
        property_id=design.property_id,
        quote_id=quote_record.id,
        design_project_id=design.id,
        title=quote_record.title,
        description="\n\n".join(description_parts),
        status=WorkOrderStatus.SCHEDULED.value,
        assigned_user_id=payload.assigned_user_id,
        scheduled_start=payload.scheduled_start,
        scheduled_end=payload.scheduled_end,
        priority=payload.priority,
        quoted_total=quote_record.total,
        quote_currency=quote_record.currency,
        material_checklist=checklist,
        customer_instructions=payload.customer_instructions,
    )
    db.add(work_order)
    db.commit()
    db.refresh(work_order)
    return work_order


@router.post(
    "/work-orders/{work_order_id}/complete",
    response_model=WorkOrderRead,
)
def complete_work_order(
    work_order_id: str,
    payload: WorkOrderCompletionCreate,
    principal: ManagerPrincipal,
    db: DbSession,
) -> WorkOrder:
    work_order = db.scalar(
        select(WorkOrder).where(
            WorkOrder.id == work_order_id,
            WorkOrder.organization_id == principal.organization_id,
        )
    )
    if work_order is None:
        raise HTTPException(status_code=404, detail="Work order not found")
    if work_order.status not in {
        WorkOrderStatus.SCHEDULED.value,
        WorkOrderStatus.IN_PROGRESS.value,
    }:
        raise HTTPException(status_code=409, detail="Only active work can be completed")
    materials = [
        {
            "description": item.description,
            "quantity": str(item.quantity),
            "unit": item.unit,
            "unit_price": str(item.unit_price),
            "line_total": str((item.quantity * item.unit_price).quantize(Decimal("0.01"))),
        }
        for item in payload.materials
    ]
    material_total = sum(
        (item.quantity * item.unit_price for item in payload.materials),
        start=Decimal("0"),
    )
    labour_total = payload.labour_hours * payload.labour_rate
    work_order.actual_labour_hours = payload.labour_hours
    work_order.actual_labour_rate = payload.labour_rate
    work_order.actual_materials = materials
    work_order.actual_total = (material_total + labour_total).quantize(Decimal("0.01"))
    work_order.completion_notes = payload.notes
    work_order.completed_at = datetime.now(UTC)
    work_order.status = WorkOrderStatus.COMPLETED.value
    db.commit()
    db.refresh(work_order)
    return work_order


@router.get(
    "/work-orders/{work_order_id}/variance",
    response_model=WorkOrderVarianceRead,
)
def get_work_order_variance(
    work_order_id: str,
    principal: CurrentPrincipal,
    db: DbSession,
) -> WorkOrderVarianceRead:
    work_order = db.scalar(
        select(WorkOrder).where(
            WorkOrder.id == work_order_id,
            WorkOrder.organization_id == principal.organization_id,
        )
    )
    if work_order is None:
        raise HTTPException(status_code=404, detail="Work order not found")
    quoted = work_order.quoted_total or Decimal("0")
    actual = work_order.actual_total or Decimal("0")
    variance = actual - quoted
    return WorkOrderVarianceRead(
        quoted_total=quoted,
        actual_total=actual,
        variance_amount=variance,
        variance_percent=(variance / quoted * 100).quantize(Decimal("0.01")) if quoted else None,
    )


@router.post(
    "/work-orders/{work_order_id}/invoice",
    response_model=InvoiceRead,
    status_code=status.HTTP_201_CREATED,
)
def create_work_order_invoice(
    work_order_id: str,
    principal: ManagerPrincipal,
    db: DbSession,
) -> Invoice:
    work_order = db.scalar(
        select(WorkOrder).where(
            WorkOrder.id == work_order_id,
            WorkOrder.organization_id == principal.organization_id,
        )
    )
    if work_order is None:
        raise HTTPException(status_code=404, detail="Work order not found")
    if work_order.status != WorkOrderStatus.COMPLETED.value:
        raise HTTPException(status_code=409, detail="Complete the work before invoicing")
    if db.scalar(select(Invoice.id).where(Invoice.work_order_id == work_order.id)):
        raise HTTPException(status_code=409, detail="This work order already has an invoice")
    property_record = db.scalar(
        select(Property).where(
            Property.id == work_order.property_id,
            Property.organization_id == principal.organization_id,
        )
    )
    if property_record is None:
        raise HTTPException(status_code=404, detail="Property not found")
    customer = (
        db.scalar(select(Customer).where(Customer.id == property_record.customer_id))
        if property_record and property_record.customer_id
        else None
    )
    quote_record = (
        db.scalar(select(Quote).where(Quote.id == work_order.quote_id))
        if work_order.quote_id
        else None
    )
    item_values = [
        (
            material["description"],
            Decimal(material["quantity"]),
            Decimal(material["unit_price"]),
        )
        for material in (work_order.actual_materials or [])
    ]
    if work_order.actual_labour_hours and work_order.actual_labour_rate:
        item_values.append(
            (
                "Installation labour",
                work_order.actual_labour_hours,
                work_order.actual_labour_rate,
            )
        )
    if not item_values:
        raise HTTPException(status_code=409, detail="Record actual costs before invoicing")
    subtotal = sum((quantity * rate for _, quantity, rate in item_values), Decimal("0"))
    tax_rate = quote_record.tax_rate if quote_record else Decimal("0")
    tax_amount = (subtotal * tax_rate / Decimal("100")).quantize(Decimal("0.01"))
    first = item_values[0]
    invoice = Invoice(
        organization_id=principal.organization_id,
        customer_id=customer.id if customer else None,
        work_order_id=work_order.id,
        number=f"INV-{datetime.now(UTC):%Y}-{uuid4().hex[:8].upper()}",
        description=first[0],
        quantity=first[1],
        rate=first[2],
        subtotal=subtotal,
        currency=work_order.quote_currency or "CAD",
        status="draft",
        customer_name=customer.name if customer else property_record.name,
        customer_email=customer.email if customer else None,
        customer_phone=customer.phone if customer else None,
        customer_address=customer.address if customer else property_record.location,
        gst_rate=tax_rate,
        pst_rate=Decimal("0"),
        gst_amount=tax_amount,
        pst_amount=Decimal("0"),
        total=subtotal + tax_amount,
        notes=f"Generated from completed work order {work_order.id}.",
    )
    invoice.items = [
        InvoiceItem(
            description=description,
            quantity=quantity,
            rate=rate,
            line_total=quantity * rate,
            position=position,
        )
        for position, (description, quantity, rate) in enumerate(item_values)
    ]
    db.add(invoice)
    db.commit()
    db.refresh(invoice)
    return invoice


@router.post(
    "/invoices/{invoice_id}/payments",
    response_model=InvoicePaymentRead,
    status_code=status.HTTP_201_CREATED,
)
def record_invoice_payment(
    invoice_id: str,
    payload: InvoicePaymentCreate,
    principal: ManagerPrincipal,
    db: DbSession,
) -> InvoicePayment:
    invoice = db.scalar(
        select(Invoice).where(
            Invoice.id == invoice_id,
            Invoice.organization_id == principal.organization_id,
        )
    )
    if invoice is None:
        raise HTTPException(status_code=404, detail="Invoice not found")
    if invoice.status == "void":
        raise HTTPException(status_code=409, detail="A void invoice cannot receive payments")
    if payload.amount > invoice.balance_due:
        raise HTTPException(status_code=422, detail="Payment exceeds the invoice balance")
    payment = InvoicePayment(
        organization_id=principal.organization_id,
        invoice_id=invoice.id,
        amount=payload.amount,
        method=payload.method,
        reference=payload.reference,
        received_at=payload.received_at or datetime.now(UTC),
    )
    invoice.paid_amount += payload.amount
    invoice.status = "paid" if invoice.paid_amount >= invoice.total else "sent"
    invoice.updated_at = datetime.now(UTC)
    db.add(payment)
    db.commit()
    db.refresh(payment)
    return payment


@router.post("/invoices", response_model=InvoiceRead, status_code=status.HTTP_201_CREATED)
def create_invoice(payload: InvoiceCreate, principal: ManagerPrincipal, db: DbSession) -> Invoice:
    customer = None
    if payload.customer_id:
        customer = db.scalar(
            select(Customer).where(
                Customer.id == payload.customer_id,
                Customer.organization_id == principal.organization_id,
            )
        )
        if customer is None:
            raise HTTPException(status_code=404, detail="Customer not found")
    customer_name = payload.customer_name or (customer.name if customer else None)
    if not customer_name:
        raise HTTPException(status_code=422, detail="Customer name is required")
    subtotal = sum((item.quantity * item.rate for item in payload.items), start=0)
    gst_amount = (subtotal * payload.gst_rate / Decimal("100")).quantize(Decimal("0.01"))
    pst_amount = (subtotal * payload.pst_rate / Decimal("100")).quantize(Decimal("0.01"))
    first_item = payload.items[0]
    if payload.number:
        duplicate = db.scalar(
            select(Invoice.id).where(
                Invoice.organization_id == principal.organization_id,
                Invoice.number == payload.number,
            )
        )
        if duplicate:
            raise HTTPException(status_code=409, detail="Invoice number already exists")
    invoice = Invoice(
        organization_id=principal.organization_id,
        customer_id=payload.customer_id,
        number=payload.number or f"INV-{datetime.now(UTC):%Y}-{uuid4().hex[:8].upper()}",
        description=first_item.description,
        quantity=first_item.quantity,
        rate=first_item.rate,
        subtotal=subtotal,
        currency=payload.currency.upper(),
        notes=payload.notes,
        customer_name=customer_name,
        customer_email=(
            payload.customer_email
            if payload.customer_email is not None
            else (customer.email if customer else None)
        ),
        customer_phone=(
            payload.customer_phone
            if payload.customer_phone is not None
            else (customer.phone if customer else None)
        ),
        customer_address=(
            payload.customer_address
            if payload.customer_address is not None
            else (customer.address if customer else None)
        ),
        company_email=payload.company_email,
        company_phone=payload.company_phone,
        company_address=payload.company_address,
        gst_rate=payload.gst_rate,
        pst_rate=payload.pst_rate,
        gst_amount=gst_amount,
        pst_amount=pst_amount,
        total=subtotal + gst_amount + pst_amount,
    )
    db.add(invoice)
    db.flush()
    invoice.items = [
        InvoiceItem(
            description=item.description,
            quantity=item.quantity,
            rate=item.rate,
            line_total=item.quantity * item.rate,
            position=position,
        )
        for position, item in enumerate(payload.items)
    ]
    db.commit()
    db.refresh(invoice)
    return invoice


@router.get("/invoices", response_model=list[InvoiceRead])
def list_invoices(principal: CurrentPrincipal, db: DbSession) -> list[Invoice]:
    return list(
        db.scalars(
            select(Invoice)
            .where(Invoice.organization_id == principal.organization_id)
            .order_by(Invoice.created_at.desc())
        )
    )


@router.put("/invoices/{invoice_id}", response_model=InvoiceRead)
def update_invoice(
    invoice_id: str,
    payload: InvoiceUpdate,
    principal: ManagerPrincipal,
    db: DbSession,
) -> Invoice:
    invoice = db.scalar(
        select(Invoice).where(
            Invoice.id == invoice_id,
            Invoice.organization_id == principal.organization_id,
        )
    )
    if invoice is None:
        raise HTTPException(status_code=404, detail="Invoice not found")
    if payload.number and payload.number != invoice.number:
        duplicate = db.scalar(
            select(Invoice.id).where(
                Invoice.organization_id == principal.organization_id,
                Invoice.number == payload.number,
                Invoice.id != invoice.id,
            )
        )
        if duplicate:
            raise HTTPException(status_code=409, detail="Invoice number already exists")
        invoice.number = payload.number
    customer = None
    if payload.customer_id:
        customer = db.scalar(
            select(Customer).where(
                Customer.id == payload.customer_id,
                Customer.organization_id == principal.organization_id,
            )
        )
        if customer is None:
            raise HTTPException(status_code=404, detail="Customer not found")
    customer_name = payload.customer_name or (customer.name if customer else None)
    if not customer_name:
        raise HTTPException(status_code=422, detail="Customer name is required")
    first_item = payload.items[0]
    invoice.customer_id = payload.customer_id
    invoice.description = first_item.description
    invoice.quantity = first_item.quantity
    invoice.rate = first_item.rate
    invoice.subtotal = sum((item.quantity * item.rate for item in payload.items), start=0)
    invoice.customer_name = customer_name
    invoice.customer_email = (
        payload.customer_email
        if payload.customer_email is not None
        else (customer.email if customer else None)
    )
    invoice.customer_phone = (
        payload.customer_phone
        if payload.customer_phone is not None
        else (customer.phone if customer else None)
    )
    invoice.customer_address = (
        payload.customer_address
        if payload.customer_address is not None
        else (customer.address if customer else None)
    )
    invoice.company_email = payload.company_email
    invoice.company_phone = payload.company_phone
    invoice.company_address = payload.company_address
    invoice.gst_rate = payload.gst_rate
    invoice.pst_rate = payload.pst_rate
    invoice.gst_amount = (invoice.subtotal * payload.gst_rate / Decimal("100")).quantize(
        Decimal("0.01")
    )
    invoice.pst_amount = (invoice.subtotal * payload.pst_rate / Decimal("100")).quantize(
        Decimal("0.01")
    )
    invoice.total = invoice.subtotal + invoice.gst_amount + invoice.pst_amount
    invoice.currency = payload.currency.upper()
    invoice.notes = payload.notes
    invoice.status = payload.status.value
    invoice.updated_at = datetime.now(UTC)
    invoice.items = [
        InvoiceItem(
            description=item.description,
            quantity=item.quantity,
            rate=item.rate,
            line_total=item.quantity * item.rate,
            position=position,
        )
        for position, item in enumerate(payload.items)
    ]
    db.commit()
    db.refresh(invoice)
    return invoice


@router.delete("/invoices/{invoice_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_invoice(invoice_id: str, principal: ManagerPrincipal, db: DbSession) -> Response:
    invoice = db.scalar(
        select(Invoice).where(
            Invoice.id == invoice_id,
            Invoice.organization_id == principal.organization_id,
        )
    )
    if invoice is None:
        raise HTTPException(status_code=404, detail="Invoice not found")
    db.delete(invoice)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def _timesheet_row(entry: TimesheetEntry, db: Session) -> dict:
    user = db.get(OrganizationUser, entry.user_id)
    property_record = db.get(Property, entry.property_id) if entry.property_id else None
    return {
        "id": entry.id,
        "organization_id": entry.organization_id,
        "user_id": entry.user_id,
        "employee_name": user.display_name if user else "Unknown employee",
        "property_id": entry.property_id,
        "property_name": property_record.name if property_record else None,
        "started_at": entry.started_at,
        "ended_at": entry.ended_at,
        "status": entry.status,
        "notes": entry.notes,
        "created_at": entry.created_at,
    }


def _utc_datetime(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


@router.post(
    "/timesheets/clock-in",
    response_model=TimesheetRead,
    status_code=status.HTTP_201_CREATED,
)
def clock_in(payload: TimesheetStart, principal: CurrentPrincipal, db: DbSession) -> dict:
    running = db.scalar(
        select(TimesheetEntry).where(
            TimesheetEntry.organization_id == principal.organization_id,
            TimesheetEntry.user_id == principal.user_id,
            TimesheetEntry.status == "running",
        )
    )
    if running is not None:
        raise HTTPException(status_code=409, detail="A shift is already running")
    if payload.property_id:
        property_record = db.scalar(
            select(Property).where(
                Property.id == payload.property_id,
                Property.organization_id == principal.organization_id,
            )
        )
        if property_record is None:
            raise HTTPException(status_code=404, detail="Property not found")
    started_at = _utc_datetime(payload.started_at) if payload.started_at else datetime.now(UTC)
    if started_at > datetime.now(UTC) + timedelta(minutes=5):
        raise HTTPException(status_code=422, detail="Clock-in time cannot be in the future")
    entry = TimesheetEntry(
        organization_id=principal.organization_id,
        user_id=principal.user_id,
        property_id=payload.property_id,
        notes=payload.notes,
        started_at=started_at,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return _timesheet_row(entry, db)


@router.post("/timesheets/{entry_id}/clock-out", response_model=TimesheetRead)
def clock_out(
    entry_id: str,
    principal: CurrentPrincipal,
    db: DbSession,
    payload: TimesheetStop | None = None,
) -> dict:
    entry = db.scalar(
        select(TimesheetEntry).where(
            TimesheetEntry.id == entry_id,
            TimesheetEntry.organization_id == principal.organization_id,
        )
    )
    if entry is None:
        raise HTTPException(status_code=404, detail="Timesheet entry not found")
    is_manager = principal.role in {OrganizationRole.ADMIN, OrganizationRole.MANAGER}
    if entry.user_id != principal.user_id and not is_manager:
        raise HTTPException(status_code=403, detail="Insufficient permission")
    if entry.status != "running":
        raise HTTPException(status_code=409, detail="Shift is not running")
    ended_at = (
        _utc_datetime(payload.ended_at) if payload and payload.ended_at else datetime.now(UTC)
    )
    started_at = _utc_datetime(entry.started_at)
    if ended_at <= started_at:
        raise HTTPException(status_code=422, detail="Clock-out must be after clock-in")
    if ended_at > datetime.now(UTC) + timedelta(minutes=5):
        raise HTTPException(status_code=422, detail="Clock-out time cannot be in the future")
    entry.ended_at = ended_at
    entry.status = "submitted"
    db.commit()
    db.refresh(entry)
    return _timesheet_row(entry, db)


@router.get("/timesheets", response_model=list[TimesheetRead])
def list_timesheets(principal: CurrentPrincipal, db: DbSession) -> list[dict]:
    statement = select(TimesheetEntry).where(
        TimesheetEntry.organization_id == principal.organization_id
    )
    if principal.role not in {OrganizationRole.ADMIN, OrganizationRole.MANAGER}:
        statement = statement.where(TimesheetEntry.user_id == principal.user_id)
    entries = list(db.scalars(statement.order_by(TimesheetEntry.started_at.desc())))
    return [_timesheet_row(entry, db) for entry in entries]


@router.post("/timesheets/{entry_id}/approve", response_model=TimesheetRead)
def approve_timesheet(entry_id: str, principal: ManagerPrincipal, db: DbSession) -> dict:
    entry = db.scalar(
        select(TimesheetEntry).where(
            TimesheetEntry.id == entry_id,
            TimesheetEntry.organization_id == principal.organization_id,
        )
    )
    if entry is None:
        raise HTTPException(status_code=404, detail="Timesheet entry not found")
    if entry.status != "submitted":
        raise HTTPException(status_code=409, detail="Only submitted timesheets can be approved")
    entry.status = "approved"
    db.commit()
    db.refresh(entry)
    return _timesheet_row(entry, db)
