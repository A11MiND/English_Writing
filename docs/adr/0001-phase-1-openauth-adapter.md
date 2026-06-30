# ADR 0001: Phase 1 OpenAuth-Compatible Adapter

Status: Accepted

## Context

The PRD requires OpenAuth-based authentication, HTTP-only application sessions, role mapping, tenant mapping and login audit logs.

## Decision

Phase 1 implements an `OpenAuthAdapter` boundary in the FastAPI backend. The runtime adapter exchanges credentials with configured OpenAuth token and userinfo endpoints and returns a subject containing `user_id`, `school_id` and `role`.

The application database remains the source of truth for user profile, role, school tenant and account status. The adapter owns only authentication proof.

## Consequences

- Phase 1 login/RBAC UAT requires configured OpenAuth endpoints.
- RBAC dependencies and protected business APIs remain isolated from provider details.
- Test authentication doubles are limited to `apps/api/tests` dependency overrides.
- Before production/UAT sign-off, the OpenAuth package/provider version must be locked and configured.
