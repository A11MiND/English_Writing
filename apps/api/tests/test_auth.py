import os

import pytest
from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_protected_endpoint_rejects_unauthenticated_request() -> None:
    response = client.get("/api/protected/teacher")

    assert response.status_code == 401
    assert response.json()["success"] is False
    assert response.json()["error_code"] == "AUTH_REQUIRED"


@pytest.mark.skipif(
    os.getenv("RUN_DB_TESTS") != "1",
    reason="Set RUN_DB_TESTS=1 when Postgres is running for auth integration tests.",
)
def test_teacher_can_login_and_access_teacher_endpoint() -> None:
    session = TestClient(app)

    login_response = session.post(
        "/api/auth/login",
        json={"email": "teacher@wfjosephlee.edu.hk", "password": "Password123!"},
    )
    assert login_response.status_code == 200
    assert login_response.json()["data"]["user"]["role"] == "TEACHER"
    assert "eaiwp_session" in session.cookies

    protected_response = session.get("/api/protected/teacher")
    assert protected_response.status_code == 200
    assert protected_response.json()["data"]["scope"] == "teacher"


@pytest.mark.skipif(
    os.getenv("RUN_DB_TESTS") != "1",
    reason="Set RUN_DB_TESTS=1 when Postgres is running for auth integration tests.",
)
def test_wrong_role_is_rejected() -> None:
    session = TestClient(app)
    session.post(
        "/api/auth/login",
        json={"email": "student@wfjosephlee.edu.hk", "password": "Password123!"},
    )

    response = session.get("/api/protected/teacher")

    assert response.status_code == 403
    assert response.json()["error_code"] == "ACCESS_DENIED"


@pytest.mark.skipif(
    os.getenv("RUN_DB_TESTS") != "1",
    reason="Set RUN_DB_TESTS=1 when Postgres is running for auth integration tests.",
)
def test_suspended_and_archived_accounts_cannot_login() -> None:
    for email in ["suspended@wfjosephlee.edu.hk", "archived@wfjosephlee.edu.hk"]:
        response = client.post(
            "/api/auth/login",
            json={"email": email, "password": "Password123!"},
        )

        assert response.status_code == 403
        assert response.json()["error_code"] == "ACCESS_DENIED"


@pytest.mark.skipif(
    os.getenv("RUN_DB_TESTS") != "1",
    reason="Set RUN_DB_TESTS=1 when Postgres is running for auth integration tests.",
)
def test_logout_invalidates_session() -> None:
    session = TestClient(app)
    session.post(
        "/api/auth/login",
        json={"email": "admin@wfjosephlee.edu.hk", "password": "Password123!"},
    )

    logout_response = session.post("/api/auth/logout")
    assert logout_response.status_code == 200

    me_response = session.get("/api/auth/me")
    assert me_response.status_code == 401
    assert me_response.json()["error_code"] == "AUTH_REQUIRED"
