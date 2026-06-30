# 13 Deployment Operations

Status: Local/UAT baseline validated from `/Users/allmind/Desktop/Edcosys2025/EngWriting`. Production deployment details are deferred.

## Authoritative Sources

- `docs/source_extracted/Technical Proposal.md`
- `docs/source_extracted/Product Requirements Document(1).md`

## Phase 0 Operations

- Local development runs through Docker Compose.
- Secrets are represented through `.env.example`; production credentials must not be committed.
- PostgreSQL and Redis are local containers for development.
- Docker Compose runs web, api, auth, marking-worker, PostgreSQL, Redis and LanguageTool-compatible grammar service.
- Runtime AI marking requires real `LLM_PROVIDER`, `LLM_MODEL` and `LLM_API_KEY`.
- Runtime auth uses `apps/auth` locally/UAT and can be replaced by a compatible OpenAuth provider.

## Current Local/UAT Operations

- The active working directory is `/Users/allmind/Desktop/Edcosys2025/EngWriting`.
- Local Git is initialized with checkpoint commits recorded in `docs/development-plan.md`.
- Docker Compose runs `web`, `api`, `auth`, `marking-worker`, `postgres`, `redis` and `grammar-service`.
- Alembic migrations through `0008_phase_8_reports` pass on the migrated stack.
- API tests, web/shared tests, TypeScript lint and Playwright E2E pass from the migrated directory.
- `.env`, dependency directories, build caches and test results are ignored by Git.

## UAT Evidence Locations

- Readiness gate: `docs/uat-readiness.md`
- Development tracker: `docs/development-plan.md`
- UI productization matrix: `docs/design/ui-productization-matrix.md`
- Stress and export evidence: `docs/uat-evidence/`
- Traceability snapshot: `docs/specs/14-requirements-traceability.md`

## Remaining Deployment Work

- Managed PostgreSQL/Redis sizing and backups.
- Production OpenAuth provider/identity source.
- Worker process supervision, dead-letter handling and metrics.
- Central logs, audit log retention and incident runbooks.
- UAT data reset procedure and seed management.
- Production PDF styling and email delivery setup.
