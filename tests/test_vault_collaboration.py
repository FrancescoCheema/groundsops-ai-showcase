from datetime import UTC, datetime, timedelta
from io import BytesIO
from zipfile import ZipFile


def _upload(client, headers, name="crew-plan.txt") -> dict:
    response = client.post(
        "/api/v1/vault/files",
        headers=headers,
        files={"file": (name, b"Private site instructions", "text/plain")},
    )
    assert response.status_code == 201
    return response.json()


def test_vault_preview_rename_share_and_recycle(client, create_identity):
    _, headers = create_identity("Vault Landscaping")
    file = _upload(client, headers)

    preview = client.get(
        f"/api/v1/vault/files/{file['id']}/content?preview=true",
        headers=headers,
    )
    assert preview.status_code == 200
    assert preview.headers["content-disposition"].startswith("inline")
    assert preview.headers["x-content-type-options"] == "nosniff"

    renamed = client.put(
        f"/api/v1/vault/files/{file['id']}/name",
        headers=headers,
        json={"name": "Monday crew plan.txt"},
    )
    assert renamed.status_code == 200
    assert renamed.json()["original_filename"] == "Monday crew plan.txt"

    share = client.post(
        f"/api/v1/vault/files/{file['id']}/shares",
        headers=headers,
        json={"expires_in_hours": 1},
    )
    assert share.status_code == 200
    public = client.get(f"/api/v1/vault/shared/{share.json()['url_token']}")
    assert public.status_code == 200
    assert public.content == b"Private site instructions"

    assert client.delete(f"/api/v1/vault/files/{file['id']}", headers=headers).status_code == 204
    assert client.get("/api/v1/vault/files", headers=headers).json() == []
    recycled = client.get(
        "/api/v1/vault/files?recycle_bin=true", headers=headers
    ).json()
    assert recycled[0]["id"] == file["id"]
    assert client.get(f"/api/v1/vault/shared/{share.json()['url_token']}").status_code == 404

    restored = client.post(
        f"/api/v1/vault/files/{file['id']}/restore", headers=headers
    )
    assert restored.status_code == 200
    assert restored.json()["deleted_at"] is None


def test_timesheet_accepts_specific_start_and_end(client, create_identity):
    _, headers = create_identity("Custom Time Landscaping")
    start = datetime.now(UTC) - timedelta(hours=2)
    end = start + timedelta(hours=1, minutes=30)
    started = client.post(
        "/api/v1/timesheets/clock-in",
        headers=headers,
        json={"started_at": start.isoformat()},
    )
    assert started.status_code == 201

    stopped = client.post(
        f"/api/v1/timesheets/{started.json()['id']}/clock-out",
        headers=headers,
        json={"ended_at": end.isoformat()},
    )
    assert stopped.status_code == 200
    assert stopped.json()["status"] == "submitted"


def test_folder_controls_share_download_and_recycle(client, create_identity):
    _, headers = create_identity("Folder Controls Landscaping")
    folder = client.post(
        "/api/v1/vault/folders",
        headers=headers,
        json={"name": "Job documents", "site_id": None},
    ).json()
    upload = client.post(
        "/api/v1/vault/files",
        headers=headers,
        data={"folder_id": folder["id"]},
        files={"file": ("scope.txt", b"Patio scope", "text/plain")},
    )
    assert upload.status_code == 201

    renamed = client.put(
        f"/api/v1/vault/containers/folders/{folder['id']}/name",
        headers=headers,
        json={"name": "Patio documents"},
    )
    assert renamed.json()["name"] == "Patio documents"
    access = client.put(
        f"/api/v1/vault/containers/folders/{folder['id']}/access",
        headers=headers,
        json={"access_scope": "management"},
    )
    assert access.json()["access_scope"] == "management"

    archive = client.get(
        f"/api/v1/vault/containers/folders/{folder['id']}/download", headers=headers
    )
    assert archive.status_code == 200
    with ZipFile(BytesIO(archive.content)) as zipped:
        assert zipped.read(zipped.namelist()[0]) == b"Patio scope"

    share = client.post(
        f"/api/v1/vault/containers/folders/{folder['id']}/shares",
        headers=headers,
        json={"expires_in_hours": 1},
    )
    assert client.get(
        f"/api/v1/vault/shared-container/{share.json()['url_token']}"
    ).status_code == 200

    assert client.delete(
        f"/api/v1/vault/containers/folders/{folder['id']}", headers=headers
    ).status_code == 204
    assert client.get(
        "/api/v1/vault/folders?recycle_bin=true", headers=headers
    ).json()[0]["id"] == folder["id"]
    assert client.post(
        f"/api/v1/vault/containers/folders/{folder['id']}/restore", headers=headers
    ).status_code == 204
