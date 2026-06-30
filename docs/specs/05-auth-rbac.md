# 05 Auth RBAC

Status: Phase 1 implemented baseline.

## Authoritative Sources

- `docs/source_extracted/Product Requirements Document(1).md`
- `docs/source_extracted/Technical Proposal.md`

## Required Roles

- `SYSTEM_ADMIN`
- `SCHOOL_ADMIN`
- `TEACHER`
- `STUDENT`

## Scope

Phase 1 establishes the authentication and authorization baseline required before school data, writing tasks and submissions are implemented.

The platform uses an OpenAuth adapter boundary. Runtime authentication exchanges credentials with configured OpenAuth token and userinfo endpoints. Test-only seeded identities are injected through pytest dependency overrides and are not runtime defaults.

## Data Model

Phase 1 creates the minimum identity tables required for authentication and audit:

- `schools`: tenant root for W F Joseph Lee Primary School and future school-owned filtering.
- `users`: application source of truth for role, school mapping and account status.
- `user_sessions`: HTTP-only application sessions established after OpenAuth-compatible authentication succeeds.
- `audit_logs`: immutable login/logout/access-control audit events.

Account status values:

- `ACTIVE`
- `SUSPENDED`
- `ARCHIVED`

Only `ACTIVE` users can establish or continue a session.

## Authentication Flow

1. User submits email and password to `POST /api/auth/login`.
2. API validates credentials through `OpenAuthAdapter`.
3. API resolves the returned subject against `users`.
4. API denies suspended or archived users.
5. API creates a `user_sessions` row.
6. API sets HTTP-only session cookie `eaiwp_session`.
7. API writes login audit log.
8. API returns the authenticated user profile through the standard response envelope.

Logout invalidates the current session, clears the cookie and writes logout audit log.

## API Contract

### `POST /api/auth/login`

Request:

```json
{
  "email": "teacher@example.edu.hk",
  "password": "string"
}
```

Success data:

```json
{
  "user": {
    "id": "uuid",
    "email": "teacher@example.edu.hk",
    "display_name": "Teacher Name",
    "role": "TEACHER",
    "school_id": "uuid",
    "status": "ACTIVE"
  }
}
```

### `POST /api/auth/logout`

Invalidates the current session. Requires authentication.

### `GET /api/auth/me`

Returns current authenticated user. Requires authentication.

### `GET /api/protected/{role}`

Phase 1 test endpoint used to verify RBAC for `admin`, `teacher` and `student`.

## RBAC Rules

- Every protected endpoint must validate an active session.
- Every protected endpoint must validate role requirements.
- Any school-owned data access must include `school_id` filter.
- Teacher-specific future data access must filter by assigned classes.
- Student-specific future data access must filter by `student_id`.
- Tokens or session identifiers must not be stored in browser local storage.
- Production cookies must use `Secure`, `HttpOnly` and `SameSite` protection.

## Test Identities

Phase tests seed application users and use a pytest-only OpenAuth dependency override for login validation:

- `admin@wfjosephlee.edu.hk` / `Password123!` / `SCHOOL_ADMIN`
- `teacher@wfjosephlee.edu.hk` / `Password123!` / `TEACHER`
- `student@wfjosephlee.edu.hk` / `Password123!` / `STUDENT`
- `suspended@wfjosephlee.edu.hk` / `Password123!` / `STUDENT`, denied
- `archived@wfjosephlee.edu.hk` / `Password123!` / `TEACHER`, denied

These accounts are for automated tests only. UAT login must use real OpenAuth identities that map to the same application users.

## Acceptance Criteria

- Teacher can login and is redirected to teacher dashboard.
- Student can login and is redirected to student home.
- School admin can login and is redirected to admin console.
- Suspended account cannot access app.
- Archived account cannot access app.
- Protected API rejects unauthenticated requests with `AUTH_REQUIRED`.
- Protected API rejects wrong role with `ACCESS_DENIED`.
- Logout invalidates the current application session.
- Login and logout are written to audit logs.
