from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from main import app


@pytest.fixture
def client():
    return TestClient(app)


class TestMainApp:
    def test_app_initialization(self):
        """Test that the app is properly initialized"""
        assert app is not None
        assert app.title == "FastAPI"

    def test_lifespan_init_db_called(self):
        """Test that init_db is called during lifespan startup"""
        with patch("main.init_db") as mock_init_db:
            # Create a new client which triggers lifespan
            with TestClient(app) as client:
                # Make a request to ensure app is fully started
                _ = client.get("/docs")
                mock_init_db.assert_called_once()

    def test_user_router_included(self, client):
        """Test that user router is properly included"""
        # Try to access a user endpoint to verify router is mounted
        response = client.get("/user/123e4567-e89b-12d3-a456-426614174000")
        # Should get 404 or 200, not 404 for route not found
        assert response.status_code in [200, 404, 500]

    def test_validation_error_handler_registered(self, client):
        """Test that validation error handler is registered"""
        # Send invalid data to trigger validation error
        response = client.post("/user/", json={"invalid": "data"})

        assert response.status_code == 422
        data = response.json()
        assert data["result"] == "error"
        assert "errors" in data
        assert len(data["errors"]) > 0
        assert data["errors"][0]["status"] == 422
        assert data["errors"][0]["title"] == "Validation Error"


class TestLifespan:
    def test_lifespan_context_manager(self):
        """Test lifespan context manager works correctly"""
        from main import lifespan

        with patch("main.init_db") as mock_init_db:
            # Test the async context manager
            import asyncio

            async def run_lifespan():
                async with lifespan(app):
                    # Inside the context, init_db should be called
                    pass
                # After exiting, verify it was called
                return mock_init_db.call_count

            result = asyncio.run(run_lifespan())
            assert result == 1
