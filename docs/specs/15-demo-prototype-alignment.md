# Demo Prototype Alignment Specification

## Purpose

This demo must be a real, runnable English AI Writing product surface aligned to the HTML prototype in:

`/Users/allmind/Library/Application Support/Open Design/namespaces/release-stable/data/projects/ccfe6909-24b2-4051-9dbf-9cb554df1e1b`

The prototype is the design source of truth for page structure, hierarchy, role paths, component vocabulary, interaction states, and English user copy. New UI may only depart from the prototype when the prototype conflicts with real backend behavior, role boundaries, security, or demo scope.

## Demo Scope

Included roles:

- Student
- Teacher
- School Admin / System Admin

Out of scope for this demo:

- Parent portal
- Parent account binding
- Parent notification workflows

Parent prototype references must not appear in final demo navigation. If an implementation route remains for internal comparison, it must not be linked from end-user UI.

## Prototype Route Contract

| Prototype file | App route | Demo requirement |
|---|---|---|
| `login.html` | `/login` | Real account login, role routing, account-state messaging. No preview role buttons. |
| `marking-workbench.html` | `/teacher/marking` | Core teacher marking workbench. AI suggestions and confidence are teacher-only. |
| `homework.html` | `/teacher/assignments` | Assignment creation, publish, close, archived states. |
| `question-center.html` | `/teacher/questions` | LLM prompt generation draft bound to year level, mode, teaching focus, word range, and rubric. |
| `analytics.html` | `/teacher/reports` | Real class report, regeneration state, export feedback. |
| `student-work.html` | `/student/writing` | Real assigned tasks, due dates, writing mode, feedback status. |
| `exam.html` | `/student/exam/:taskId` | Timed writing, suggestions disabled, paste blocked, focus/submission events recorded. |
| `student-feedback.html` | `/student/feedback/:submissionId` | Teacher-released feedback only. No raw AI confidence, model metadata, or class comparison. |
| `class-management.html` | `/admin/classes` | Class roster, teacher ownership, student account status. Parent link UI hidden for demo. |
| `settings.html` | `/admin/settings` | AI policy, exam safeguards, export policy, and real LLM API settings. |
| `parent-portal.html` | `/parent/progress` | Out of scope for demo; route hidden or disabled. |
| `index.html` | `/prototype` | Internal preview only; not an end-user page. |

## Design System Contract

Production UI should reuse the prototype vocabulary before inventing new components:

- `top-nav`
- `sidebar`
- `side-nav`
- `panel`
- `metric`
- `task-card`
- `rubric-item`
- `state-card`
- `segmented`
- `modal`
- `toast`
- `table`
- `input`
- `select`
- `textarea`
- `btn`

The target visual tone is restrained school operations software: neutral surfaces, single blue primary action, dense but readable teacher/admin workflows, and mobile-friendly student surfaces. Do not turn workflow screens into marketing pages.

## Real Backend Rules

- Grammar check remains the existing real LanguageTool-compatible service.
- Practice Mode may call grammar suggestions.
- Exam Mode must not call grammar suggestions and must block paste in the client.
- AI marking must call a real configured LLM provider. Missing configuration is a visible error, not a fake success.
- Prompt generation must call a real configured LLM provider.
- Teacher review and release state must be enforced by backend data.
- Student feedback APIs must only return released teacher-approved content and must exclude teacher-only AI internals.
- Admin LLM API settings must support provider, model, base URL, API key configured state, masked key display, and connection testing.

## Required States

Every major workflow must expose these states where applicable:

- loading
- empty
- error
- disabled
- pending review
- released
- archived
- blocked/suspended account

## Required Interactions

- segmented tab switching
- modal confirmation
- toast feedback
- exam word count
- exam paste blocking
- exam timer
- prompt generation draft
- copy action
- export queue/download feedback
- report regeneration loading state

## Acceptance Criteria

- All end-user UI is English.
- Parent functionality is hidden for the demo.
- Every included prototype page has a corresponding route.
- UI structure and component hierarchy match the prototype unless this file records an explicit product adjustment.
- No prototype dummy data is treated as business fact.
- Student cannot see raw AI confidence, model metadata, or class comparison.
- Feedback is invisible to students until teacher release.
- Admin can configure and test LLM settings without exposing the raw API key.
- Desktop, tablet, and mobile checks are completed before demo sign-off.

## Demo Smoke Gate

`scripts/dev/check_demo_smoke.sh` is the local demo gate. It must pass before a live demo unless a known local
environment issue is recorded. The script checks:

- `/login` and `/prototype` are reachable.
- `/parent/progress` is hidden with 404.
- `/api/health` reports API and Redis readiness.
- Admin can test the real LLM connection.
- Teacher prompt generation calls the real LLM.
- Student Practice Mode grammar check calls the real LanguageTool-compatible service.
- Student Exam Mode suggestion check is blocked by backend policy.

Because this is a real smoke gate, LLM checks may create prompt draft and AI usage audit rows in the local demo
database. Use `CONFIRM_RESET=RESET_DEMO_DB scripts/dev/reset_demo_db.sh` before demos that need a clean seeded state.
