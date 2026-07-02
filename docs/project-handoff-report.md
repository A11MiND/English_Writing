# English AI Writing Platform Project Handoff Report

Date: 2026-07-02

Project: English AI Writing Platform 2026-2027

School: W F Joseph Lee Primary School

Target stage: UAT-ready controlled pilot demo

## 1. Repository Location

The active project has been migrated to:

```bash
/Users/allmind/Desktop/Edcosys2025/EngWriting
```

Future development should happen from this directory, not from the older Codex workspace copy.

The current local Git repository is initialized in this directory. At the time this report was written, `git status --short` was clean.

Recent checkpoints:

```text
de28785 productize catalyst inspired app shell
cbd4984 refactor page information architecture
f0f92ae add ui smoke coverage
f242345 productize teacher reporting and review
e1901f8 productize writing editor and feedback
```

## 2. Source Documents

The source documents are the authoritative product and technical inputs. They are stored inside the repository:

```text
docs/source/Product Requirements Document(1).docx
docs/source/Technical Proposal.docx
docs/source/English_AI_Writing_Platform_Technical_Proposal_UIUX(2).docx
docs/source/Spec-driven Development Specification.docx
```

Extracted Markdown copies are under:

```text
docs/source_extracted/
```

Spec-driven development files are under:

```text
docs/specs/
```

Important specs and traceability docs:

```text
docs/specs/00-spec-driven-development.md
docs/specs/01-product-scope.md
docs/specs/02-architecture.md
docs/specs/03-data-model.md
docs/specs/04-api-contract.md
docs/specs/05-auth-rbac.md
docs/specs/06-practice-mode.md
docs/specs/07-exam-mode.md
docs/specs/08-ai-marking.md
docs/specs/09-feedback-exercises.md
docs/specs/10-reports-export.md
docs/specs/11-uiux-screen-spec.md
docs/specs/12-testing-acceptance.md
docs/specs/13-deployment-operations.md
docs/specs/14-requirements-traceability.md
```

Progress and design planning files:

```text
docs/development-plan.md
docs/uat-readiness.md
docs/design/ui-productization-matrix.md
docs/design/page-ia-matrix.md
docs/uat-evidence/
```

## 3. Architecture Summary

The project is a monorepo with the required architecture:

```text
apps/web/                  Next.js, TypeScript, Tailwind CSS frontend
apps/api/                  FastAPI backend
apps/auth/                 Local auth service for UAT/dev
workers/marking-worker/    Async AI marking worker
services/grammar-service/  Grammar service container
packages/shared/           Shared TypeScript constants/types
infra/                     Migrations, seed data and infrastructure assets
tests/e2e/                 Playwright E2E tests
docs/                      Source docs, specs, design notes and UAT evidence
```

Runtime dependencies:

- Frontend: Next.js, React, TypeScript, Tailwind CSS.
- Writing editor: TipTap.
- Backend: FastAPI, SQLAlchemy, Pydantic.
- Database: PostgreSQL.
- Migrations: Alembic.
- Queue/cache: Redis.
- Grammar: LanguageTool-compatible service through an adapter.
- LLM: adapter-based provider layer, configured by environment variables.
- Tests: Pytest, Vitest, Playwright.
- Local environment: Docker Compose.

The UI direction is Catalyst-inspired: clean sidebar app shell, neutral canvas, compact tables/forms, clear action hierarchy. The paid Catalyst source has not been copied; components must remain project-owned React/Tailwind code unless the user later supplies a licensed kit.

## 4. Current Service State

The user asked to stop all frontend/backend services for other work. The Docker Compose stack is currently stopped.

`docker compose ps` currently shows no running services.

When running, the local service map is:

| Service | Container | Host Port | Purpose |
| --- | --- | ---: | --- |
| web | `engwriting-web-1` | 3000 | Next.js frontend |
| api | `engwriting-api-1` | 8000 | FastAPI backend |
| auth | `engwriting-auth-1` | 9000 | Local auth service |
| grammar-service | `engwriting-grammar-service-1` | 8010 | Grammar checking service |
| postgres | `engwriting-postgres-1` | 5432 | PostgreSQL |
| redis | `engwriting-redis-1` | 6379 | Redis cache/queue |
| marking-worker | `engwriting-marking-worker-1` | internal only | AI marking jobs |

Port conflict note: the user often has other projects on ports `3000` and `8000`. Before starting this project, check ports or make host ports configurable in `.env`.

Useful port checks:

```bash
lsof -nP -iTCP:3000 -sTCP:LISTEN
lsof -nP -iTCP:8000 -sTCP:LISTEN
lsof -nP -iTCP:9000 -sTCP:LISTEN
lsof -nP -iTCP:8010 -sTCP:LISTEN
lsof -nP -iTCP:5432 -sTCP:LISTEN
lsof -nP -iTCP:6379 -sTCP:LISTEN
```

## 5. Local Accounts

Seeded local demo accounts:

| Role | Email | Password |
| --- | --- | --- |
| Admin | `admin@wfjosephlee.edu.hk` | `Password123!` |
| Teacher | `teacher@wfjosephlee.edu.hk` | `Password123!` |
| Student | `student@wfjosephlee.edu.hk` | `Password123!` |

These are local UAT/demo credentials only. Do not reuse them for production.

## 6. Start, Stop and Test Commands

Start local stack:

```bash
cd /Users/allmind/Desktop/Edcosys2025/EngWriting
docker compose up -d --build
```

Stop local stack:

```bash
cd /Users/allmind/Desktop/Edcosys2025/EngWriting
docker compose stop
```

Run migrations:

```bash
cd /Users/allmind/Desktop/Edcosys2025/EngWriting
docker compose exec -T api alembic upgrade head
```

Backend tests:

```bash
cd /Users/allmind/Desktop/Edcosys2025/EngWriting
docker compose exec -T api env RUN_DB_TESTS=1 pytest
```

Frontend tests and build:

```bash
cd /Users/allmind/Desktop/Edcosys2025/EngWriting
pnpm lint
pnpm test
pnpm --filter @english-ai-writing/web build
```

Playwright E2E:

```bash
cd /Users/allmind/Desktop/Edcosys2025/EngWriting
E2E_BASE_URL=http://localhost:3000 \
E2E_API_BASE_URL=http://localhost:8000 \
PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH="/Users/allmind/Library/Caches/ms-playwright/chromium-1223/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing" \
pnpm --filter @english-ai-writing/e2e test
```

Last known validation after the Catalyst-inspired shell update:

- `pnpm lint`: passed.
- `pnpm test`: passed, 14 tests.
- `pnpm --filter @english-ai-writing/web build`: passed.
- Playwright E2E: passed, 10/10.

## 7. Current Product Status

The project is no longer Phase 0 only. It has a working local UAT demo path across the major PRD workflow:

- Admin account/class management and CSV import flow.
- Teacher dashboard.
- Rubric/task/assignment workflow.
- Student dashboard.
- Practice Mode editor with autosave, word count and grammar suggestions.
- Exam Mode editor with timer, paste blocking and blur/focus logging.
- Submission locking.
- AI marking job flow.
- Teacher marking review, manual override and release.
- Student released feedback and post-writing exercises.
- Class reports and CSV/PDF export.
- Basic school/student/teacher scoping tests.
- Stress/UAT evidence folder with partial load/queue evidence.

The latest focus shifted from backend feature completion to product-quality UI/UX:

- `docs/design/page-ia-matrix.md` defines page-level user intent, primary actions, hidden/secondary content and API needs.
- `docs/design/ui-productization-matrix.md` tracks Catalyst-inspired UI implementation.
- Student Home has been refactored around `To do`, `Teacher feedback` and `Done work`.
- Teacher Dashboard has been refactored around `Today`, `Set writing task`, `Mark writing`, `Class progress` and `Rubrics`.
- Shared app shell has been rebuilt toward a Catalyst-style sidebar layout.

## 8. Screenshot and Evidence Files

Recent visual evidence:

```text
docs/uat-evidence/screenshots/11-student-home-ia-refactor.png
docs/uat-evidence/screenshots/12-teacher-dashboard-ia-refactor.png
docs/uat-evidence/screenshots/13-catalyst-student-home.png
docs/uat-evidence/screenshots/14-catalyst-teacher-dashboard.png
docs/uat-evidence/screenshots/15-catalyst-admin-console.png
```

UAT and readiness notes:

```text
docs/uat-readiness.md
docs/uat-evidence/
```

## 9. Non-Negotiable Product and Security Rules

These rules come from the PRD and technical proposal and should not be weakened:

- Do not call the LLM on every keystroke.
- Practice Mode uses editor delta detection, debounce, grammar service and cache for real-time suggestions.
- LLM is only for full overview, suggestion explanation, rubric marking, feedback and exercises.
- Exam Mode disables real-time suggestions and AI rewrite.
- Exam Mode is restricted browser writing mode, not OS-level exam lockdown.
- Teacher review is the final assessment control.
- AI marking must be reviewable, editable and overridable by teachers.
- Every school-owned query must filter by `school_id`.
- Student queries must filter by `student_id`.
- Teacher queries must filter by assigned class.
- Student name and email must not be sent to the LLM provider.
- AI output must be JSON schema validated before saving.
- Failed AI marking must not delete or modify the submitted essay.
- Support flow assumes student issues are escalated through teachers.
- Do not implement parent portal, LMS integration, Word add-in, Google Docs add-on, plagiarism detection, handwriting OCR or native mobile app.
- Runtime product behavior should not use fake/mock outputs. If a real service is unavailable, fail clearly or return an explicit unavailable status.
- Test doubles are allowed only inside tests.
- Do not store tokens in browser local storage.
- Use HTTP-only cookies for sessions.
- Treat student writing as untrusted input.
- Sanitize HTML before rendering.
- Validate file upload type and size.

## 10. API Response Standard

Keep the API envelope unchanged.

Success:

```json
{
  "success": true,
  "data": {},
  "request_id": "string"
}
```

Error:

```json
{
  "success": false,
  "error_code": "string",
  "message": "string",
  "request_id": "string"
}
```

Required error codes include:

```text
AUTH_REQUIRED
ACCESS_DENIED
VALIDATION_ERROR
NOT_FOUND
DUPLICATE_RECORD
TASK_CLOSED
SUBMISSION_LOCKED
AI_MARKING_FAILED
EXPORT_FAILED
SUPPORT_TICKET_NOT_FOUND
```

## 11. LLM and Secret Handling

The user supplied real LLM API keys in chat during development. Treat any key pasted into chat as compromised for production. Rotate before any real deployment.

Rules:

- Never commit `.env`.
- Never print raw API keys in logs, reports, API responses or screenshots.
- Configure LLM providers only through environment variables.
- Admin UI may show provider/model/configured/last status, but must never show the key.

Expected environment variables:

```text
LLM_PROVIDER
LLM_MODEL
LLM_API_KEY
LLM_BASE_URL
LLM_TIMEOUT_SECONDS
```

Provider direction:

- DeepSeek should work through the OpenAI-compatible adapter.
- MiniMax may be used for cheaper test data generation or compatible test runs.
- Business logic must not be hardcoded to one vendor.

## 12. Current Gaps and Risks

Remaining gaps compared with a polished UAT-ready pilot:

1. UI productization is still in progress.
   - App shell, Student Home, Teacher Dashboard and Admin Console have first-pass Catalyst-inspired updates.
   - Practice/Exam editor, Teacher Marking Review, Reports and Admin details still need a deeper user-task-focused pass.

2. Port management needs improvement.
   - The project currently uses common development ports `3000` and `8000`.
   - Add `.env`-driven host port configuration to avoid collisions with the user's other projects.

3. Full provider-costed AI drain has not been completed.
   - Queue/load evidence exists.
   - A full 470-essay real LLM marking drain should only be run with explicit cost approval.

4. Production deployment is not decided.
   - Local Docker Compose works.
   - Cloud target, backups, monitoring, TLS, domain, autoscaling and disaster recovery are later work.

5. UAT data is generated demo data.
   - There is no real school UAT dataset yet.
   - The current data is enough for demo and flow verification, not for real educational evaluation.

6. OpenAuth production integration needs finalization.
   - The local auth service supports the demo/UAT flow.
   - Production identity provider details must be confirmed before deployment.

7. Security gates must keep expanding.
   - Existing school/student/teacher scoping tests should be preserved.
   - Add route-level DB tests whenever UI/API surface expands.

## 13. Recommended Next Work

Immediate next batch:

1. Add configurable Docker host ports.
   - Reduce collisions with the user's other projects.
   - Document examples for alternate web/api ports.

2. Continue UI/UX productization by user task, not by feature dumping.
   - Student: `What do I need to do now?`
   - Teacher: `What needs my attention today?`
   - Admin: `Which setup tasks are safe and complete?`

3. Productize these pages next:
   - Practice Mode editor.
   - Exam Mode editor.
   - Teacher marking review.
   - Class report page.
   - Admin import/account management.

4. Run regression after each UI batch.
   - `pnpm lint`
   - `pnpm test`
   - `pnpm --filter @english-ai-writing/web build`
   - Playwright E2E.

5. Update these files after each batch:
   - `docs/development-plan.md`
   - `docs/uat-readiness.md`
   - `docs/design/ui-productization-matrix.md`
   - `docs/design/page-ia-matrix.md`

## 14. UX Direction for the Next Engineer

The user explicitly wants the UI to feel like Tailwind Labs Catalyst:

- Sidebar application layout.
- Clean white work area.
- Neutral gray app canvas.
- Compact but readable tables and forms.
- Simple, direct action naming.
- Modern but not flashy.

But the user also emphasized the real audience:

- Primary school teachers.
- Primary school students.

So design decisions should prioritize:

- Clear wording.
- Large click targets.
- Few steps.
- Friendly but not childish visuals.
- Immediate and understandable feedback.
- Teacher efficiency.
- Student low cognitive load.
- Strong privacy defaults.
- No unnecessary charts, controls or jargon.

Do not simply keep adding widgets to existing pages. Start each page by writing:

1. Who is using this page?
2. What is the one main task?
3. What does the user need to know first?
4. What can be hidden until needed?
5. What backend data is required?
6. What action should be safest and most obvious?

## 15. Handoff Checklist

Before the new engineer starts:

- Open `/Users/allmind/Desktop/Edcosys2025/EngWriting`.
- Read `docs/development-plan.md`.
- Read `docs/specs/14-requirements-traceability.md`.
- Read `docs/design/page-ia-matrix.md`.
- Read `docs/design/ui-productization-matrix.md`.
- Confirm `.env` exists locally but is untracked.
- Run `git status --short`.
- Start Docker only when ports are available.
- Run migrations and tests before making changes.
- Do not weaken the non-negotiable PRD/security rules.
- Do not commit secrets.

