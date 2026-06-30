# ADR 0003: LLM Provider Adapter Registry

Status: Accepted

## Context

The platform must support AI-assisted marking without hardcoding one LLM provider inside business logic. The user specifically requested mainstream model support such as DeepSeek, Qwen and Doubao, and the source requirements require adapter-based async workers, JSON schema validation and no student name/email disclosure to the LLM provider.

## Decision

Use a provider registry plus an `LLMAdapter` boundary in the FastAPI service layer.

- `deepseek`, `qwen` and `doubao` use an OpenAI-compatible chat-completions adapter with provider-specific base URL presets.
- `openai_compatible` is available for any compatible provider by setting `LLM_BASE_URL`.
- Provider, model, base URL, API key and timeout are configured through environment variables.
- AI marking output is validated against a Pydantic JSON schema before it can be saved by future worker code.
- Prompt construction excludes student name and email parameters by design.

## Consequences

- Future Phase 6 marking jobs can switch providers without changing marking business logic.
- UAT must run with a real provider configuration and `LLM_API_KEY`.
- Production deployments should explicitly set `LLM_MODEL` because provider model names can change.
- Non-OpenAI-compatible providers will require a new adapter implementation behind the same `LLMAdapter` protocol.
