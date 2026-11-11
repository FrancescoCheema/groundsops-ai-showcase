from pathlib import Path

import pytest

from groundsops.storage import LocalObjectStorage, tenant_storage_key


def test_tenant_storage_key_is_scoped_and_strips_directories() -> None:
    key = tenant_storage_key(
        "organization-id",
        "vault",
        "file-id",
        "../../crew-plan.pdf",
    )

    assert key == "organizations/organization-id/vault/file-id/crew-plan.pdf"


@pytest.mark.parametrize(
    "component",
    ["", ".", "..", "another/tenant", "another\\tenant"],
)
def test_tenant_storage_key_rejects_invalid_scope_components(component: str) -> None:
    with pytest.raises(ValueError):
        tenant_storage_key(component, "vault", "file-id", "plan.pdf")


def test_local_storage_matches_production_interface(tmp_path: Path) -> None:
    storage = LocalObjectStorage(str(tmp_path))
    key = tenant_storage_key("org", "vault", "file", "plan.txt")

    storage.put(key, b"patio plan", "text/plain")

    assert storage.get(key) == b"patio plan"
    assert storage.signed_get_url(
        key,
        filename="plan.txt",
        content_type="text/plain",
    ) is None
    storage.healthcheck()
    storage.delete(key)
    assert not (tmp_path / key).exists()


def test_local_backend_does_not_issue_signed_url(client, create_identity) -> None:
    _, headers = create_identity("Local Signed URL Landscaping")
    uploaded = client.post(
        "/api/v1/vault/files",
        headers=headers,
        files={"file": ("scope.txt", b"Patio scope", "text/plain")},
    )

    response = client.get(
        f"/api/v1/vault/files/{uploaded.json()['id']}/signed-url",
        headers=headers,
    )

    assert response.status_code == 409
    assert response.json()["detail"].startswith("Signed URLs")
