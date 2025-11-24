import uuid
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlmodel import Session

from src.models import ActivityLog, get_session
from src.routes.activity import ActivityLogRouter


@pytest.fixture
def mock_session():
    return MagicMock(spec=Session)


@pytest.fixture
def app(mock_session):
    router = ActivityLogRouter()
    app = FastAPI()
    app.include_router(router)

    # Override the get_session dependency
    app.dependency_overrides[get_session] = lambda: mock_session

    return app


@pytest.fixture
def client(app):
    return TestClient(app)


@pytest.fixture
def sample_activity_log():
    return ActivityLog(
        activity_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        project_id=uuid.uuid4(),
        action_type="TEST_ACTION",
        action_desc="This is a test action",
        status_code=200,
        details=None,
        timestamp="2025-11-25T00:00:00Z",
    )


class TestActivityLogRouter:
    @patch("src.routes.activity.read")
    @patch("src.routes.activity.log")
    def test_get_activity_log_success(
        self, mock_log, mock_read, client, sample_activity_log
    ):
        mock_read.return_value = sample_activity_log

        response = client.get(f"/activity_log/{sample_activity_log.activity_id}")
        data = response.json()

        assert response.status_code == 200
        assert "data" in data
        assert data["data"]["activity_id"] == str(sample_activity_log.activity_id)
        mock_read.assert_called_once()
        mock_log.assert_called_once()

    @patch("src.routes.activity.read")
    @patch("src.routes.activity.log")
    def test_get_activity_log_not_found(self, mock_log, mock_read, client):
        # Mock read to raise 404 HTTPException
        from fastapi import HTTPException

        test_id = uuid.uuid4()
        mock_read.side_effect = HTTPException(
            status_code=404, detail=f"ActivityLog with id {test_id} not found"
        )

        response = client.get(f"/activity_log/{test_id}")
        assert response.status_code == 404
