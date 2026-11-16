import importlib.util
from pathlib import Path

from groundsops.config import get_settings
from groundsops.storage import get_object_storage

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"


def _load(name: str):
    spec = importlib.util.spec_from_file_location(name.replace("-", "_"), SCRIPTS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_demo_leads_with_a_real_before_and_after_concept(client, monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "demo_workspace_enabled", True)
    monkeypatch.setattr(settings, "auth_mode", "development")
    seed = _load("seed-demo-workspace")
    seed.seed()

    token = client.post(
        "/api/v1/auth/development-token",
        json={"organization_id": seed.DEMO_ORGANIZATION_ID, "email": seed.DEMO_EMAIL},
    ).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    designs = client.get("/api/v1/design-projects", headers=headers).json()
    assert designs[0]["name"] == "Backyard lawn renovation"
    captures = client.get(
        f"/api/v1/design-projects/{designs[0]['id']}/captures", headers=headers
    ).json()
    assert len(captures) == 1
    photo = client.get(f"/api/v1/captures/{captures[0]['id']}/content", headers=headers)
    assert photo.status_code == 200 and photo.content[:3] == b"\xff\xd8\xff"

    jobs = client.get(
        f"/api/v1/design-projects/{designs[0]['id']}/generations", headers=headers
    ).json()
    job = jobs[0]
    assert job["status"] == "succeeded"
    assert job["estimated_area"] is not None and job["calibration_unit"] == "ft"
    for part in ("output", "mask"):
        response = client.get(f"/api/v1/generations/{job['id']}/{part}", headers=headers)
        assert response.status_code == 200, part
    estimate = client.get(
        f"/api/v1/generations/{job['id']}/material-estimate", headers=headers
    ).json()
    assert estimate["material_type"] == "sod" and float(estimate["total"]) > 0
    reviews = client.get(f"/api/v1/generations/{job['id']}/reviews", headers=headers).json()
    assert reviews[0]["decision"] == "approved"

    # The nightly reset removes the seeded files along with the rows.
    _load("reset-demo-workspace").reset(confirmed=True)
    storage = get_object_storage()
    leftovers = [
        path for path in storage.root.rglob("*")
        if path.is_file() and seed.DEMO_ORGANIZATION_ID in str(path) and "branding" not in str(path)
    ]
    assert leftovers == []
