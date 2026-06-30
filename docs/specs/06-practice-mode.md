# 06 Practice Mode

Status: Phase 5 grammar suggestion baseline implemented.

## Authoritative Sources

- `docs/source_extracted/Product Requirements Document(1).md`
- `docs/source_extracted/Technical Proposal.md`
- `docs/source_extracted/English_AI_Writing_Platform_Technical_Proposal_UIUX(2).md`

## Non-Negotiable Rules

- Do not call LLM on every keystroke.
- Use editor delta detection, debounce, grammar service and cache for real-time suggestions.
- LLM is limited to full overview, suggestion explanation, rubric marking, feedback and exercises.

## Phase 4 Scope

Practice Mode uses TipTap as the writing editor and implements:

- Student can open an assigned published Practice Mode task.
- Editor displays task title, instruction, mode, word limits and word count.
- Draft content autosaves after typing pauses.
- Autosave persists `content_html`, `content_text`, `word_count` and a version counter.
- Student can submit final writing.
- Submission saves a locked copy of final HTML/text.
- Once submitted, the editor becomes read-only and further draft saves return `SUBMISSION_LOCKED`.

## Phase 5 Scope

- Real-time grammar suggestions use editor-change detection plus a debounce before calling the backend.
- Realtime checks call `/api/suggestions/check` with `check_mode = CHANGED`.
- Full Check calls `/api/suggestions/check` with `check_mode = FULL`.
- Backend grammar checks use a grammar adapter boundary, not an LLM.
- Runtime grammar checks use the LanguageTool-compatible adapter behind `GRAMMAR_SERVICE_URL`.
- Redis caches checks by normalized text and language so repeated chunks avoid duplicate grammar-service calls.
- Suggestions are normalized to `id`, `rule_id`, `category`, `message`, `short_message`, `offset`, `length`, `replacements` and `severity`.
- TipTap renders inline highlights from normalized offset spans without modifying submitted text.
- The Practice Mode side panel shows suggestion cards, affected source text, replacement actions, dismiss actions, service status and stale overview state.
- Accepting a suggestion replaces only the returned text span.
- Dismissing a suggestion removes it from the active set.
- Editing text invalidates only suggestions whose original source span no longer matches.

No LLM calls are made during typing, autosave or realtime grammar checks.
