from functools import lru_cache
from pathlib import Path, PurePosixPath
from typing import Protocol
from urllib.parse import quote

from groundsops.config import get_settings


class ObjectStorage(Protocol):
    def put(self, key: str, data: bytes, content_type: str | None = None) -> None: ...
    def get(self, key: str) -> bytes: ...
    def delete(self, key: str) -> None: ...
    def signed_get_url(
        self,
        key: str,
        *,
        filename: str,
        content_type: str,
        inline: bool = False,
    ) -> str | None: ...
    def healthcheck(self) -> None: ...


def tenant_storage_key(
    organization_id: str,
    category: str,
    resource_id: str,
    filename: str,
) -> str:
    safe_name = Path(filename).name
    parts = (organization_id, category, resource_id, safe_name)
    if any(not part or part in {".", ".."} or "/" in part or "\\" in part for part in parts):
        raise ValueError("Invalid tenant storage key component")
    return str(PurePosixPath("organizations", *parts))


class LocalObjectStorage:
    def __init__(self, root: str) -> None:
        self.root = Path(root).resolve()

    def _path(self, key: str) -> Path:
        path = (self.root / key).resolve()
        if self.root not in path.parents:
            raise ValueError("Invalid storage key")
        return path

    def put(self, key: str, data: bytes, content_type: str | None = None) -> None:
        del content_type
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_bytes(data)
        temporary.replace(path)

    def get(self, key: str) -> bytes:
        return self._path(key).read_bytes()

    def delete(self, key: str) -> None:
        self._path(key).unlink(missing_ok=True)

    def signed_get_url(
        self,
        key: str,
        *,
        filename: str,
        content_type: str,
        inline: bool = False,
    ) -> None:
        del key, filename, content_type, inline
        return None

    def healthcheck(self) -> None:
        self.root.mkdir(parents=True, exist_ok=True)


class S3ObjectStorage:
    def __init__(self) -> None:
        try:
            import boto3
            from botocore.config import Config
            from botocore.exceptions import ClientError
        except ImportError as exc:
            raise RuntimeError("Install boto3 to use S3 storage") from exc

        settings = get_settings()
        if not settings.s3_bucket:
            raise RuntimeError("S3_BUCKET is required when STORAGE_BACKEND=s3")
        options: dict[str, object] = {"region_name": settings.s3_region}
        if settings.s3_endpoint_url:
            options["endpoint_url"] = settings.s3_endpoint_url
        if settings.s3_access_key_id:
            options["aws_access_key_id"] = settings.s3_access_key_id
        if settings.s3_secret_access_key:
            options["aws_secret_access_key"] = settings.s3_secret_access_key
        if settings.s3_force_path_style:
            options["config"] = Config(s3={"addressing_style": "path"})
        self.client = boto3.client("s3", **options)
        self.client_error = ClientError
        self.bucket = settings.s3_bucket
        self.ttl_seconds = settings.storage_signed_url_ttl_seconds
        self.kms_key_id = settings.s3_kms_key_id
        self.server_side_encryption = settings.s3_server_side_encryption

    def put(self, key: str, data: bytes, content_type: str | None = None) -> None:
        options: dict[str, object] = {
            "Bucket": self.bucket,
            "Key": key,
            "Body": data,
            "ContentType": content_type or "application/octet-stream",
        }
        if self.kms_key_id:
            options["ServerSideEncryption"] = "aws:kms"
            options["SSEKMSKeyId"] = self.kms_key_id
        elif self.server_side_encryption.lower() != "none":
            options["ServerSideEncryption"] = self.server_side_encryption
        self.client.put_object(**options)

    def get(self, key: str) -> bytes:
        try:
            return self.client.get_object(Bucket=self.bucket, Key=key)["Body"].read()
        except self.client_error as exc:
            if exc.response.get("Error", {}).get("Code") in {"NoSuchKey", "404"}:
                raise FileNotFoundError(key) from exc
            raise

    def delete(self, key: str) -> None:
        self.client.delete_object(Bucket=self.bucket, Key=key)

    def signed_get_url(
        self,
        key: str,
        *,
        filename: str,
        content_type: str,
        inline: bool = False,
    ) -> str:
        disposition = "inline" if inline else "attachment"
        return self.client.generate_presigned_url(
            "get_object",
            Params={
                "Bucket": self.bucket,
                "Key": key,
                "ResponseContentType": content_type,
                "ResponseContentDisposition": (
                    f"{disposition}; filename*=UTF-8''{quote(Path(filename).name)}"
                ),
            },
            ExpiresIn=self.ttl_seconds,
        )

    def healthcheck(self) -> None:
        try:
            self.client.head_bucket(Bucket=self.bucket)
        except Exception as exc:
            raise RuntimeError("S3 storage is not reachable") from exc


@lru_cache
def get_object_storage() -> ObjectStorage:
    settings = get_settings()
    if settings.storage_backend == "local":
        return LocalObjectStorage(settings.storage_root)
    if settings.storage_backend == "s3":
        return S3ObjectStorage()
    raise RuntimeError(f"Unsupported storage backend: {settings.storage_backend}")
