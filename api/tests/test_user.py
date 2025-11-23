import uuid
from datetime import datetime
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError

from src.models import Project, ProjectAttribute, Status, User, get_session
from src.routes.user import UserRouter


@pytest.fixture
def app():
    app = FastAPI()
    app.include_router(UserRouter())
    return app


@pytest.fixture
def client(app):
    return TestClient(app)


@pytest.fixture
def mock_session():
    return MagicMock()


@pytest.fixture
def override_session(app, mock_session):
    app.dependency_overrides[get_session] = lambda: mock_session
    yield mock_session
    app.dependency_overrides.clear()


class TestGetUser:
    def test_success(self, client, override_session):
        user_id = uuid.uuid4()
        mock_user = User(user_id=user_id, name="Test", email="test@example.com")

        override_session.get.return_value = mock_user
        override_session.exec.return_value.all.return_value = []

        response = client.get(f"/user/{user_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["result"] == "ok"
        assert data["data"]["id"] == str(user_id)
        assert data["data"]["name"] == "Test"
        assert data["data"]["email"] == "test@example.com"
        assert data["data"]["projects"] == []

    def test_not_found(self, client, override_session):
        user_id = uuid.uuid4()
        override_session.get.return_value = None

        response = client.get(f"/user/{user_id}")

        assert response.status_code == 404
        data = response.json()
        assert data["result"] == "error"
        assert data["errors"][0]["status"] == 404
        assert "not found" in data["errors"][0]["detail"].lower()

    def test_invalid_uuid(self, client):
        response = client.get("/user/not-a-uuid")
        assert response.status_code == 422

    def test_server_error(self, client, override_session):
        user_id = uuid.uuid4()
        override_session.get.side_effect = Exception("DB error")

        response = client.get(f"/user/{user_id}")

        assert response.status_code == 500
        data = response.json()
        assert data["result"] == "error"
        assert data["errors"][0]["status"] == 500


class TestCreateUser:
    def test_success(self, client, override_session):
        override_session.get.return_value = None

        response = client.post(
            "/user/",
            json={"name": "New User", "email": "new@example.com"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["result"] == "ok"
        assert data["data"]["name"] == "New User"
        assert data["data"]["email"] == "new@example.com"
        override_session.add.assert_called_once()
        override_session.commit.assert_called_once()

    def test_with_custom_id(self, client, override_session):
        user_id = uuid.uuid4()
        override_session.get.return_value = None

        response = client.post(
            "/user/",
            json={
                "name": "Custom ID",
                "email": "custom@example.com",
                "user_id": str(user_id),
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["result"] == "ok"

    def test_duplicate_id(self, client, override_session):
        user_id = uuid.uuid4()
        existing = User(user_id=user_id, name="Existing", email="exist@example.com")
        override_session.get.return_value = existing

        response = client.post(
            "/user/",
            json={
                "name": "Duplicate",
                "email": "dup@example.com",
                "user_id": str(user_id),
            },
        )

        assert response.status_code == 409
        data = response.json()
        assert data["result"] == "error"
        assert data["errors"][0]["status"] == 409

    def test_missing_name(self, client):
        response = client.post("/user/", json={"email": "noname@example.com"})
        assert response.status_code == 422

    def test_missing_email(self, client):
        response = client.post("/user/", json={"name": "No Email"})
        assert response.status_code == 422

    def test_empty_body(self, client):
        response = client.post("/user/", json={})
        assert response.status_code == 422

    def test_integrity_error(self, client, override_session):
        override_session.get.return_value = None
        override_session.commit.side_effect = IntegrityError(
            "dup", None, Exception("UNIQUE constraint failed")
        )

        response = client.post(
            "/user/",
            json={"name": "Dup", "email": "dup@example.com"},
        )

        assert response.status_code == 422
        data = response.json()
        assert data["result"] == "error"
        override_session.rollback.assert_called_once()

    def test_server_error(self, client, override_session):
        override_session.get.return_value = None
        override_session.commit.side_effect = Exception("DB connection failed")

        response = client.post(
            "/user/",
            json={"name": "Error", "email": "error@example.com"},
        )

        assert response.status_code == 500
        data = response.json()
        assert data["result"] == "error"
        assert data["errors"][0]["status"] == 500
        override_session.rollback.assert_called_once()


class TestCreateUserEdgeCases:
    def test_empty_name_string(self, client, override_session):
        """Test with empty name string"""
        response = client.post(
            "/user/",
            json={"name": "", "email": "test@example.com"},
        )

        assert response.status_code == 422
        data = response.json()
        assert "name and email are required" in data["errors"][0]["detail"]

    def test_empty_email_string(self, client, override_session):
        """Test with empty email string"""
        response = client.post(
            "/user/",
            json={"name": "Test", "email": ""},
        )

        assert response.status_code == 422
        data = response.json()
        assert "name and email are required" in data["errors"][0]["detail"]

    def test_both_empty_strings(self, client, override_session):
        """Test with both fields as empty strings"""
        response = client.post(
            "/user/",
            json={"name": "", "email": ""},
        )

        assert response.status_code == 422


class TestParseUser:
    def test_parse_user_without_projects(self):
        """Test _parse_user without projects"""
        user_id = uuid.uuid4()
        user = User(user_id=user_id, name="Alice", email="alice@example.com")

        result = UserRouter._parse_user(user)

        assert result.data.id == user_id
        assert result.data.name == "Alice"
        assert result.data.email == "alice@example.com"
        assert result.data.projects == []

    def test_parse_user_with_projects(self):
        """Test _parse_user with projects"""
        user_id = uuid.uuid4()
        user = User(user_id=user_id, name="Bob", email="bob@example.com")

        projects = [
            ProjectAttribute(
                id=uuid.uuid4(),
                user_id=user_id,
                name="Project 1",
                description="Desc 1",
                start_date=datetime(2024, 1, 1),
                end_date=datetime(2024, 12, 31),
                status=Status.PENDING,
            )
        ]

        result = UserRouter._parse_user(user, projects)

        assert result.data.id == user_id
        assert len(result.data.projects) == 1
        assert result.data.projects[0].name == "Project 1"

    def test_parse_user_with_none_projects(self):
        """Test _parse_user with None projects explicitly"""
        user_id = uuid.uuid4()
        user = User(user_id=user_id, name="Charlie", email="charlie@example.com")

        result = UserRouter._parse_user(user, None)

        assert result.data.projects == []


class TestCreateUserValidationError:
    def test_validation_error_during_commit(self, client, override_session):
        """Test ValidationError handling during commit - COVERS THE ROLLBACK"""
        override_session.get.return_value = None

        # Create a ValidationError to simulate Pydantic validation failure
        from pydantic import BaseModel, Field

        class DummyModel(BaseModel):
            value: int = Field(..., gt=0)

        try:
            DummyModel(value=-1)
        except ValidationError as validation_err:
            override_session.commit.side_effect = validation_err

        response = client.post(
            "/user/",
            json={"name": "Test", "email": "test@example.com"},
        )

        assert response.status_code == 409
        data = response.json()
        assert data["result"] == "error"
        assert data["errors"][0]["status"] == 409
        assert data["errors"][0]["title"] == "Conflict in data"

        # Verify rollback was called
        override_session.rollback.assert_called_once()


class TestParseProjects:
    def test_parse_empty_projects(self):
        """Test parsing empty project list"""
        result = UserRouter._parse_projects([])
        assert result == []
        assert isinstance(result, list)

    def test_parse_single_project(self):
        """Test parsing a single project"""
        project_id = uuid.uuid4()
        user_id = uuid.uuid4()
        start_date = datetime(2024, 1, 1)
        end_date = datetime(2024, 12, 31)

        project = Project(
            project_id=project_id,
            user_id=user_id,
            name="Test Project",
            description="Test Description",
            start_date=start_date,
            end_date=end_date,
            status=Status.PENDING,
        )

        result = UserRouter._parse_projects([project])

        assert len(result) == 1
        assert isinstance(result[0], ProjectAttribute)
        assert result[0].id == project_id
        assert result[0].user_id == user_id
        assert result[0].name == "Test Project"
        assert result[0].description == "Test Description"
        assert result[0].start_date == start_date
        assert result[0].end_date == end_date
        assert result[0].status == Status.PENDING

    def test_parse_multiple_projects(self):
        """Test parsing multiple projects - THIS COVERS THE APPEND LINE"""
        user_id = uuid.uuid4()

        projects = [
            Project(
                project_id=uuid.uuid4(),
                user_id=user_id,
                name=f"Project {i}",
                description=f"Description {i}",
                start_date=datetime(2024, 1, 1),
                end_date=datetime(2024, 12, 31),
                status="in_progress",
            )
            for i in range(3)
        ]

        result = UserRouter._parse_projects(projects)

        assert len(result) == 3
        for i, parsed in enumerate(result):
            assert isinstance(parsed, ProjectAttribute)
            assert parsed.name == f"Project {i}"
            assert parsed.description == f"Description {i}"
            assert parsed.user_id == user_id

    def test_parse_project_with_none_values(self):
        """Test parsing project with optional None values"""
        start_date = datetime.now()
        end_date = datetime.now()
        project = Project(
            project_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            name="Minimal Project",
            description="",  # Optional field
            start_date=start_date,
            end_date=end_date,
            status=Status.PENDING,
        )

        result = UserRouter._parse_projects([project])

        assert len(result) == 1
        assert result[0].description == ""
        assert result[0].start_date == start_date
        assert result[0].end_date == end_date
        assert result[0].status == Status.PENDING
