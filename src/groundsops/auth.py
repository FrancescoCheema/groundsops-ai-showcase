from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import InvalidTokenError, PyJWKClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from groundsops.config import get_settings
from groundsops.db import get_db
from groundsops.models import Organization, OrganizationRole, OrganizationUser
from groundsops.subscription import has_workspace_access

bearer_scheme = HTTPBearer(auto_error=False)
READ_ONLY_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})
# Billing must stay reachable so an expired workspace can subscribe.
BILLING_EXEMPT_PREFIXES = ("/api/v1/billing",)


@dataclass(frozen=True)
class AuthenticatedPrincipal:
    user_id: str
    organization_id: str
    email: str
    role: OrganizationRole
    platform_admin: bool = False


@dataclass(frozen=True)
class VerifiedIdentity:
    subject: str
    email: str
    display_name: str


def ensure_development_auth() -> None:
    if get_settings().auth_mode != "development":
        raise HTTPException(status_code=404, detail="Not found")


def create_development_token(user: OrganizationUser) -> tuple[str, int]:
    settings = get_settings()
    if settings.auth_mode != "development":
        raise RuntimeError("Development tokens are disabled")
    now = datetime.now(UTC)
    expires_at = now + timedelta(minutes=settings.jwt_ttl_minutes)
    payload = {
        "sub": user.id,
        "organization_id": user.organization_id,
        "email": user.email,
        "role": user.role,
        "iss": settings.jwt_issuer,
        "aud": settings.jwt_audience,
        "iat": now,
        "exp": expires_at,
    }
    token = jwt.encode(payload, settings.jwt_secret, algorithm="HS256")
    return token, settings.jwt_ttl_minutes * 60


def create_development_signup_token(email: str, display_name: str) -> tuple[str, int]:
    settings = get_settings()
    if settings.auth_mode != "development":
        raise RuntimeError("Development tokens are disabled")
    now = datetime.now(UTC)
    expires_at = now + timedelta(minutes=settings.jwt_ttl_minutes)
    payload = {
        "sub": f"development:{email.lower()}",
        "email": email.lower(),
        "name": display_name,
        "signup": True,
        "iss": settings.jwt_issuer,
        "aud": settings.jwt_audience,
        "iat": now,
        "exp": expires_at,
    }
    token = jwt.encode(payload, settings.jwt_secret, algorithm="HS256")
    return token, settings.jwt_ttl_minutes * 60


def _decode_token(token: str) -> dict:
    settings = get_settings()
    try:
        if settings.auth_mode == "development":
            return jwt.decode(
                token,
                settings.jwt_secret,
                algorithms=["HS256"],
                issuer=settings.jwt_issuer,
                audience=settings.jwt_audience,
            )
        if not settings.oidc_jwks_url:
            raise HTTPException(status_code=503, detail="OIDC is not configured")
        signing_key = PyJWKClient(settings.oidc_jwks_url).get_signing_key_from_jwt(token)
        return jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            issuer=settings.jwt_issuer,
            audience=settings.jwt_audience,
        )
    except HTTPException:
        raise
    except InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


def _token_claims(
    credentials: HTTPAuthorizationCredentials | None,
) -> dict:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return _decode_token(credentials.credentials)


def get_verified_identity(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> VerifiedIdentity:
    claims = _token_claims(credentials)
    settings = get_settings()
    if not claims.get("sub") or not claims.get("email"):
        raise HTTPException(status_code=401, detail="Token is missing identity claims")
    if settings.auth_mode == "development":
        if claims.get("signup") is not True:
            raise HTTPException(status_code=401, detail="A signup token is required")
    elif claims.get("token_use") != "id" or claims.get("email_verified") is not True:
        raise HTTPException(status_code=401, detail="A verified Cognito ID token is required")
    return VerifiedIdentity(
        subject=claims["sub"],
        email=claims["email"].lower(),
        display_name=(claims.get("name") or claims["email"].split("@", 1)[0])[:200],
    )


def get_current_principal(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    db: Annotated[Session, Depends(get_db)],
) -> AuthenticatedPrincipal:
    claims = _token_claims(credentials)
    settings = get_settings()
    required_claims = (
        ("sub", "organization_id", "email")
        if settings.auth_mode == "development"
        else ("sub", "email")
    )
    if any(not claims.get(claim) for claim in required_claims):
        raise HTTPException(status_code=401, detail="Token is missing required claims")
    if settings.auth_mode != "development" and (
        claims.get("token_use") != "id" or claims.get("email_verified") is not True
    ):
        raise HTTPException(status_code=401, detail="A verified Cognito ID token is required")
    if settings.auth_mode == "development":
        user = db.scalar(
            select(OrganizationUser).where(
                OrganizationUser.organization_id == claims["organization_id"],
                OrganizationUser.email == claims["email"].lower(),
                OrganizationUser.active.is_(True),
                OrganizationUser.deleted_at.is_(None),
            )
        )
    else:
        user = db.scalar(
            select(OrganizationUser).where(
                OrganizationUser.cognito_subject == claims["sub"],
                OrganizationUser.active.is_(True),
                OrganizationUser.deleted_at.is_(None),
            )
        )
        if user is None:
            candidates = list(
                db.scalars(
                    select(OrganizationUser).where(
                        OrganizationUser.email == claims["email"].lower(),
                        OrganizationUser.cognito_subject.is_(None),
                        OrganizationUser.active.is_(True),
                        OrganizationUser.deleted_at.is_(None),
                    )
                )
            )
            if len(candidates) == 1:
                user = candidates[0]
                user.cognito_subject = claims["sub"]
                db.commit()
    if user is None:
        raise HTTPException(status_code=401, detail="User is inactive or token is stale")
    if settings.auth_mode == "development":
        if user.id != claims["sub"] or user.role != claims.get("role"):
            raise HTTPException(status_code=401, detail="User is inactive or token is stale")
    try:
        role = OrganizationRole(user.role)
    except ValueError as exc:
        raise HTTPException(status_code=403, detail="Unknown role") from exc
    groups = claims.get("cognito:groups") or []
    platform_admin = (
        claims.get("platform_admin") is True
        if settings.auth_mode == "development"
        else "groundsops-platform-admins" in groups
    )
    if (
        settings.billing_enabled
        and not platform_admin
        and request.method not in READ_ONLY_METHODS
        and not request.url.path.startswith(BILLING_EXEMPT_PREFIXES)
    ):
        organization = db.get(Organization, user.organization_id)
        if organization is not None and not has_workspace_access(organization):
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail="Your trial has ended. Start a subscription to keep making changes.",
            )
    return AuthenticatedPrincipal(
        user_id=user.id,
        organization_id=user.organization_id,
        email=user.email,
        role=role,
        platform_admin=platform_admin,
    )


CurrentPrincipal = Annotated[AuthenticatedPrincipal, Depends(get_current_principal)]
SignupIdentity = Annotated[VerifiedIdentity, Depends(get_verified_identity)]


def require_roles(*roles: OrganizationRole) -> Callable:
    allowed = set(roles)

    def authorize(principal: CurrentPrincipal) -> AuthenticatedPrincipal:
        if principal.role not in allowed:
            raise HTTPException(status_code=403, detail="Insufficient permission")
        return principal

    return authorize


def require_platform_admin(
    principal: CurrentPrincipal,
) -> AuthenticatedPrincipal:
    if not principal.platform_admin:
        raise HTTPException(status_code=403, detail="Platform administrator required")
    return principal


AdminPrincipal = Annotated[
    AuthenticatedPrincipal,
    Depends(require_roles(OrganizationRole.ADMIN)),
]
ManagerPrincipal = Annotated[
    AuthenticatedPrincipal,
    Depends(require_roles(OrganizationRole.ADMIN, OrganizationRole.MANAGER)),
]
DesignerPrincipal = Annotated[
    AuthenticatedPrincipal,
    Depends(
        require_roles(
            OrganizationRole.ADMIN,
            OrganizationRole.MANAGER,
            OrganizationRole.DESIGNER,
        )
    ),
]
PlatformPrincipal = Annotated[
    AuthenticatedPrincipal,
    Depends(require_platform_admin),
]
