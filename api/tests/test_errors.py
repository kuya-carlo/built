import json
from unittest.mock import MagicMock

import pytest
from fastapi import Request
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError

from src.utils import error_handler, error_response


@pytest.fixture(autouse=True)
def mock_logger(mocker):
    """
    Automatically patches the log function to prevent database write errors
    when running tests that mock the request state (like error tests).
    """
    mocker.patch("src.utils.errors.log")


class TestErrorResponse:
    def test_single_error(self):
        """Test error_response with a single error"""
        errors = [{"status": 404, "title": "Not Found", "detail": "Users not found"}]

        response = error_response(errors, 404)

        assert response.status_code == 404
        data = json.loads(response.body.decode())
        assert data["result"] == "error"
        assert len(data["errors"]) == 1
        assert data["errors"][0]["status"] == 404
        assert data["errors"][0]["title"] == "Not Found"
        assert data["errors"][0]["detail"] == "Users not found"

    def test_multiple_errors(self):
        """Test error_response with multiple errors"""
        errors = [
            {"status": 422, "title": "Validation Error", "detail": "Name is required"},
            {"status": 422, "title": "Validation Error", "detail": "Email is invalid"},
        ]

        response = error_response(errors, 422)

        assert response.status_code == 422
        data = json.loads(response.body.decode())
        assert data["result"] == "error"
        assert len(data["errors"]) == 2

    def test_default_status_code(self):
        """Test error_response with default status code"""
        errors = [
            {"status": 500, "title": "Internal Error", "detail": "Something went wrong"}
        ]

        response = error_response(errors)

        assert response.status_code == 500

    def test_custom_status_code(self):
        """Test error_response with custom status code"""
        errors = [
            {"status": 409, "title": "Conflict", "detail": "Resource already exists"}
        ]

        response = error_response(errors, 409)

        assert response.status_code == 409


class TestValidationExceptionHandler:
    @pytest.mark.asyncio
    async def test_request_validation_error(self):
        """Test handling of RequestValidationError"""
        # Create a mock request
        mock_request = MagicMock(spec=Request)

        # Create a RequestValidationError
        # This simulates Pydantic validation errors
        from pydantic import BaseModel, Field

        class TestModel(BaseModel):
            name: str = Field(..., min_length=1)
            email: str

        try:
            TestModel(name="", email="")
        except ValidationError as e:
            exc = RequestValidationError(e.errors())

        response = await error_handler(mock_request, exc)

        assert response.status_code == 422
        data = json.loads(response.body.decode())
        assert data["result"] == "error"
        assert len(data["errors"]) > 0
        assert data["errors"][0]["status"] == 422
        assert data["errors"][0]["title"] == "Validation Error"
        assert "detail" in data["errors"][0]

    @pytest.mark.asyncio
    async def test_request_validation_error_field_location(self):
        """Test that field location is included in error detail"""
        mock_request = MagicMock(spec=Request)

        from pydantic import BaseModel

        class TestModel(BaseModel):
            name: str
            email: str

        try:
            TestModel(email="test")  # Missing 'name'
        except ValidationError as e:
            exc = RequestValidationError(e.errors())

        response = await error_handler(mock_request, exc)

        data = json.loads(response.body.decode())
        # Check that the field name appears in the detail
        assert any("name" in err["detail"].lower() for err in data["errors"])

    @pytest.mark.asyncio
    async def test_non_validation_error(self):
        """Test handling of non-RequestValidationError exceptions"""
        mock_request = MagicMock(spec=Request)
        exc = Exception("Some random error")

        response = await error_handler(mock_request, exc)

        assert response.status_code == 500  # Changed from 422 to 500
        data = json.loads(response.body.decode())
        assert data["result"] == "error"
        assert len(data["errors"]) == 1
        assert data["errors"][0]["status"] == 500
        assert data["errors"][0]["title"] == "Internal Server Error"
        assert "Some random error" in data["errors"][0]["detail"]

    @pytest.mark.asyncio
    async def test_validation_error_with_nested_fields(self):
        """Test validation error with nested field locations"""
        mock_request = MagicMock(spec=Request)
        exc = None
        from pydantic import BaseModel

        class Address(BaseModel):
            street: str
            city: str

        class Person(BaseModel):
            name: str
            address: Address

        try:
            Person(name="John", address={"street": "123 Main"})  # Missing city
        except ValidationError as e:
            exc = RequestValidationError(e.errors())

        if exc:
            response = await error_handler(mock_request, exc)

            data = json.loads(response.body.decode())
            assert data["result"] == "error"
            # Should contain nested field path like "address.city"
            assert any("address" in err["detail"] for err in data["errors"])
