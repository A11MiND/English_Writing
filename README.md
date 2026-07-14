# English AI Writing Platform 2026-2027

School-based English AI writing, assessment and reporting platform for W F Joseph Lee Primary School.

This repository is currently through Phase 8 backend/frontend baseline with Phase 9 test scaffolding.

Current UAT readiness is tracked in `docs/uat-readiness.md`. A normal unit-test pass is not UAT sign-off; real UAT requires Postgres, Redis, LanguageTool, DeepSeek, browser E2E and stress evidence.

## Implemented Contents

- Monorepo workspace with `apps`, `packages`, `services`, `workers`, `infra`, `tests` and `docs`.
- Source `.docx` documents copied to `docs/source/`.
- Extracted source Markdown in `docs/source_extracted/`.
- Spec-driven development baseline in `docs/specs/`.
- Next.js, TypeScript and Tailwind frontend skeleton in `apps/web`.
- FastAPI backend skeleton in `apps/api`.
- PostgreSQL and Redis local services through Docker Compose.
- Alembic baseline migration in `infra/migrations`.
- Shared TypeScript API envelope, roles and error-code types in `packages/shared`.
- OpenAuth HTTP authentication adapter, HTTP-only application session cookie, RBAC dependencies and login/logout audit logging.
- OpenAuth-compatible `apps/auth` service with hashed-password local/UAT identities and bearer token/userinfo endpoints.
- Core school data models for teacher profiles, student profiles, classes and class memberships.
- Admin account list, class list/create and CSV import APIs.
- Teacher assigned-class API and student profile API.
- Minimal role-based web pages for Admin, Teacher and Student workspaces.
- Task and rubric workflow models for rubrics, rubric dimensions, writing tasks and assignments.
- Teacher rubric builder, task builder and assignment APIs.
- Student assigned-task API and dashboard task visibility.
- TipTap Practice Mode and Exam Mode editor pages.
- Draft autosave, word count and final submission locking.
- Exam Mode paste blocking, timer support and browser event logging.
- Provider-agnostic LLM adapter foundation with `deepseek`, `qwen`, `doubao`, `minimax` and `openai_compatible` provider configuration.
- AI marking JSON schema validation service for future worker persistence.
- Marking result, teacher review and AI usage log tables.
- Submission-created queued marking results and Redis queue jobs.
- Redis-backed marking worker plus teacher-triggered marking fallback and teacher review override.
- Grammar adapter foundation with LanguageTool-compatible provider support.
- `/api/suggestions/check` with Redis caching and normalized suggestion spans.
- Practice Mode debounce checks, inline highlights, suggestion panel, Full Check, accept and dismiss actions.
- Student feedback release and post-writing exercise completion.
- Class report generation, completion analytics, rubric breakdown, common weaknesses, CSV export and PDF export.
- Playwright E2E smoke scaffold and stress scripts for login, writing, submission, marking queue and reports.

## Prerequisites

- Docker Desktop
- Docker Compose v2
- Node.js and pnpm only if running the web app outside Docker
- Python 3.12 only if running the API outside Docker

## Local Setup

```bash
cd english-ai-writing-platform
cp .env.example .env
docker compose up -d --build
docker compose exec -T api alembic upgrade head
```

The services should be available at:

- Web: `http://localhost:3000`
- API: `http://localhost:8000`
- API docs: `http://localhost:8000/docs`
- Auth service: `http://localhost:9000`
- Grammar service: `http://localhost:8010`
- PostgreSQL: `localhost:5432`
- Redis: `localhost:6379`
- Marking worker: `marking-worker` Docker Compose service

The Docker `web` service builds the Next.js app and runs it with `next start`.
If you run the web app outside Docker for local UI work, keep the same API
stack running and start a host production preview on a separate port:

```bash
pnpm --filter @english-ai-writing/web build
pnpm --dir apps/web exec next start -H 127.0.0.1 -p 3001
```

### Temporary team demo link

For a short review session, keep the full Docker stack running and expose only
the Next.js web entry point through a Cloudflare Quick Tunnel:

```bash
docker compose up -d
PUBLIC_DEMO_ACK=I_UNDERSTAND scripts/dev/start_demo_tunnel.sh
```

The command prints a temporary `https://*.trycloudflare.com` URL. The URL exists
only while the tunnel process and this machine stay online. It is suitable for a
controlled demo, not production hosting. Do not share local admin credentials,
rotate any API key previously pasted into chat, and stop the tunnel after the
review.

## Health Checks

```bash
curl http://localhost:8000/health
curl http://localhost:8000/api/health
curl http://localhost:8000/api/health/db
```

## OpenAuth Configuration

Runtime login uses the `apps/auth` OpenAuth-compatible service in Docker Compose:

```text
OPENAUTH_TOKEN_URL=http://auth:9000/oauth/token
OPENAUTH_USERINFO_URL=http://auth:9000/userinfo
OPENAUTH_CLIENT_ID=english-ai-writing-web
OPENAUTH_CLIENT_SECRET=local-dev-client-secret
OPENAUTH_SIGNING_SECRET=local-dev-signing-secret
OPENAUTH_USERS_JSON=[...]
OPENAUTH_USERS_JSON_FILE=/app/tests/fixtures/uat/minimax/openauth-users.combined.json
```

The application validates OpenAuth subject claims against its `users` table before creating the HTTP-only session cookie. Local/UAT identities use PBKDF2 password hashes in `OPENAUTH_USERS_JSON`; production deployments must replace all local secrets and identities.

For large generated UAT identity sets, prefer `OPENAUTH_USERS_JSON_FILE` over
embedding hundreds of users in `OPENAUTH_USERS_JSON`. The auth container mounts
`tests/fixtures/uat` read-only so generated OpenAuth users can be loaded from a
file without hitting process environment length limits.

All API responses use the standard envelope:

```json
{
  "success": true,
  "data": {},
  "request_id": "string"
}
```

## Migrations

Run the Alembic migrations:

```bash
docker compose exec api alembic upgrade head
```

Phase 1 creates identity, session and audit tables. Phase 2 adds teacher/student profiles, classes and class memberships, then seeds P4A, P5A and P6A for local UAT. Phase 3 adds rubrics, rubric dimensions, writing tasks and assignments, then seeds one P5 rubric, one Practice Mode task and one Exam Mode task for P5A. Phase 4 adds drafts, submissions, exam events and a 30-minute timer on the seeded Exam Mode task. AI marking foundation adds marking results, teacher reviews and AI usage logs. Phase 7 adds feedback release and exercises. Phase 8 adds `class_reports`.

Reset local UAT data when DB-backed tests have polluted the development database:

```bash
CONFIRM_RESET=RESET_UAT_DB scripts/dev/reset_uat_db.sh
```

This drops and recreates the local PostgreSQL database, reapplies Alembic migrations and restores the seeded school, users, classes, rubric and writing tasks. Do not run it against any shared or production database.

For product demos, use the friendlier wrapper with the same safety behavior:

```bash
CONFIRM_RESET=RESET_DEMO_DB scripts/dev/reset_demo_db.sh
```

Run a real demo smoke check after Docker is up. It verifies web routes, API
health, Admin LLM connection, teacher prompt generation, LanguageTool-compatible
grammar checking and Exam Mode suggestion blocking:

```bash
scripts/dev/check_demo_smoke.sh
```

Override URLs when needed:

```bash
WEB_BASE_URL=http://localhost:3000 API_BASE_URL=http://localhost:8000 scripts/dev/check_demo_smoke.sh
```

The smoke check intentionally uses real API calls. The prompt-generation and AI
connection checks may create prompt draft and AI usage audit rows in the local
demo database. Run `CONFIRM_RESET=RESET_DEMO_DB scripts/dev/reset_demo_db.sh`
when you need to return to a clean seeded demo state.

## Phase 2 APIs

- `GET /api/admin/users`
- `GET /api/admin/classes`
- `POST /api/admin/classes`
- `POST /api/admin/import/users`
- `GET /api/teacher/classes`
- `GET /api/student/profile`

CSV import is exposed in the Admin page as a textarea-based pilot tool. Expected headers are:

```text
email,display_name,student_number,level,class_name,staff_code
```

## Phase 3 APIs

- `GET /api/teacher/rubrics`
- `POST /api/teacher/rubrics`
- `GET /api/teacher/tasks`
- `POST /api/teacher/tasks`
- `POST /api/teacher/tasks/{task_id}/assignments`
- `GET /api/student/tasks`

The teacher dashboard exposes a basic rubric builder, task builder and class assignment form. The student dashboard lists published tasks assigned to the student's current class.

## Phase 4 APIs

- `GET /api/student/tasks/{task_id}/writing`
- `PUT /api/student/tasks/{task_id}/draft`
- `POST /api/student/tasks/{task_id}/submit`
- `POST /api/student/tasks/{task_id}/exam-events`

Student task cards link to:

- Practice: `/student/tasks/{task_id}/practice`
- Exam: `/student/tasks/{task_id}/exam`

## Phase 5 Grammar Suggestion API

- `POST /api/suggestions/check`

Local grammar suggestions use a LanguageTool-compatible service:

```text
GRAMMAR_PROVIDER=languagetool
GRAMMAR_SERVICE_URL=http://grammar-service:8010
GRAMMAR_CACHE_TTL_SECONDS=86400
```

The endpoint is Practice Mode only; Exam Mode suggestion checks are rejected. Grammar service failures do not block writing, autosave or submission.

## LLM Adapter Configuration

AI marking requires a real LLM provider:

```text
LLM_PROVIDER=deepseek
LLM_MODEL=deepseek-v4-flash
LLM_API_KEY=
LLM_BASE_URL=https://api.deepseek.com
```

Supported provider presets:

- `deepseek`
- `qwen`
- `doubao`
- `minimax`
- `openai_compatible`

Set `LLM_PROVIDER`, `LLM_MODEL` and `LLM_API_KEY`. Use `LLM_BASE_URL` for `openai_compatible` or to override a preset endpoint. No production credentials should be committed.

DeepSeek OpenAI-compatible setup:

- `LLM_BASE_URL=https://api.deepseek.com`
- recommended current models: `deepseek-v4-flash`, `deepseek-v4-pro`
- avoid new usage of `deepseek-chat` and `deepseek-reasoner`; they are scheduled for deprecation on 2026-07-24

DeepSeek also exposes an Anthropic-compatible URL, `https://api.deepseek.com/anthropic`. This codebase currently uses the OpenAI-compatible chat-completions adapter.

MiniMax OpenAI-compatible setup for lower-cost UAT testing:

- `LLM_PROVIDER=minimax`
- `LLM_MODEL=MiniMax-M3`
- `LLM_BASE_URL=https://api.minimaxi.com/v1`
- set `LLM_API_KEY` from the deployment or local environment only

MiniMax can also generate fictional UAT fixtures without committing the key:

```bash
MINIMAX_API_KEY=... python scripts/uat/generate_minimax_uat_data.py --student-count 470
```

Outputs are written to `tests/fixtures/uat/minimax/`:

- `students.csv`
- `teachers.csv`
- `openauth-users.json`
- `openauth-users.combined.env` after applying fixtures
- `stress-student-credentials.csv` after applying fixtures
- `writing-fixtures.json`
- `writing-fixtures.applied.json` after importing writing fixtures

Prepare generated identities for local UAT:

```bash
python scripts/uat/apply_uat_fixtures.py
```

This writes a combined OpenAuth env snippet and stress credential CSV. After
putting the generated `OPENAUTH_USERS_JSON` into local `.env` and restarting
`auth`, import the matching DB users:

```bash
python scripts/uat/apply_uat_fixtures.py --import-users
```

Create generated UAT rubrics, writing tasks and assignments through the real
teacher APIs:

```bash
python scripts/uat/apply_uat_fixtures.py --import-writing-fixtures
```

Use both flags after `auth` has been restarted with the combined OpenAuth users
when you want a full generated pilot dataset:

```bash
python scripts/uat/apply_uat_fixtures.py --import-users --import-writing-fixtures
```

Run distinct-student stress with:

```bash
STRESS_STUDENT_CREDENTIALS_CSV=tests/fixtures/uat/minimax/stress-student-credentials.csv \
STRESS_API_BASE_URL=http://127.0.0.1:8000 \
STRESS_EVIDENCE_DIR=docs/uat-evidence/2026-06-29 \
python tests/stress/uat_load.py
```

Check the currently attached UAT evidence without silently passing missing
items:

```bash
python scripts/uat/check_uat_gate.py
python scripts/uat/check_uat_gate.py --require-distinct-student-stress --require-writing-fixtures-applied
```

## AI Marking Foundation APIs

- `GET /api/teacher/marking/submissions`
- `POST /api/teacher/marking-results/{marking_result_id}/run`
- `POST /api/teacher/marking-results/{marking_result_id}/retry`
- `POST /api/teacher/marking-results/{marking_result_id}/review`
- `POST /api/teacher/marking-results/{marking_result_id}/release`
- `GET /api/student/submissions/{submission_id}/feedback`
- `POST /api/student/exercises/{exercise_id}/complete`

The teacher dashboard includes a basic AI marking queue. Marking fails clearly when no real LLM provider credentials are configured.

Normal local marking flow:

1. Student submits writing.
2. API creates `marking_results.status = QUEUED`.
3. API enqueues the marking result ID to Redis.
4. `marking-worker` consumes the job and saves schema-valid AI marking output.

Worker logs:

```bash
docker compose logs -f marking-worker
```

Teacher release controls expose feedback to students. Students can open released feedback from the writing editor after submission and complete post-writing exercises.

## Phase 8 Reports And Exports

- `GET /api/teacher/reports/classes/{class_id}`
- `POST /api/teacher/reports/classes/{class_id}/generate`
- `GET /api/teacher/reports/classes/{class_id}/export.csv`
- `GET /api/teacher/reports/classes/{class_id}/export.pdf`

Teacher reports enforce assigned-class access. Reports include completion status, rubric breakdown, score distribution, common weaknesses and per-student/task completion rows. CSV/PDF export actions are audit logged.

## Tests

Backend tests:

```bash
docker compose exec api pytest
```

Run real database integration tests when Postgres is available:

```bash
docker compose exec api env RUN_DB_TESTS=1 pytest
```

Run the UAT truth gate after configuring a real LLM provider key in the environment:

```bash
docker compose exec api env RUN_DB_TESTS=1 RUN_LLM_TESTS=1 pytest
```

`LLM_API_KEY` must stay in local or deployment environment variables only. Do not commit API keys or paste them into logs/evidence files.

Real DeepSeek marking smoke:

```bash
LIVE_API_BASE_URL=http://127.0.0.1:8000 python tests/live/deepseek_marking_smoke.py
```

The smoke script logs in through the API, creates a temporary task, submits a student essay and runs teacher-triggered AI marking. It prints only IDs, status, score and metadata keys.

Frontend tests:

```bash
docker compose exec web pnpm test
```

E2E smoke tests:

```bash
cd tests/e2e
pnpm install
E2E_BASE_URL=http://localhost:3000 pnpm test
```

Containerized E2E smoke, with a Docker-only web service using a same-origin `/api` proxy to `http://api:8000`:

```bash
docker compose --profile e2e up -d web-e2e
docker compose --profile e2e run --rm e2e
```

The current E2E smoke covers admin, teacher and student login routing, the shared app shell, teacher rubric/task controls, admin AI status/account controls and student task entry.

Stress scripts:

```bash
STRESS_API_BASE_URL=http://127.0.0.1:8000 python tests/stress/login_burst.py
STRESS_TASK_ID=<task-id> python tests/stress/submission_burst.py
STRESS_CLASS_ID=<class-id> python tests/stress/report_after_marking.py
```

## Current Limitations

- Local OpenAuth-compatible identities are development/UAT fixtures; production must replace secrets and identity source.
- CSV import is intentionally simple for Phase 2; it does not yet support file upload validation or complex quoted CSV cells.
- Imported local users are school data records until matching identities exist in OpenAuth.
- The demo UI is aligned to the supplied role-based prototype routes for Admin, Teacher and Student.
- Phase 3 integration tests create temporary `Test Task` and `Test Rubric` records in the local development database.
- Parent portal functionality is not part of the current demo scope and is not linked from end-user navigation.
- Phase 4 integration tests create temporary writing tasks, drafts, submissions and exam events.
- Phase 5 uses a LanguageTool-compatible service; Docker Compose includes a `grammar-service` image.
- Suggestion span mapping is implemented for plain text offsets and TipTap inline text; complex rich-text edge cases need broader E2E coverage.
- AI marking worker exists for local/UAT, but production-grade dead-letter queues, backoff scheduling and worker metrics are not implemented yet.
- Email and production deployment setup are not implemented yet.
- PDF export is service-generated and functional; visual formatting can be improved after UI review.
- Database pooling is disabled by default (`DATABASE_POOL_ENABLED=false`) to keep async test and hot-reload behavior stable; deployment operations will revisit pool settings.

## Next Recommendation

Run full Docker verification with real LLM credentials, then harden UI selectors and expand Playwright coverage across the complete UAT flow.
