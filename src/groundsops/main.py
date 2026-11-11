import logging
import time
from uuid import uuid4

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.requests import Request
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from groundsops.api import router
from groundsops.billing import router as billing_router
from groundsops.config import get_settings
from groundsops.db import engine
from groundsops.observability import configure_logging, log_event
from groundsops.rate_limit import SlidingWindowRateLimiter
from groundsops.storage import get_object_storage

settings = get_settings()
configure_logging(settings.log_level)
logger = logging.getLogger("groundsops.requests")
app = FastAPI(title=settings.app_name, version="0.1.0")
rate_limiter = SlidingWindowRateLimiter(
    settings.rate_limit_requests,
    settings.rate_limit_window_seconds,
)
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=settings.cors_origin_regex,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
    expose_headers=["X-Request-ID"],
)
app.include_router(router)
app.include_router(billing_router)


@app.middleware("http")
async def api_rate_limit(request: Request, call_next):
    if settings.rate_limit_enabled and request.url.path.startswith("/api/"):
        forwarded = request.headers.get("X-Forwarded-For", "").split(",", 1)[0].strip()
        client = forwarded or (request.client.host if request.client else "unknown")
        allowed, retry_after = rate_limiter.allow(client)
        if not allowed:
            return JSONResponse(
                status_code=429,
                content={"detail": "Too many requests"},
                headers={"Retry-After": str(retry_after)},
            )
    return await call_next(request)


@app.middleware("http")
async def request_observability(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", "")
    if not request_id or len(request_id) > 128:
        request_id = str(uuid4())
    started_at = time.perf_counter()
    status_code = 500
    try:
        response = await call_next(request)
        status_code = response.status_code
        return response
    except Exception:
        log_event(
            logger,
            logging.ERROR,
            "request_failed",
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            duration_ms=round((time.perf_counter() - started_at) * 1000, 2),
        )
        raise
    finally:
        duration_ms = round((time.perf_counter() - started_at) * 1000, 2)
        log_event(
            logger,
            logging.INFO,
            "request_completed",
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            status_code=status_code,
            duration_ms=duration_ms,
            environment=settings.app_env,
        )
        if "response" in locals():
            response.headers["X-Request-ID"] = request_id


@app.get("/health", tags=["operations"])
def health() -> dict[str, str]:
    return {"status": "healthy"}


@app.get("/ready", tags=["operations"])
def readiness() -> dict[str, str]:
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        get_object_storage().healthcheck()
    except (SQLAlchemyError, OSError, RuntimeError):
        return JSONResponse(status_code=503, content={"status": "not_ready"})
    return {"status": "ready"}
