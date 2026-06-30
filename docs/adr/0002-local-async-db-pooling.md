# ADR 0002: Local Async Database Pooling

## Status

Accepted for Phase 2 local development.

## Context

The FastAPI backend uses SQLAlchemy async with asyncpg. During Docker integration tests, Starlette `TestClient` creates separate event loops across test client instances. Reusing pooled asyncpg connections across those loops produced `Future attached to a different loop` errors.

Phase 2 needs stable local tests and hot-reload behavior before production deployment tuning.

## Decision

Set `DATABASE_POOL_ENABLED=false` by default and create the SQLAlchemy async engine with `NullPool` unless pooling is explicitly enabled.

## Consequences

- Local tests and development avoid event-loop connection reuse failures.
- Each database session opens a fresh connection, which is acceptable for Phase 2 pilot development.
- Production deployment must revisit connection pooling in `docs/specs/13-deployment-operations.md` before UAT hardening.
