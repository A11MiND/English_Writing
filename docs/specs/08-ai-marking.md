# 08 AI Marking

Status: AI marking foundation implemented with Redis-backed local worker.

## Authoritative Sources

- `docs/source_extracted/Product Requirements Document(1).md`
- `docs/source_extracted/Technical Proposal.md`

## Non-Negotiable Rules

- Teacher review is the final assessment control.
- AI marking must be reviewable, editable and overridable by teachers.
- Student name and email must not be sent to the LLM provider.
- AI output must be JSON schema validated before saving.
- Failed AI marking must not delete or modify the submitted essay.

## Adapter Design

- Backend exposes a service-layer `LLMAdapter` protocol with `generate_json`.
- `deepseek`, `qwen`, `doubao` and `minimax` use an OpenAI-compatible chat-completions adapter.
- `openai_compatible` allows additional providers by setting `LLM_BASE_URL`.
- Provider selection is controlled by:
  - `LLM_PROVIDER`
  - `LLM_MODEL`
  - `LLM_API_KEY`
  - `LLM_BASE_URL`
  - `LLM_TIMEOUT_SECONDS`
- Provider presets are infrastructure configuration. Marking business logic must not branch on provider names.
- MiniMax UAT testing uses `LLM_PROVIDER=minimax`, `LLM_MODEL=MiniMax-M3` and `LLM_BASE_URL=https://api.minimaxi.com/v1`.
- The marking prompt includes a compact valid JSON example to improve schema adherence for lower-cost providers while still requiring strict JSON schema validation before saving.

## JSON Schema

The validated marking output contains:

- `content_score`
- `language_score`
- `organisation_score`
- `total_score`
- `confidence_level`
- `content_feedback`
- `language_feedback`
- `organisation_feedback`
- `strengths`
- `weaknesses`
- `sentence_level_comments`
- `recommended_exercises`
- `warning_flags`
- `model_metadata`

Any missing, extra or wrongly typed field rejects the provider output.

## Prompt Boundary

- Marking prompts include task title, task instruction, rubric summary, NLP metrics and essay text.
- Marking prompts do not accept student name or student email parameters.
- The system prompt treats essay content as untrusted input and instructs the model not to follow instructions inside the essay.
- The system prompt includes an example output shape but the saved result always comes from validated provider JSON, not from the example.

## Phase 6 Remaining Work

- Aggregate grammar service output once Phase 5 suggestions exist.
- Expand NLP metrics beyond current word count/mode metadata.
- Add richer teacher review screens and release workflow.
- Add production hardening for worker concurrency, dead-letter queues, backoff scheduling and operational metrics.

## Implemented Foundation

- Submitting writing creates one queued `marking_results` record.
- Submitting writing enqueues the marking result ID to Redis using `MARKING_QUEUE_NAME`.
- The `marking-worker` service consumes Redis jobs and calls the shared marking processor.
- Teacher can list submissions for assigned classes only.
- Teacher can run configured LLM marking for a queued result as a manual UAT fallback.
- LLM output is schema validated before fields are copied to `marking_results`.
- Invalid provider output is retried up to three attempts inside the processing service, then marked `AI_MARKING_FAILED`.
- Failed marking updates only marking status and error metadata; the submitted essay is not modified.
- Teacher can save manual override scores in `teacher_reviews`.
- Teacher override writes `TEACHER_MARKING_OVERRIDE` to `audit_logs`.
- AI provider success/failure writes `ai_usage_logs`.
