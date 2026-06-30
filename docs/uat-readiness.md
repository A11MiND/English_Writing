# UAT Readiness Gate

Status date: 2026-06-29

This gate measures real UAT readiness against the PRD and Technical Proposal. It does not count placeholder screens, fake provider output, or skipped UAT-critical tests as pass evidence.

## Current Gate Status

| Area | Status | Evidence Required Before UAT Sign-off |
| --- | --- | --- |
| Local infrastructure | Passing | `docker compose ps` shows web, api, auth, grammar-service, marking-worker, postgres and redis running. |
| Authentication and RBAC | Passing for UAT core | Browser E2E verifies admin, teacher and student login paths; DB-backed suspended/archived-account and wrong-role rejection tests exist. |
| Core school data | Passing for UAT core | Browser E2E verifies admin CSV import with row-level result; DB-backed tests cover valid rows, invalid rows, duplicate email, class membership and teacher assigned-class filtering. |
| Task/rubric workflow | Passing for UAT core | Browser E2E creates unique Practice/Exam tasks through teacher-authenticated API, assigns them to P5A and verifies task visibility; DB tests cover draft/publish/close/archive, duplicate/archive and used-rubric edit rejection. |
| Practice Mode | Passing for UAT core | Browser E2E verifies student opens a created Practice task, receives a real LanguageTool suggestion, accepts it and submits a locked writing. |
| Exam Mode | Passing for UAT core | Browser E2E verifies student opens a created Exam task, suggestions are absent, paste is blocked, the timer is displayed and timer expiry auto-submits locked writing. |
| Grammar service | Passing for UAT core | Real LanguageTool container is used by browser E2E and API tests; no runtime fake suggestions are used. |
| AI marking | Passing for UAT core | Browser E2E runs teacher-triggered real DeepSeek marking, validates the saved result path, saves teacher review override and releases feedback. API tests cover schema validation, retry/failure behavior, essay preservation, MiniMax provider defaults and prompt hardening. |
| Feedback/exercises | Passing for UAT core | Browser E2E verifies released student feedback and post-writing exercise completion. DB-backed tests cover unreleased feedback visibility. |
| Reports/export | Passing for UAT core | Browser E2E generates a class report and downloads CSV/PDF evidence files; API tests cover CSV/PDF export, audit log and assigned-class enforcement. |
| Stress | Passing for local UAT load evidence | `tests/stress/uat_load.py` produced dated evidence for 150 logins, 100 concurrent writing users with autosave and suggestions, 470 submissions within 30 minutes, 470 queued marking jobs and teacher report generation. Latest strict evidence used 470 distinct generated OpenAuth student identities. |
| Security | Passing for UAT core | Automated checks cover HTML sanitization, prompt-injection boundary, API source scope guards, no browser local/session storage token in E2E, no student PII in LLM prompt and assigned-class/student ownership filtering. |

## Latest Verified Evidence

2026-06-29:

- `CONFIRM_RESET=RESET_UAT_DB scripts/dev/reset_uat_db.sh`: reset the local controlled-pilot database, ran Alembic through `0008_phase_8_reports`, then restarted app services.
- `docker compose --profile e2e run --rm e2e`: 7 passed. Covered admin CSV import, teacher creates and assigns unique Practice/Exam tasks, student Practice suggestion accept and submit, student Exam paste block and timer auto-submit, no token in browser local/session storage, real DeepSeek marking, teacher review override, feedback release, student feedback/exercise completion, class report generation and CSV/PDF export.
- `docker compose exec -T api env RUN_DB_TESTS=1 RUN_LLM_TESTS=1 pytest apps/api/tests`: 50 passed, 0 skipped, 1 warning. This includes Exam Mode duration validation, MiniMax provider defaults, external OpenAuth subject import support and security gate checks.
- `docker compose exec -T web pnpm --dir apps/web exec tsc --noEmit`: passed.
- `docker compose exec -T web pnpm test`: 12 passed.
- `PYTHONPATH=apps/auth python -m pytest apps/auth/tests`: 3 passed, 1 warning. This covers JSON-env identities, file-based generated identities and suspended account rejection in the OpenAuth-compatible service.
- Post-E2E cleanup: `CONFIRM_RESET=RESET_UAT_DB scripts/dev/reset_uat_db.sh` completed again after browser E2E created temporary UAT rows.
- Final post-reset verification:
  - Redis `LLEN marking:jobs`: 0.
  - `GET /api/health`: 200.
  - `GET /health` on auth: 200.
  - Seed admin login: 200 with `SCHOOL_ADMIN`.
- MiniMax support added:
  - `LLM_PROVIDER=minimax`
  - `LLM_MODEL=MiniMax-M3`
  - `LLM_BASE_URL=https://api.minimaxi.com/v1`
  - `scripts/uat/generate_minimax_uat_data.py` generates fictional students, teacher CSV, OpenAuth identity JSON and writing fixtures when `MINIMAX_API_KEY` is supplied locally.
- Distinct generated-student UAT tooling added:
  - Admin import accepts optional `external_user_id` so generated OpenAuth `sub` values can match database user IDs.
  - `scripts/uat/apply_uat_fixtures.py` prepares combined OpenAuth env snippets and can import generated CSV users through the real admin API.
  - `scripts/uat/apply_uat_fixtures.py --import-writing-fixtures` can import generated UAT rubrics, writing tasks and class assignments through the real teacher APIs while preserving teacher assigned-class RBAC.
  - `tests/stress/uat_load.py` supports `STRESS_STUDENT_CREDENTIALS_CSV` to run login, writing and submission load with distinct student credentials.
- `python -m pytest tests/unit/test_uat_fixture_scripts.py`: 2 passed, 1 warning. This covers topic normalisation and UAT writing fixture application behavior.
- `python -m pytest tests/unit/test_uat_fixture_scripts.py tests/unit/test_uat_gate.py`: 5 passed, 1 warning.
- `python scripts/uat/check_uat_gate.py`: passed against current attached stress/export evidence.
- `MINIMAX_API_KEY=<local secret> python scripts/uat/generate_minimax_uat_data.py --student-count 470 --topic-count 11 --essay-count 0 --timeout-seconds 120`: passed using MiniMax-M3. Output fixture contains 470 generated student identities and 11 generated writing topics across P4/P5/P6 and Practice/Exam.
- `python scripts/uat/apply_uat_fixtures.py --import-users --import-writing-fixtures`: passed against the real local API with 2 teachers imported, 470 students imported, 11 writing tasks created and assigned, and 0 rejected rows.
- `STRESS_STUDENT_CREDENTIALS_CSV=tests/fixtures/uat/minimax/stress-student-credentials.csv STRESS_API_BASE_URL=http://127.0.0.1:8000 STRESS_EVIDENCE_DIR=docs/uat-evidence/2026-06-29 python tests/stress/uat_load.py`: passed using distinct generated student accounts:
  - 150 distinct student logins completed in 5.17s, p95 1.051s.
  - 100 concurrent writing users completed 300 autosaves and 100 suggestion checks in 15.98s.
  - 470 distinct student submissions completed in 31.16s, p95 1.666s.
  - 470 marking jobs were queued; Redis `LLEN marking:jobs` confirmed 470 before the queue was cleared.
  - Teacher report generation and CSV export completed in 4.28s.
- `python scripts/uat/check_uat_gate.py --require-distinct-student-stress --require-writing-fixtures-applied`: passed against `docs/uat-evidence/2026-06-29/stress-20260629T070653Z.jsonl`.
- `docker compose exec -T redis redis-cli DEL marking:jobs`: cleared the stress-created marking queue before restarting the worker.
- `CONFIRM_RESET=RESET_UAT_DB scripts/dev/reset_uat_db.sh`: completed after the strict UAT run; local Postgres was dropped, recreated, migrated and reseeded.
- Post-reset verification:
  - Redis `LLEN marking:jobs`: 0.
  - `GET /api/health`: 200.
  - `GET /health` on auth: 200.
  - Seed admin login: 200 with `SCHOOL_ADMIN`.
- `STRESS_API_BASE_URL=http://127.0.0.1:8000 STRESS_EVIDENCE_DIR=docs/uat-evidence/2026-06-29 python tests/stress/uat_load.py`: passed local UAT load targets:
  - 150 login requests completed in 5.25s, p95 1.158s.
  - 100 concurrent writing users completed 300 autosaves and 100 suggestion checks in 17.91s.
  - 470 submissions completed in 29.7s, p95 1.294s.
  - 470 marking jobs were queued; Redis `LLEN marking:jobs` confirmed 470 before the stress queue was cleared.
  - Teacher report generation and CSV export completed in 0.31s with 519871 CSV bytes.
- `docker compose exec -T redis redis-cli DEL marking:jobs`: cleared the 470 stress queue before restarting the worker to avoid uncontrolled paid live LLM calls.
- Export evidence saved:
  - `docs/uat-evidence/2026-06-29/class-report-88888888-8888-4888-8888-888888888884.csv`
  - `docs/uat-evidence/2026-06-29/class-report-88888888-8888-4888-8888-888888888884.pdf`
  - `docs/uat-evidence/2026-06-29/stress-20260629T020024Z.jsonl`

2026-06-28:

- `docker compose exec -T api env RUN_DB_TESTS=1 pytest apps/api/tests/test_task_workflow.py`: 7 passed.
- `docker compose exec -T api env RUN_DB_TESTS=1 pytest apps/api/tests`: 43 passed, 1 skipped.
- `docker compose exec -T web pnpm test`: 12 passed.
- `docker compose exec -T web pnpm --dir apps/web exec tsc --noEmit`: passed.
- Browser smoke: teacher dashboard, admin console and student home render with the unified app shell; browser console had no error logs during the checked flows.
- `docker compose --profile e2e run --rm e2e`: 3 passed. This covers admin, teacher and student login routing, shared app shell, teacher rubric/task controls, admin AI status/account controls and student task entry.
- `scripts/dev/reset_uat_db.sh` was added for explicit local DB reset and reseed after DB-backed tests pollute the controlled pilot dataset. It refuses to run unless `CONFIRM_RESET=RESET_UAT_DB` is set.
- Docker E2E now uses `web-e2e` with same-origin `/api` proxying to `http://api:8000`, avoiding cross-origin session cookie failures inside the Playwright container.
- `LIVE_API_BASE_URL=http://127.0.0.1:8000 python tests/live/deepseek_marking_smoke.py`: passed with `status=AI_MARKED`, `attempts=1`.
- `docker compose exec -T api env RUN_DB_TESTS=1 RUN_LLM_TESTS=1 pytest apps/api/tests`: 44 passed, 0 skipped.

Known evidence limitations after 2026-06-29:

- 2026-06-29 hardening run:
  - `docker compose exec -T web pnpm test`: passed, 14 tests.
  - `docker compose exec -T web pnpm lint`: passed.
  - `docker compose exec -T api env RUN_DB_TESTS=1 pytest apps/api/tests/test_reports_export.py`: passed, 4 tests.
  - `docker compose exec -T api env RUN_DB_TESTS=1 pytest`: passed, 49 passed / 1 skipped.
  - E2E workspace wiring was corrected by adding `tests/*` to `pnpm-workspace.yaml`; Playwright started but the first rerun exposed a missing local Chromium binary. A subsequent browser install reached download completion but hung during install finalization, and the final rerun using an existing Chrome for Testing binary was blocked by the execution environment approval limit. Do not count browser E2E as passed for this hardening run.
- 2026-06-29 review/API hardening run:
  - `docker compose exec -T api env RUN_DB_TESTS=1 pytest apps/api/tests/test_marking_workflow.py`: passed, 2 passed / 1 skipped.
  - `docker compose exec -T api env RUN_DB_TESTS=1 pytest`: passed, 50 passed / 1 skipped.
  - `pnpm lint`: passed.
  - Teacher review override now enforces 0-5 dimension scores, 0-15 total score, total-score consistency and release-only-through-release-endpoint semantics.
  - `docs/specs/11-uiux-screen-spec.md` now includes the UI productization page matrix required before Catalyst-style visual work begins.
- 2026-06-29 E2E repair run:
  - `E2E_BASE_URL=http://localhost:3000 E2E_API_BASE_URL=http://localhost:8000 PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH=<local Chrome for Testing> pnpm --filter @english-ai-writing/e2e test`: passed, 7 passed.
  - Fixed host-run E2E API requests so browser setup calls use `E2E_API_BASE_URL` instead of accidentally hitting Next.js `/api` on port 3000.
  - Increased Playwright expect timeout to 30 seconds to tolerate first-load Next.js compilation during local UAT.
  - Updated report export assertion for the hardened downloaded-file status message.
  - `pnpm test`: passed, 14 web/shared tests after stabilising Vitest with a single worker.
- 2026-06-29 ownership/lock hardening run:
  - `docker compose exec -T api env RUN_DB_TESTS=1 pytest apps/api/tests/test_marking_workflow.py`: passed, 3 passed / 1 skipped.
  - `docker compose exec -T api env RUN_DB_TESTS=1 pytest apps/api/tests/test_writing_editor.py`: passed, 3 passed.
  - `docker compose exec -T api env RUN_DB_TESTS=1 pytest`: passed, 51 passed / 1 skipped.
  - `pnpm test`: passed, 14 tests.
  - `pnpm lint`: passed.
  - `E2E_BASE_URL=http://localhost:3000 E2E_API_BASE_URL=http://localhost:8000 PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH=<local Chrome for Testing> pnpm --filter @english-ai-writing/e2e test`: passed, 7 passed.
  - Added DB-backed tests that released feedback and exercise completion are scoped to the owning student, and that submitted writing rejects both later autosave and a second submit attempt.
- 2026-06-29 teacher assigned-class marking hardening run:
  - `docker compose exec -T api env RUN_DB_TESTS=1 pytest apps/api/tests/test_marking_workflow.py`: passed, 4 passed / 1 skipped.
  - `docker compose exec -T api env RUN_DB_TESTS=1 pytest`: passed, 52 passed / 1 skipped.
  - `pnpm test`: passed, 14 tests.
  - `pnpm lint`: passed.
  - `E2E_BASE_URL=http://localhost:3000 E2E_API_BASE_URL=http://localhost:8000 PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH=<local Chrome for Testing> pnpm --filter @english-ai-writing/e2e test`: passed, 7 passed.
  - Added DB-backed tests that an active teacher without assigned class membership cannot see, run, review or release a marking result for another teacher's assigned class submission.
- 2026-06-29 UI productization API support run:
  - `docker compose exec -T api env RUN_DB_TESTS=1 pytest apps/api/tests/test_task_workflow.py`: passed, 9 tests.
  - `docker compose exec -T api env RUN_DB_TESTS=1 pytest apps/api/tests/test_marking_workflow.py`: passed, 5 passed / 1 skipped.
  - `docker compose exec -T api env RUN_DB_TESTS=1 pytest`: passed, 54 passed / 1 skipped.
  - `pnpm test`: passed, 14 tests.
  - `pnpm lint`: passed.
  - `E2E_BASE_URL=http://localhost:3000 E2E_API_BASE_URL=http://localhost:8000 PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH=<local Chrome for Testing> pnpm --filter @english-ai-writing/e2e test`: passed, 7 passed.
  - Added UI data contracts for Student Home task status, Teacher Dashboard summary counts and Marking Review filters before visual implementation.
- 2026-06-30 UI productization API gap run:
  - `docker compose exec -T api env RUN_DB_TESTS=1 pytest apps/api/tests/test_task_workflow.py apps/api/tests/test_writing_editor.py apps/api/tests/test_security_gate.py`: passed, 17 tests.
  - `docker compose exec -T api env RUN_DB_TESTS=1 pytest`: passed, 56 passed / 1 skipped.
  - `pnpm test`: passed, 14 tests.
  - `pnpm lint`: passed.
  - `E2E_BASE_URL=http://localhost:3000 E2E_API_BASE_URL=http://localhost:8000 PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH=<local Chrome for Testing> pnpm --filter @english-ai-writing/e2e test`: passed, 7 passed.
  - Added `used_by_task_count` to teacher rubric list responses, `GET /api/teacher/tasks/{task_id}` for task detail, and `GET /api/teacher/submissions/{submission_id}/exam-events` for assigned-class-scoped Exam Mode audit review.
- 2026-06-30 EngWriting migration validation:
  - Project copied to `/Users/allmind/Desktop/Edcosys2025/EngWriting`; source Codex worktree retained.
  - Local Git repository initialized with checkpoint `b8b4d17 foundation-uat-api-support-checkpoint`.
  - `.env`, dependency directories and local caches verified as ignored before commit.
  - Migrated Docker Compose stack started from the new directory after tagging existing local images for the new project name.
  - `docker compose exec -T api alembic upgrade head`: passed on the migrated stack.
  - `docker compose exec -T api env RUN_DB_TESTS=1 pytest`: passed, 56 passed / 1 skipped.
  - `pnpm test`: passed, 14 tests.
  - `pnpm lint`: passed.
  - `E2E_BASE_URL=http://localhost:3000 E2E_API_BASE_URL=http://localhost:8000 PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH=<local Chrome for Testing> pnpm --filter @english-ai-writing/e2e test`: passed, 7 passed.
- Earlier stress evidence used the seeded student credential repeatedly, but the latest strict evidence file uses 470 distinct generated student credentials.
- MiniMax fixture generation and generated writing fixture import were executed with the API key supplied through local runtime only. The key was not committed or rendered in UI/evidence.
- The 470 marking queue stress pass validates queue creation, not full worker drain through the live LLM provider. A 470-essay worker drain test should be explicitly approved as a costed external-provider test.
- UI productization is still behind the backend workflow: the current screens are usable for UAT flow validation, but they need the planned UI pass for a polished school pilot.
- The local DB was reset and reseeded after the strict stress pass. Latest stress evidence remains on disk under `docs/uat-evidence/2026-06-29/`.

## Runtime Truth Rules

- Runtime AI marking must use a configured real LLM provider. Missing `LLM_API_KEY` is a hard configuration failure for marking, not a fake pass.
- Runtime grammar suggestions must use the configured self-hosted LanguageTool-compatible service. If unavailable, writing continues with `service_status=unavailable`; fake suggestions are not allowed.
- Test doubles are allowed only in test modules.
- API keys and production credentials must not be committed, logged, rendered in the browser or included in evidence files.

## Required Real-Acceptance Commands

```bash
docker compose up -d --build
docker compose exec api alembic upgrade head
docker compose exec api env RUN_DB_TESTS=1 RUN_LLM_TESTS=1 pytest
docker compose exec web pnpm test
E2E_BASE_URL=http://localhost:3000 E2E_API_BASE_URL=http://localhost:8000 pnpm --filter @english-ai-writing/e2e test
STRESS_API_BASE_URL=http://127.0.0.1:8000 STRESS_EVIDENCE_DIR=docs/uat-evidence/2026-06-29 python tests/stress/uat_load.py
python -m pytest tests/unit/test_uat_fixture_scripts.py
python -m pytest tests/unit/test_uat_fixture_scripts.py tests/unit/test_uat_gate.py
python scripts/uat/check_uat_gate.py
python scripts/uat/check_uat_gate.py --require-distinct-student-stress --require-writing-fixtures-applied
STRESS_STUDENT_CREDENTIALS_CSV=tests/fixtures/uat/minimax/stress-student-credentials.csv STRESS_API_BASE_URL=http://127.0.0.1:8000 STRESS_EVIDENCE_DIR=docs/uat-evidence/2026-06-29 python tests/stress/uat_load.py
```

`RUN_LLM_TESTS=1` requires `LLM_PROVIDER`, `LLM_MODEL`, `LLM_BASE_URL` and `LLM_API_KEY` to be configured in the runtime environment. Keep the API key outside version control.

## UAT-Critical Skipped Tests Policy

Before UAT sign-off, skipped tests are acceptable only for:

- optional provider-specific live tests when a separate provider is intentionally out of scope;
- destructive or long-running stress tests that have a separately attached run log;
- tests explicitly marked as superseded by a stronger E2E scenario.

Skipped tests are not acceptable for authentication, tenant isolation, teacher assigned-class access, student data filtering, submission locking, feedback release visibility, export generation or real DeepSeek marking.
