# 13 Deployment Operations

Status: Local/UAT baseline through Phase 9 scaffold. Production deployment details are deferred.

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

## Remaining Deployment Work

- Managed PostgreSQL/Redis sizing and backups.
- Production OpenAuth provider/identity source.
- Worker process supervision, dead-letter handling and metrics.
- Central logs, audit log retention and incident runbooks.
- UAT data reset procedure and seed management.
- Production PDF styling and email delivery setup.
