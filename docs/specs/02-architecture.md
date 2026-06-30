# 02 Architecture

Status: UAT core architecture baseline implemented. Production hardening remains.

## Authoritative Sources

- `docs/source_extracted/Technical Proposal.md`
- `docs/source_extracted/Spec-driven Development Specification.md`

## Phase 0 Architecture

- Monorepo with `apps/web`, `apps/api`, `apps/auth`, `workers`, `services`, `packages`, `infra`, `tests` and `docs`.
- Frontend: Next.js, TypeScript and Tailwind CSS.
- Backend: FastAPI, Pydantic, SQLAlchemy and Alembic.
- Local services: PostgreSQL and Redis via Docker Compose.
- Shared TypeScript package defines common API envelope, roles and error codes.

## Implemented Runtime Architecture

- `apps/web`: Next.js App Router frontend with role-protected student, teacher and admin surfaces.
- `apps/api`: FastAPI backend with SQLAlchemy models, Alembic migrations, Pydantic validation, RBAC dependencies and standard API envelope.
- `apps/auth`: local OpenAuth-compatible service for UAT and development identity flows.
- `workers/marking-worker`: Redis-backed marking worker entrypoint that processes queued AI marking jobs.
- `services/grammar-service`: LanguageTool-compatible grammar service integration through Docker Compose.
- `packages/shared`: shared TypeScript types for API envelopes, roles, tasks, rubrics, marking, reports and UI contracts.
- `tests/e2e`, `tests/stress`, `tests/unit` and `apps/api/tests`: browser, stress, unit and DB-backed API coverage for the UAT core flow.

## LLM Adapter Foundation

- Business logic must depend on the `LLMAdapter` protocol, not a concrete provider SDK.
- Runtime environments require a real `LLM_PROVIDER` and `LLM_API_KEY`.
- `deepseek`, `qwen` and `doubao` are represented as provider presets using the OpenAI-compatible chat-completions adapter.
- `openai_compatible` supports additional compatible providers through `LLM_BASE_URL`.
- Production/UAT deployments must provide `LLM_API_KEY` through environment variables only.
- AI marking output must pass Pydantic JSON schema validation before future persistence.
- Prompt construction must not accept student name or student email fields.

## Grammar Adapter Foundation

- Business logic depends on a `GrammarAdapter` protocol.
- Runtime environments use the LanguageTool-compatible adapter through `GRAMMAR_PROVIDER=languagetool` and `GRAMMAR_SERVICE_URL`.
- Suggestion responses are normalized before reaching the web app.
- Redis caching is applied at the backend by normalized text and language.
- Grammar adapter failures are non-blocking and do not affect draft autosave or submission.
- Practice Mode may call the grammar endpoint after typing pauses or Full Check.
- Exam Mode never calls the grammar endpoint from the frontend and backend rejects suggestion checks for Exam tasks.
- LLM providers are not used for realtime grammar checking.

## Architecture Rules

- Do not call LLM on every keystroke.
- Use adapter boundaries for grammar, LLM and email integrations.
- Every protected data path in later phases must enforce tenant, role and ownership filters.

## Remaining Architecture Gaps

- Email adapter and password-reset/support email flows are not implemented beyond documented adapter boundary requirements.
- NLP metrics are minimal and should be expanded into a fuller service layer for readability, lexical and sentence-level metrics.
- Worker operations need dead-letter queue, retry backoff scheduling, concurrency controls and metrics.
- Production deployment needs managed PostgreSQL/Redis, backup automation, central logs, audit retention and runbooks.
- UI architecture needs reusable Catalyst-inspired, project-owned components for buttons, forms, tables, dialogs, shell and page headings.
