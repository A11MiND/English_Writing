# 12 Testing Acceptance

Status: UAT core E2E and stress evidence captured on 2026-06-29.

## Authoritative Sources

- `docs/source_extracted/Spec-driven Development Specification.md`
- `docs/source_extracted/Product Requirements Document(1).md`

## Phase 0 Acceptance

- Docker Compose starts PostgreSQL, Redis, API and web services.
- Backend health endpoints return the standard API response envelope.
- Frontend can call backend health endpoint.
- Alembic can upgrade to the baseline revision.
- README documents local setup.

## AI Marking Foundation Tests

- LLM adapter unit tests cover provider registry, OpenAI-compatible request shape, invalid JSON rejection, missing API key rejection and prompt identity exclusion.
- LLM adapter unit tests cover `minimax` provider defaults for MiniMax-M3.
- Marking queue unit tests cover enqueue, dequeue and pending count without real Redis.
- Marking workflow integration test covers submission-created queued marking result, teacher-run configured LLM marking and teacher review override.
- Database-backed marking workflow tests require `RUN_DB_TESTS=1`.

## Phase 5 Grammar Suggestion Tests

- Grammar service unit tests cover normalized suggestion spans and Redis cache reuse.
- Suggestion API tests cover unauthenticated rejection.
- Database-backed suggestion API tests cover Practice Mode normalized suggestions and Exam Mode rejection.
- Frontend unit tests cover suggestion text-span replacement.
- Database-backed suggestion API tests require `RUN_DB_TESTS=1`.

## Phase 8 Report Tests

- Report API tests cover unauthenticated rejection.
- Database-backed report tests cover teacher generation, CSV export, PDF export and unassigned class denial.
- Export tests verify content type and generated file signatures.

## Phase 9 E2E And Stress Scaffold

- `tests/e2e` contains Playwright UAT coverage for admin CSV import, teacher task creation/assignment, student Practice suggestion accept/submit, Exam paste block/timer auto-submit, real DeepSeek marking, teacher review/release, student feedback/exercise completion and report CSV/PDF export.
- `tests/stress/uat_load.py` runs a real-service stress pass for 150 logins, 100 concurrent writing users with autosave and suggestions, 470 submissions, 470 queued marking jobs and teacher report generation.
- Stress evidence is written as JSONL under `docs/uat-evidence/<date>/`.
- The recorded local OpenAuth stress pass uses the seeded student credential repeatedly.
- Generated-student tooling now supports provisioning matching OpenAuth identities through `external_user_id`, importing generated users through the real admin API, importing generated UAT rubrics/tasks/assignments through the real teacher APIs and rerunning stress with `STRESS_STUDENT_CREDENTIALS_CSV`.
- The 470 marking queue stress pass intentionally does not drain all jobs through the live LLM provider to avoid uncontrolled paid calls. Worker drain and provider rate-limit testing should be run as a separate approved costed test.
- `scripts/uat/generate_minimax_uat_data.py` can generate fictional UAT fixture CSV and writing content with MiniMax-M3 when `MINIMAX_API_KEY` is provided in the local environment.
- `scripts/uat/apply_uat_fixtures.py` prepares `openauth-users.combined.env`, `stress-student-credentials.csv` and optional real API imports for users and writing fixtures.
- `scripts/uat/check_uat_gate.py` checks required UAT evidence, report exports, stress scenario pass flags and optional strict requirements for distinct-student stress and generated writing fixture import.

## Latest Acceptance Commands

```bash
docker compose exec -T web pnpm --dir apps/web exec tsc --noEmit
docker compose exec -T web pnpm test
docker compose exec -T api env RUN_DB_TESTS=1 RUN_LLM_TESTS=1 pytest apps/api/tests
docker compose --profile e2e run --rm e2e
docker compose stop marking-worker
STRESS_API_BASE_URL=http://127.0.0.1:8000 STRESS_EVIDENCE_DIR=docs/uat-evidence/2026-06-29 python tests/stress/uat_load.py
python -m pytest tests/unit/test_uat_fixture_scripts.py
python scripts/uat/check_uat_gate.py
python scripts/uat/check_uat_gate.py --require-distinct-student-stress --require-writing-fixtures-applied
STRESS_STUDENT_CREDENTIALS_CSV=tests/fixtures/uat/minimax/stress-student-credentials.csv STRESS_API_BASE_URL=http://127.0.0.1:8000 STRESS_EVIDENCE_DIR=docs/uat-evidence/2026-06-29 python tests/stress/uat_load.py
docker compose exec -T redis redis-cli DEL marking:jobs
docker compose start marking-worker
```
