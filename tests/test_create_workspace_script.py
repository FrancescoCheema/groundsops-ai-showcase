import importlib.util
from pathlib import Path

from groundsops.config import get_settings

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "create-workspace.py"


def _load():
    spec = importlib.util.spec_from_file_location("create_workspace", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def signup_headers(client, email: str, name: str = "Owner Name") -> dict[str, str]:
    token = client.post(
        "/api/v1/auth/development-signup-token", json={"email": email, "display_name": name}
    ).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_script_bootstraps_first_workspace_and_owner_can_join(client, capsys, monkeypatch):
    monkeypatch.setattr(get_settings(), "app_public_url", "https://app.example.com/")
    script = _load()

    assert script.main(["--name", "GroundsOps", "--owner-email", "Owner@Example.com"]) == 0
    output = capsys.readouterr().out
    link = output.strip().splitlines()[-1]
    assert link.startswith("https://app.example.com/?invite=")
    token = link.split("?invite=", 1)[1]

    accepted = client.post(
        "/api/v1/invitations/accept",
        headers=signup_headers(client, "owner@example.com"),
        json={"token": token},
    )
    assert accepted.status_code == 201
    assert accepted.json()["role"] == "admin"


def test_script_refuses_an_email_already_in_a_workspace(client, create_identity, capsys):
    create_identity("Existing Company")
    script = _load()

    exit_code = script.main(
        ["--name", "Second", "--owner-email", "existing-company@example.com"]
    )

    assert exit_code == 1
    assert "already belongs" in capsys.readouterr().err
