from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "GroundsOps AI"
    app_env: str = "development"
    database_url: str = "sqlite:///./groundsops.db"
    log_level: str = "INFO"
    auth_mode: str = "development"
    demo_workspace_enabled: bool = False
    rate_limit_enabled: bool = False
    rate_limit_requests: int = Field(default=240, ge=10, le=10000)
    rate_limit_window_seconds: int = Field(default=60, ge=1, le=3600)
    jwt_issuer: str = "groundsops-local"
    jwt_audience: str = "groundsops-api"
    jwt_secret: str = "replace-with-a-long-random-local-development-secret"
    jwt_ttl_minutes: int = 60
    oidc_jwks_url: str | None = None
    storage_backend: str = "local"
    storage_root: str = "./var/uploads"
    storage_signed_url_ttl_seconds: int = Field(default=300, ge=60, le=3600)
    s3_bucket: str | None = None
    s3_region: str = "ca-central-1"
    s3_endpoint_url: str | None = None
    s3_force_path_style: bool = False
    s3_access_key_id: str | None = None
    s3_secret_access_key: str | None = None
    s3_kms_key_id: str | None = None
    s3_server_side_encryption: str = "AES256"
    image_max_bytes: int = 10 * 1024 * 1024
    vault_max_bytes: int = 25 * 1024 * 1024
    vault_quota_bytes: int = 1024 * 1024 * 1024
    malware_scan_enabled: bool = False
    malware_scan_required: bool = True
    clamav_host: str = "clamav"
    clamav_port: int = Field(default=3310, ge=1, le=65535)
    clamav_timeout_seconds: float = Field(default=10.0, ge=0.5, le=120)
    image_max_pixels: int = 25_000_000
    inference_provider: str = "disabled"
    replicate_api_token: str | None = None
    replicate_model_version: str | None = None
    # Prompt adherence for FLUX Fill (1.5-100). Replicate's default is 60; low values
    # let the model ignore the requested material and continue the surrounding scene.
    replicate_guidance: float = Field(default=60.0, ge=1.5, le=100)
    inference_timeout_seconds: int = 180
    inference_max_attempts: int = 3
    inference_monthly_budget_usd: float = 10.0
    inference_estimated_job_cost_usd: float = 0.10
    replicate_cost_per_second_usd: float = 0.000975
    replicate_cost_per_output_usd: float = 0.05
    evaluation_masked_change_min: float = Field(default=0.20, ge=0, le=1)
    evaluation_protected_change_max: float = Field(default=0.08, ge=0, le=1)
    evaluation_pixel_change_threshold: float = Field(default=0.05, ge=0, le=1)
    billing_enabled: bool = False
    billing_trial_days: int = Field(default=14, ge=0, le=365)
    billing_plan_name: str = "GroundsOps Pro"
    billing_webhook_tolerance_seconds: int = Field(default=300, ge=30, le=3600)
    stripe_secret_key: str | None = None
    stripe_webhook_secret: str | None = None
    stripe_price_id: str | None = None
    stripe_api_base: str = "https://api.stripe.com"
    stripe_automatic_tax: bool = False
    app_public_url: str = "http://localhost:3000"
    cors_origin_regex: str = (
        r"^(capacitor|ionic)://localhost$|^https?://(localhost|127\.0\.0\.1|"
        r"10\.[0-9.]+|192\.168\.[0-9.]+|"
        r"172\.(1[6-9]|2[0-9]|3[01])\.[0-9.]+)(:[0-9]+)?$"
    )

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
