# ADR 0004: No Runtime Mock Services

Status: Accepted

## Context

The delivery requirement is a real UAT pilot, not a demo that silently substitutes local mock authentication, grammar or LLM behavior. Earlier phase scaffolding allowed local stand-ins for speed. That is no longer acceptable for phase completion.

## Decision

Runtime application code must use real service adapters only:

- Authentication uses OpenAuth HTTP token and userinfo endpoints.
- Grammar suggestions use a LanguageTool-compatible self-hosted service.
- AI marking uses a configured real LLM provider such as DeepSeek, Qwen, Doubao or another OpenAI-compatible endpoint.
- Missing service configuration must fail clearly instead of returning deterministic fake output.
- Test-only doubles may exist under `apps/api/tests` and must be injected through test dependency overrides or explicit test parameters.

## Consequences

- Local `docker compose up` requires real external-service configuration for full login and AI marking.
- Tests can still validate application logic without external credentials, but those test doubles are not runtime defaults.
- UAT sign-off must include OpenAuth, LanguageTool and LLM-provider credentials/configuration.
