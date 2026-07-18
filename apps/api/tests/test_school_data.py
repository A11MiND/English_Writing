import os
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_admin_school_data_rejects_unauthenticated_request() -> None:
    response = client.get("/api/admin/classes")

    assert response.status_code == 401
    assert response.json()["success"] is False
    assert response.json()["error_code"] == "AUTH_REQUIRED"


@pytest.mark.skipif(
    os.getenv("RUN_DB_TESTS") != "1",
    reason="Set RUN_DB_TESTS=1 when Postgres is running for school data integration tests.",
)
def test_admin_can_list_seeded_classes() -> None:
    session = TestClient(app)
    session.post(
        "/api/auth/login",
        json={"email": "admin@school.example", "password": "Password123!"},
    )

    response = session.get("/api/admin/classes")

    assert response.status_code == 200
    class_names = [row["name"] for row in response.json()["data"]["classes"]]
    assert {"P4A", "P5A", "P6A"}.issubset(set(class_names))


@pytest.mark.skipif(
    os.getenv("RUN_DB_TESTS") != "1",
    reason="Set RUN_DB_TESTS=1 when Postgres is running for school data integration tests.",
)
def test_teacher_can_only_list_assigned_classes() -> None:
    session = TestClient(app)
    session.post(
        "/api/auth/login",
        json={"email": "teacher@school.example", "password": "Password123!"},
    )

    response = session.get("/api/teacher/classes")

    assert response.status_code == 200
    class_names = [row["name"] for row in response.json()["data"]["classes"]]
    assert class_names == ["P4A", "P5A", "P6A"]


@pytest.mark.skipif(
    os.getenv("RUN_DB_TESTS") != "1",
    reason="Set RUN_DB_TESTS=1 when Postgres is running for school data integration tests.",
)
def test_student_profile_is_scoped_to_current_student() -> None:
    session = TestClient(app)
    session.post(
        "/api/auth/login",
        json={"email": "student@school.example", "password": "Password123!"},
    )

    response = session.get("/api/student/profile")

    assert response.status_code == 200
    assert response.json()["data"]["profile"] == {
        "student_number": "S0001",
        "level": "P5",
        "class_name": "P5A",
    }


@pytest.mark.skipif(
    os.getenv("RUN_DB_TESTS") != "1",
    reason="Set RUN_DB_TESTS=1 when Postgres is running for school data integration tests.",
)
def test_admin_import_rejects_duplicate_email() -> None:
    session = TestClient(app)
    session.post(
        "/api/auth/login",
        json={"email": "admin@school.example", "password": "Password123!"},
    )

    response = session.post(
        "/api/admin/import/users",
        json={
            "role": "STUDENT",
            "rows": [
                {
                    "email": "student@school.example",
                    "display_name": "Duplicate Student",
                    "student_number": "S0999",
                    "level": "P5",
                    "class_name": "P5A",
                }
            ],
        },
    )

    assert response.status_code == 200
    body = response.json()["data"]
    assert body["successful_count"] == 0
    assert body["rejected_count"] == 1
    assert "Duplicate email." in body["rejected_rows"][0]["reasons"]


@pytest.mark.skipif(
    os.getenv("RUN_DB_TESTS") != "1",
    reason="Set RUN_DB_TESTS=1 when Postgres is running for school data integration tests.",
)
def test_admin_imports_valid_student() -> None:
    session = TestClient(app)
    session.post(
        "/api/auth/login",
        json={"email": "admin@school.example", "password": "Password123!"},
    )
    suffix = uuid4().hex[:8]

    response = session.post(
        "/api/admin/import/users",
        json={
            "role": "STUDENT",
            "rows": [
                {
                    "email": f"student.{suffix}@school.example",
                    "display_name": "Imported Student",
                    "student_number": f"S{suffix[:6].upper()}",
                    "level": "P5",
                    "class_name": "P5A",
                }
            ],
        },
    )

    assert response.status_code == 200
    body = response.json()["data"]
    assert body["successful_count"] == 1
    assert body["rejected_count"] == 0


@pytest.mark.skipif(
    os.getenv("RUN_DB_TESTS") != "1",
    reason="Set RUN_DB_TESTS=1 when Postgres is running for school data integration tests.",
)
def test_admin_import_can_use_external_user_id_for_openauth_subject_mapping() -> None:
    session = TestClient(app)
    session.post(
        "/api/auth/login",
        json={"email": "admin@school.example", "password": "Password123!"},
    )
    suffix = uuid4().hex[:8]
    external_user_id = str(uuid4())

    response = session.post(
        "/api/admin/import/users",
        json={
            "role": "STUDENT",
            "rows": [
                {
                    "external_user_id": external_user_id,
                    "email": f"student.external.{suffix}@school.example",
                    "display_name": "External Subject Student",
                    "student_number": f"EXT{suffix[:6].upper()}",
                    "level": "P5",
                    "class_name": "P5A",
                }
            ],
        },
    )

    assert response.status_code == 200
    assert response.json()["data"]["successful_count"] == 1

    users_response = session.get("/api/admin/users")
    imported = next(
        row
        for row in users_response.json()["data"]["users"]
        if row["email"] == f"student.external.{suffix}@school.example"
    )
    assert imported["id"] == external_user_id


@pytest.mark.skipif(
    os.getenv("RUN_DB_TESTS") != "1",
    reason="Set RUN_DB_TESTS=1 when Postgres is running for school data integration tests.",
)
def test_admin_can_suspend_and_restore_account_status() -> None:
    session = TestClient(app)
    session.post(
        "/api/auth/login",
        json={"email": "admin@school.example", "password": "Password123!"},
    )
    users_response = session.get("/api/admin/users")
    assert users_response.status_code == 200
    student = next(
        row for row in users_response.json()["data"]["users"] if row["email"] == "student@school.example"
    )

    suspend_response = session.patch(
        f"/api/admin/users/{student['id']}/status",
        json={"status": "SUSPENDED", "reason": "Integration test"},
    )
    assert suspend_response.status_code == 200
    assert suspend_response.json()["data"]["user"]["status"] == "SUSPENDED"

    restore_response = session.patch(
        f"/api/admin/users/{student['id']}/status",
        json={"status": "ACTIVE", "reason": "Integration test cleanup"},
    )
    assert restore_response.status_code == 200
    assert restore_response.json()["data"]["user"]["status"] == "ACTIVE"
