# 07 Exam Mode

Status: UAT core implemented and browser-tested on 2026-06-29.

## Authoritative Sources

- `docs/source_extracted/Product Requirements Document(1).md`
- `docs/source_extracted/Technical Proposal.md`

## Non-Negotiable Rules

- Exam Mode disables real-time suggestions and AI rewrite.
- Exam Mode is restricted browser writing mode, not OS-level secure exam lockdown.
- Paste attempts and window focus changes must be logged when implemented.

## Phase 4 Scope

Exam Mode uses TipTap in restricted writing mode and implements:

- Student can open an assigned published Exam Mode task.
- Editor displays task title, prompt, word count, submit control and exam notice.
- Real-time suggestions and AI rewrite controls are not rendered.
- Paste into the editor is blocked.
- Paste attempts are logged as `PASTE_ATTEMPT`.
- Browser focus changes are logged as `WINDOW_BLUR` and `WINDOW_FOCUS`.
- Draft content autosaves after typing pauses.
- Student can manually submit.
- If `exam_duration_minutes` is configured on the task, the frontend displays a timer and auto-submits when it expires.
- Submitted Exam Mode writing is locked.

## 2026-06-29 Acceptance Evidence

- API create/update task contracts accept `exam_duration_minutes` for Exam Mode tasks.
- Exam Mode task creation rejects missing `exam_duration_minutes`.
- Practice Mode tasks clear/reject exam duration configuration.
- Teacher task builder exposes an Exam minutes field when Exam Mode is selected.
- Playwright UAT flow creates a one-minute Exam Mode task and verifies paste blocking plus timer auto-submit.
- `docker compose --profile e2e run --rm e2e`: 7 passed, including `student completes Exam Mode, paste is blocked and timer auto-submits`.

## Boundary

Exam Mode is restricted browser writing mode only. It does not claim OS-level secure exam lockdown.
