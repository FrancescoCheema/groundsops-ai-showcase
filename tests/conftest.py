import os

os.environ["DATABASE_URL"] = "sqlite:///./test_groundsops.db"
os.environ["STORAGE_ROOT"] = "./var/test-uploads"
os.environ["AUTH_MODE"] = "development"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from groundsops.db import Base, engine  # noqa: E402
from groundsops.main import app  # noqa: E402
from groundsops.storage import get_object_storage  # noqa: E402


@pytest.fixture(autouse=True)
def clean_database():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)
    storage = get_object_storage()
    if storage.root.exists():
        for path in sorted(storage.root.rglob("*"), reverse=True):
            if path.is_file():
                path.unlink()
            elif path.is_dir():
                path.rmdir()


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def create_identity(client):
    def factory(name: str, role: str = "admin") -> tuple[str, dict[str, str]]:
        bootstrap_response = client.post(
            "/api/v1/auth/development-bootstrap",
            json={
                "organization_name": name,
                "admin_email": f"{name.lower().replace(' ', '-')}@example.com",
                "admin_display_name": "Admin User",
            },
        )
        assert bootstrap_response.status_code == 201
        organization_id = bootstrap_response.json()["organization_id"]
        admin_token = bootstrap_response.json()["access_token"]
        admin_headers = {"Authorization": f"Bearer {admin_token}"}
        if role == "admin":
            return organization_id, admin_headers

        email = f"{role}-{organization_id}@example.com"
        user_response = client.post(
            "/api/v1/users",
            headers=admin_headers,
            json={
                "email": email,
                "display_name": f"{role.title()} User",
                "role": role,
            },
        )
        assert user_response.status_code == 201
        token_response = client.post(
            "/api/v1/auth/development-token",
            json={"organization_id": organization_id, "email": email},
        )
        assert token_response.status_code == 200
        return organization_id, {
            "Authorization": f"Bearer {token_response.json()['access_token']}"
        }

    return factory
