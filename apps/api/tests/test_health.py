import os

import pytest
from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_root_health_uses_standard_success_envelope() -> None:
    response = client.get("/health", headers={"x-request-id": "test-request"})

    assert response.status_code == 200
    assert response.headers["x-request-id"] == "test-request"
    assert response.json() == {
        "success": True,
        "data": {
            "service": "api",
            "status": "ok",
            "environment": "local",
            "checks": {},
        },
        "request_id": "test-request",
    }


def test_request_id_is_generated_when_missing() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.headers["x-request-id"]
    assert response.json()["request_id"] == response.headers["x-request-id"]


@pytest.mark.skipif(
    os.getenv("RUN_DB_TESTS") != "1",
    reason="Set RUN_DB_TESTS=1 when Postgres is running for the integration health check.",
)
def test_database_health_check_succeeds_when_database_is_available() -> None:
    response = client.get("/api/health/db")

    assert response.status_code == 200
    assert response.json()["success"] is True
    assert response.json()["data"]["checks"]["database"] == "ok"
