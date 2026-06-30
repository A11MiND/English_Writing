from __future__ import annotations

import hashlib
import secrets
import sys


def hash_password(password: str, iterations: int = 210_000) -> str:
    salt = secrets.token_bytes(16)
    derived = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return f"pbkdf2_sha256${iterations}${salt.hex()}${derived.hex()}"


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python -m auth_service.hash_password '<password>'")
    print(hash_password(sys.argv[1]))
