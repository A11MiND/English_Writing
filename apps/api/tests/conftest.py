from __future__ import annotations

from app.core.auth import OpenAuthAdapter, OpenAuthSubject, Role, get_openauth_adapter
from app.core.responses import ApiException, ErrorCode
from app.main import app


class TestOpenAuthAdapter(OpenAuthAdapter):
    password = "Password123!"
    subjects = {
        "system@edcosys.local": OpenAuthSubject(
            "22222222-2222-4222-8222-222222222222", None, Role.SYSTEM_ADMIN
        ),
        "admin@wfjosephlee.edu.hk": OpenAuthSubject(
            "33333333-3333-4333-8333-333333333333",
            "11111111-1111-4111-8111-111111111111",
            Role.SCHOOL_ADMIN,
        ),
        "teacher@wfjosephlee.edu.hk": OpenAuthSubject(
            "44444444-4444-4444-8444-444444444444",
            "11111111-1111-4111-8111-111111111111",
            Role.TEACHER,
        ),
        "other.teacher@wfjosephlee.edu.hk": OpenAuthSubject(
            "44444444-4444-4444-8444-444444444445",
            "11111111-1111-4111-8111-111111111111",
            Role.TEACHER,
        ),
        "student@wfjosephlee.edu.hk": OpenAuthSubject(
            "55555555-5555-4555-8555-555555555555",
            "11111111-1111-4111-8111-111111111111",
            Role.STUDENT,
        ),
        "other.student@wfjosephlee.edu.hk": OpenAuthSubject(
            "55555555-5555-4555-8555-555555555556",
            "11111111-1111-4111-8111-111111111111",
            Role.STUDENT,
        ),
        "suspended@wfjosephlee.edu.hk": OpenAuthSubject(
            "66666666-6666-4666-8666-666666666666",
            "11111111-1111-4111-8111-111111111111",
            Role.STUDENT,
        ),
        "archived@wfjosephlee.edu.hk": OpenAuthSubject(
            "77777777-7777-4777-8777-777777777777",
            "11111111-1111-4111-8111-111111111111",
            Role.TEACHER,
        ),
    }

    async def authenticate(self, email: str, password: str) -> OpenAuthSubject:
        subject = self.subjects.get(email.lower().strip())
        if subject is None or password != self.password:
            raise ApiException(ErrorCode.AUTH_REQUIRED, "Invalid email or password.", 401)
        return subject


def get_test_openauth_adapter() -> OpenAuthAdapter:
    return TestOpenAuthAdapter()


app.dependency_overrides[get_openauth_adapter] = get_test_openauth_adapter
