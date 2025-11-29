import datetime
import uuid
from typing import Generator
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from src.models import Status
from src.models.database import Materials, Project, User
from src.routes.materials import MaterialRouter
from src.utils import get_session


@pytest.fixture(name="session")
def session_fixture() -> Generator[Session, None, None]:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


@pytest.fixture(name="client")
def client_fixture(session: Session) -> Generator[TestClient, None, None]:
    with patch("src.routes.materials.log") as mock_log:
        app = FastAPI()
        app.include_router(MaterialRouter())

        def get_session_override():
            return session

        app.dependency_overrides[get_session] = get_session_override
        yield TestClient(app)


@pytest.fixture(name="sample_user")
def sample_user_fixture(session: Session) -> User:
    user = User(user_id=uuid.uuid4(), name="Test User", email="test@example.com")
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


@pytest.fixture(name="sample_project")
def sample_project_fixture(session: Session, sample_user: User) -> Project:
    project = Project(
        project_id=uuid.uuid4(),
        user_id=sample_user.user_id,
        name="Test Project",
        description="A test project",
        start_date=datetime.datetime.now(),
        end_date=datetime.datetime.now(),
        status=Status.PENDING,
    )
    session.add(project)
    session.commit()
    session.refresh(project)
    return project


@pytest.fixture(name="sample_material")
def sample_material_fixture(session: Session, sample_project: Project) -> Materials:
    material = Materials(
        material_id=uuid.uuid4(),
        project_id=sample_project.project_id,
        name="Steel Rod",
        qty_needed=10,
        qty_acquired=5,
        unit="pcs",
    )
    session.add(material)
    session.commit()
    session.refresh(material)
    return material


class TestGetMaterial:
    def test_get_existing_material(
        self, client: TestClient, sample_material: Materials
    ):
        response = client.get(f"/material/{sample_material.material_id}")
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["id"] == str(sample_material.material_id)
        assert data["name"] == sample_material.name

    def test_get_nonexistent_material(self, client: TestClient):
        response = client.get(f"/material/{uuid.uuid4()}")
        assert response.status_code == 404

    def test_get_material_invalid_uuid(self, client: TestClient):
        response = client.get("/material/invalid-uuid")
        assert response.status_code == 422


class TestCreateMaterial:
    def test_create_material_success(self, client: TestClient, sample_project: Project):
        payload = {
            "project_id": str(sample_project.project_id),
            "name": "Galvanized Steel",
            "qty_needed": 5,
            "qty_acquired": 2,
            "unit": "kg",
        }
        response = client.post("/material/", json=payload)
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["name"] == payload["name"]
        assert data["qty_needed"] == payload["qty_needed"]
        assert data["qty_acquired"] == payload["qty_acquired"]
        assert data["unit"] == payload["unit"]

    def test_create_material_missing_required(self, client: TestClient):
        payload = {"name": "Incomplete Material"}
        response = client.post("/material/", json=payload)
        assert response.status_code == 422


class TestUpdateMaterial:
    def test_update_material_name(self, client: TestClient, sample_material: Materials):
        payload = {"name": "Updated Name"}
        response = client.patch(
            f"/material/{sample_material.material_id}", json=payload
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["name"] == payload["name"]

    def test_update_material_nonexistent(self, client: TestClient):
        payload = {"name": "Ghost"}
        response = client.patch(f"/material/{uuid.uuid4()}", json=payload)
        assert response.status_code == 404

    def test_update_material_invalid_uuid(self, client: TestClient):
        response = client.patch("/material/invalid-uuid", json={"name": "x"})
        assert response.status_code == 422


class TestDeleteMaterial:
    def test_delete_existing_material(
        self, client: TestClient, sample_material: Materials
    ):
        response = client.delete(f"/material/{sample_material.material_id}")
        assert response.status_code == 200
        # Verify deletion
        get_response = client.get(f"/material/{sample_material.material_id}")
        assert get_response.status_code == 404

    def test_delete_nonexistent_material(self, client: TestClient):
        response = client.delete(f"/material/{uuid.uuid4()}")
        assert response.status_code == 404

    def test_delete_material_invalid_uuid(self, client: TestClient):
        response = client.delete("/material/invalid-uuid")
        assert response.status_code == 422
