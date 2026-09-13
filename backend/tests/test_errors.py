"""Unit tests for exception handling and standard error envelopes."""

from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel, Field

from backend.app.core.exceptions import (
    ConflictException,
    InfrastructureException,
    NotFoundException,
    ValidationException,
)
from backend.app.core.middleware import RequestIdMiddleware, register_exception_handlers

# Create isolated error test app with middleware and handlers
err_app = FastAPI()
err_app.add_middleware(RequestIdMiddleware)
register_exception_handlers(err_app)


class SamplePayload(BaseModel):
    name: str = Field(min_length=3)
    age: int = Field(ge=0)


@err_app.get("/test/not-found")
def route_not_found():
    raise NotFoundException("University", "0191eb70-0000-7000-8000-000000000001")


@err_app.get("/test/conflict")
def route_conflict():
    raise ConflictException(
        "University with code 'KU' already exists.",
        details={"code": "KU"},
    )


@err_app.get("/test/validation")
def route_validation():
    raise ValidationException(
        "Invalid checkpoint configuration",
        details={"step": -1},
    )


@err_app.get("/test/infrastructure")
def route_infrastructure():
    raise InfrastructureException("Database connection timed out.")


@err_app.post("/test/pydantic-validation")
def route_pydantic(payload: SamplePayload):
    return {"status": "ok"}


@err_app.get("/test/unhandled")
def route_unhandled():
    raise RuntimeError("Secret DB password or internal crash trace")


client = TestClient(err_app, raise_server_exceptions=False)


def test_not_found_envelope() -> None:
    """Verify NotFoundException formats into standard envelope with 404."""
    res = client.get("/test/not-found")
    assert res.status_code == 404
    data = res.json()
    assert "error" in data
    assert data["error"]["code"] == "NOT_FOUND"
    assert "University" in data["error"]["message"]
    assert data["error"]["details"]["entity"] == "University"
    assert "request_id" in data["error"]
    assert res.headers.get("X-Request-ID") == data["error"]["request_id"]


def test_conflict_envelope() -> None:
    """Verify ConflictException formats into standard envelope with 409."""
    res = client.get("/test/conflict")
    assert res.status_code == 409
    data = res.json()
    assert data["error"]["code"] == "CONFLICT"
    assert data["error"]["details"]["code"] == "KU"


def test_validation_exception_envelope() -> None:
    """Verify ValidationException formats into standard envelope with 422."""
    res = client.get("/test/validation")
    assert res.status_code == 422
    data = res.json()
    assert data["error"]["code"] == "VALIDATION_ERROR"


def test_infrastructure_exception_envelope() -> None:
    """Verify InfrastructureException formats into standard envelope with 503."""
    res = client.get("/test/infrastructure")
    assert res.status_code == 503
    data = res.json()
    assert data["error"]["code"] == "INFRASTRUCTURE_ERROR"


def test_pydantic_request_validation_error() -> None:
    """Verify FastAPI/Pydantic validation errors map to standard VALIDATION_ERROR envelope."""
    res = client.post("/test/pydantic-validation", json={"name": "a", "age": -5})
    assert res.status_code == 422
    data = res.json()
    assert data["error"]["code"] == "VALIDATION_ERROR"
    assert "details" in data["error"]
    errors = data["error"]["details"]["errors"]
    assert len(errors) >= 1
    fields = [e["field"] for e in errors]
    assert "name" in fields or "age" in fields


def test_unhandled_exception_suppresses_traceback() -> None:
    """Verify 500 errors suppress internal tracebacks, error messages, and credentials."""
    res = client.get("/test/unhandled")
    assert res.status_code == 500
    data = res.json()
    assert data["error"]["code"] == "INTERNAL_SERVER_ERROR"
    # Ensure sensitive crash string is not exposed
    assert "Secret DB password" not in res.text
    assert "RuntimeError" not in res.text
    assert "Traceback" not in res.text
