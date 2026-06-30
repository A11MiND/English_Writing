# 02 Architecture

Status: Phase 5 baseline plus LLM and grammar adapter foundations.

## Authoritative Sources

- `docs/source_extracted/Technical Proposal.md`
- `docs/source_extracted/Spec-driven Development Specification.md`

## Phase 0 Architecture

- Monorepo with `apps/web`, `apps/api`, `apps/auth`, `workers`, `services`, `packages`, `infra`, `tests` and `docs`.
- Frontend: Next.js, TypeScript and Tailwind CSS.
- Backend: FastAPI, Pydantic, SQLAlchemy and Alembic.
- Local services: PostgreSQL and Redis via Docker Compose.
- Shared TypeScript package defines common API envelope, roles and error codes.

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
