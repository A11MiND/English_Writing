# Developer Notes

## Phase 0

Phase 0 establishes local development foundations only. Do not add product behavior before the corresponding spec file is completed.

## Phase 1

Phase 1 establishes authentication and RBAC baseline behavior:

- OpenAuth HTTP token/userinfo adapter.
- HTTP-only application session cookie.
- Application source of truth for user role, school tenant and account status.
- Login/logout audit logs.
- Protected API dependencies for authenticated user and role checks.

Runtime authentication requires configured OpenAuth endpoints. Pytest uses a test-only dependency override for seeded identities.

## Phase 2

Phase 2 establishes core school data behavior:

- `teacher_profiles`, `student_profiles`, `classes` and `class_memberships` are managed through Alembic revision `0003_phase_2_core_school_data`.
- Admin school data endpoints filter by `school_id`.
- Teacher class queries join through `class_memberships` with `membership_role = TEACHER`.
- Student profile queries filter by the authenticated `user.id`.
- Admin CSV import returns successful and rejected rows without hiding validation failures.
- Import writes an audit log summary with role, success count and rejection count.

Imported users are data records for account-management and class workflows until matching identities are provisioned in OpenAuth.

`DATABASE_POOL_ENABLED` defaults to `false` so local reload and TestClient integration tests do not reuse asyncpg connections across event loops. Deployment operations should revisit pooling for production.

## Phase 3

Phase 3 establishes task and rubric workflow behavior:

- `rubrics`, `rubric_dimensions`, `writing_tasks` and `assignments` are managed through Alembic revision `0004_phase_3_tasks`.
- Rubrics must include Content, Language and Organisation dimensions.
- Writing task modes are `PRACTICE` and `EXAM`.
- Writing task statuses are `DRAFT`, `PUBLISHED`, `CLOSED` and `ARCHIVED`.
- Teacher task and rubric APIs filter by `school_id`.
- Teacher task assignment verifies the teacher is assigned to the target class.
- Student task queries filter by authenticated student profile and current class, and return only `PUBLISHED` tasks.

Phase 3 does not implement writing drafts, submissions or editor behavior. Those begin in Phase 4.

## Phase 4

Phase 4 establishes writing editor behavior:

- `drafts`, `submissions` and `exam_events` are managed through Alembic revision `0005_phase_4_editor`.
- `writing_tasks.exam_duration_minutes` stores optional exam timer duration.
- Practice and Exam editor pages use TipTap.
- Draft autosave writes HTML, plain text, word count and a version counter.
- Submission stores a locked final copy and prevents further draft saves for the same student/task.
- Exam Mode blocks paste in the editor and records `PASTE_ATTEMPT`.
- Exam Mode records `WINDOW_BLUR` and `WINDOW_FOCUS`.
- Exam Mode auto-submits when the configured frontend timer reaches zero.

Phase 4 intentionally does not perform real-time grammar checks, LLM calls, AI marking or feedback generation. Suggestions begin in Phase 5.

## LLM Adapter Foundation

The backend now has a provider-agnostic LLM service layer for future AI marking:

- `app.services.llm.LLMAdapter` is the business boundary.
- `deepseek`, `qwen` and `doubao` are supported through the OpenAI-compatible chat-completions adapter.
- `openai_compatible` supports any compatible provider when `LLM_BASE_URL` is set.
- AI marking output is validated by `app.services.ai_marking_schema.AIMarkingOutput`.
- Prompt construction does not accept student name or email fields.

Relevant environment variables:

```text
LLM_PROVIDER=deepseek
LLM_MODEL=deepseek-v4-flash
LLM_API_KEY=
LLM_BASE_URL=https://api.deepseek.com
LLM_TIMEOUT_SECONDS=30
```

Production deployments should set `LLM_MODEL` explicitly because provider model names can change over time. DeepSeek uses the OpenAI-compatible base URL `https://api.deepseek.com` in this application. `deepseek-v4-flash` is the default local/UAT model; `deepseek-v4-pro` can be selected by changing `LLM_MODEL`. DeepSeek also exposes `https://api.deepseek.com/anthropic`, but that endpoint is for Anthropic-compatible clients, not the current OpenAI-compatible adapter.

## AI Marking Foundation

AI marking foundation behavior:

- `marking_results`, `teacher_reviews` and `ai_usage_logs` are managed through Alembic revision `0006_phase_6_ai_marking`.
- Student submission creates a queued marking result in the same transaction as the locked submission, then attempts Redis enqueue after commit.
- Redis enqueue uses `MARKING_QUEUE_NAME`; enqueue failure does not reject a successfully persisted submission.
- `app.workers.marking_worker` consumes Redis jobs and calls the same marking processor used by the teacher-triggered UAT fallback.
- Teacher marking endpoints filter through the submitted student's current class and teacher assigned-class membership.
- `app.services.marking.process_marking_result` calls the configured `LLMAdapter`, validates JSON output and saves only schema-valid fields.
- Invalid LLM output is retried up to three attempts in the service call before marking `AI_MARKING_FAILED`.
- Failed AI marking never updates submitted essay HTML/text.
- Teacher overrides are stored in `teacher_reviews` and audited as `TEACHER_MARKING_OVERRIDE`.

The teacher-triggered run endpoint remains as a local/UAT fallback. Production hardening should add dead-letter handling, backoff scheduling and worker metrics.

## Phase 7

Phase 7 establishes feedback release and post-writing exercises:

- `teacher_reviews.feedback_released_at` and `feedback_released_by` are managed through Alembic revision `0007_phase_7_feedback`.
- `post_writing_exercises` stores generated follow-up exercises per student submission.
- Successful AI marking converts `recommended_exercises` into assigned post-writing exercise rows.
- Teacher release sets `teacher_reviews.status = RELEASED`.
- Student feedback endpoints return `NOT_FOUND` until feedback is released.
- Student exercise completion filters by authenticated `student_id` and requires released feedback.

Teacher review hardening:

- Review overrides are constrained to the current school rubric shape: Content, Language and Organisation are each 0-5, total is 0-15.
- When all three dimension scores are supplied, `total_score` must equal their sum.
- The review endpoint accepts `DRAFT`, `REVIEWED` and `RELEASE_READY`; `RELEASED` can only be set through the dedicated feedback release endpoint so `feedback_released_at` and audit logging stay consistent.
- Released feedback and post-writing exercise completion are scoped to the owning `student_id`; another active student receives `NOT_FOUND`.
- Submitted writing is locked against both later autosave and a second submit attempt.
- Teacher marking list, run, review and release endpoints are scoped through assigned class membership; an active teacher without the submitted student's class receives no list item and `NOT_FOUND` for direct marking-result actions.

## UI Productization

UI productization must start from the page matrix in `docs/specs/11-uiux-screen-spec.md`, not from component restyling. For each page, confirm the user goal, data/API dependencies, three presentation options, selected direction and UX risks before implementing Tailwind/Catalyst-style components.

UI API support added before visual implementation:

- `GET /api/student/tasks` includes draft, submission, locked and feedback release state for Student Home.
- `GET /api/teacher/dashboard-summary` provides teacher overview counts scoped by assigned class and optional `class_id` / `task_id`.
- `GET /api/teacher/marking/submissions` supports `class_id`, `task_id` and marking `status` filters for the Marking Review workspace.
- `GET /api/teacher/rubrics` includes `used_by_task_count` so the Rubric Builder can warn before editing or archiving rubrics already used by tasks.
- `GET /api/teacher/tasks/{task_id}` returns a single teacher-owned task with assigned classes for edit/detail screens.
- `GET /api/teacher/submissions/{submission_id}/exam-events` returns ordered Exam Mode audit events for submissions in the teacher's assigned classes only.

## Source Documents

The authoritative source `.docx` files are stored in `docs/source/`.

Readable Markdown extractions are stored in `docs/source_extracted/`.

## Architecture Defaults

- Frontend: Next.js, TypeScript, Tailwind CSS.
- Backend: FastAPI, SQLAlchemy, Pydantic.
- Database: PostgreSQL.
- Migrations: Alembic.
- Cache / queue foundation: Redis.
- Shared frontend contracts: `packages/shared`.

## API Response Rule

Every endpoint must return the standard success or error envelope with a `request_id`.

## Security Baseline For Future Phases

- Protected endpoints must validate session and role.
- School-owned queries must filter by `school_id`.
- Student queries must filter by `student_id`.
- Teacher queries must filter by assigned class.
- Tokens must not be stored in browser local storage.
- Student names and emails must not be sent to LLM providers.
- AI JSON output must be schema validated before saving.
