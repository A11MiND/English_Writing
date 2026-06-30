import json

import pytest
from fastapi import HTTPException

from auth_service.hash_password import hash_password
from auth_service.main import IdentityStore, Settings


def user_payload(email: str = "test.user@example.edu") -> dict:
    return {
        "email": email,
        "password_hash": hash_password("Password123!", iterations=1_000),
        "sub": "11111111-2222-4333-8444-555555555555",
        "school_id": "aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee",
        "role": "STUDENT",
        "status": "ACTIVE",
    }


def test_identity_store_loads_users_from_json_env() -> None:
    row = user_payload()

    store = IdentityStore.from_settings(Settings(openauth_users_json=json.dumps([row])))

    authenticated = store.authenticate("TEST.USER@example.edu", "Password123!")
    assert authenticated.email == row["email"]
    assert authenticated.user_id == row["sub"]


def test_identity_store_loads_users_from_json_file(tmp_path) -> None:
    row = user_payload("file.user@example.edu")
    path = tmp_path / "openauth-users.json"
    path.write_text(json.dumps([row]), encoding="utf-8")

    store = IdentityStore.from_settings(
        Settings(openauth_users_json="[]", openauth_users_json_file=str(path))
    )

    authenticated = store.authenticate("file.user@example.edu", "Password123!")
    assert authenticated.role == "STUDENT"
    assert authenticated.school_id == row["school_id"]


def test_identity_store_rejects_suspended_file_user(tmp_path) -> None:
    row = {**user_payload("suspended@example.edu"), "status": "SUSPENDED"}
    path = tmp_path / "openauth-users.json"
    path.write_text(json.dumps([row]), encoding="utf-8")
    store = IdentityStore.from_settings(Settings(openauth_users_json_file=str(path)))

    with pytest.raises(HTTPException) as exc:
        store.authenticate("suspended@example.edu", "Password123!")

    assert exc.value.status_code == 403
