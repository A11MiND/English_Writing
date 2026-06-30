from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from http.cookiejar import CookieJar


API_BASE_URL = os.getenv("STRESS_API_BASE_URL", "http://127.0.0.1:8000")
PASSWORD = os.getenv("STRESS_PASSWORD", "Password123!")


class Session:
    def __init__(self) -> None:
        self.cookies = CookieJar()
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.cookies))

    def request(self, method: str, path: str, payload: dict | None = None) -> tuple[int, bytes]:
        data = None
        headers = {"accept": "application/json"}
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")
            headers["content-type"] = "application/json"
        request = urllib.request.Request(
            f"{API_BASE_URL}{path}",
            data=data,
            headers=headers,
            method=method,
        )
        try:
            response = self.opener.open(request, timeout=30)
            return response.status, response.read()
        except urllib.error.HTTPError as exc:
            return exc.code, exc.read()

    def login(self, email: str, password: str = PASSWORD) -> None:
        status, body = self.request("POST", "/api/auth/login", {"email": email, "password": password})
        if status != 200:
            raise RuntimeError(f"Login failed for {email}: {status} {body[:200]!r}")
