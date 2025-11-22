import uuid
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError

from src.models import User, get_session
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
