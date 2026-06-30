# 11 UIUX Screen Spec

Status: Phase 4 baseline.

## Authoritative Sources

- `docs/source_extracted/English_AI_Writing_Platform_Technical_Proposal_UIUX(2).md`

## Required Pages

- Login page
- Platform homepage
- Student home
- Teacher dashboard
- Admin management
- Practice Mode
- Exam Mode
- Overview / feedback
- Data / report page

## UI Productization Method

Before changing production UI components, create a page-by-page design matrix. The matrix must answer:

1. What is the page trying to help the user complete?
2. What data must be displayed, edited or submitted?
3. Which backend APIs provide or mutate that data?
4. Which UX risks can cause teacher/student/admin mistakes?
5. What are at least three viable presentation options?
6. Which option is selected and why?

Do not start by simply restyling existing Tailwind classes. Productization must start from user goals and data shape, then move into component implementation. Catalyst-style React/Tailwind patterns may be used as visual inspiration only if the actual components are implemented inside this codebase and no paid/proprietary source is copied.

Detailed page-by-page productization matrix: `docs/design/ui-productization-matrix.md`.

## Productization Page Matrix Draft

| Page | Primary user goal | Data / API dependencies | Option A | Option B | Option C | UX improvements required |
| --- | --- | --- | --- | --- | --- | --- |
| Login | Enter the correct role workspace with clear account-state feedback. | `POST /api/auth/login`, `GET /api/auth/me`, `POST /api/auth/logout` | Centered auth card with school identity. | Split layout with school context and form. | Compact modal-style login over neutral background. | Clear suspended/archived messaging, no localStorage tokens, visible role redirect state. |
| Platform homepage | Route authenticated users to the right role home. | `GET /api/auth/me`, `GET /api/health` | Role-aware dashboard cards. | Minimal redirect/loading shell. | Status-oriented pilot landing page. | Avoid marketing copy; show only actionable role entry and system status. |
| Student home | Let students see assigned writing tasks and feedback actions. | `GET /api/student/profile`, `GET /api/student/tasks`, feedback/exercise endpoints | Task list grouped by mode. | Calendar/deadline-oriented list. | Progress dashboard with task cards. | Make Practice vs Exam unmistakable, hide draft/other-class tasks, show submitted/locked state. |
| Practice Mode | Write, autosave, receive grammar suggestions and submit safely. | `GET /api/student/tasks/{id}/writing`, `PUT /draft`, `POST /submit`, `POST /api/suggestions/check` | Editor + right suggestion rail. | Editor with collapsible suggestion drawer. | Split editor and diagnostics tabs. | Debounced suggestions, stale indicator, accept/dismiss clarity, submit confirmation, locked read-only state. |
| Exam Mode | Complete timed restricted browser writing without suggestions. | Writing workspace, draft/submit, `POST /exam-events` | Focused editor with timer top bar. | Two-column prompt/editor exam layout. | Full-screen writing canvas with event log status. | Paste block feedback, blur/focus logging visibility, timer auto-submit warning, no suggestion/rewrite controls. |
| Teacher dashboard | Understand class writing activity and next actions. | `GET /api/teacher/classes`, tasks/rubrics/marking/report APIs | Operational dashboard with queues. | Class-first dashboard. | Task-first dashboard. | Separate creation from review work, show errors, highlight unmarked/unreleased items. |
| Task builder | Create/edit/publish/archive tasks and assign classes. | `/api/teacher/tasks`, `/assignments`, `/rubrics`, `/classes` | Wizard: task -> rubric -> assignment. | Single-page form with side preview. | Table list + slide-over editor. | Prevent publishing without rubric, clarify draft vs published, validate Exam duration. |
| Rubric builder | Manage school-based scoring dimensions. | `/api/teacher/rubrics`, duplicate/archive endpoints | Dimension table editor. | Card editor per dimension. | Rubric library with detail panel. | Lock or warn after rubric is used, show total score consistency. |
| Marking review | Review AI marking, override scores and release feedback. | `/api/teacher/marking/submissions`, `/run`, `/review`, `/release` | Submission list + review panel. | Queue table + detail drawer. | Class/task grouped marking board. | Show AI status/failures, validate 0-5 scores, release only through explicit teacher action. |
| Student feedback | Read released feedback and complete exercises. | `GET /api/student/submissions/{id}/feedback`, `POST /api/student/exercises/{id}/complete` | Feedback report with exercise cards. | Essay-centric annotated view. | Score-first overview with tabs. | Hide unreleased feedback, distinguish teacher override from AI suggestion, track exercise completion. |
| Admin management | Maintain school users/classes and AI service visibility. | `/api/admin/users`, `/import/users`, `/classes`, `/ai/status` | Account table + import panel. | Import-first workflow with validation report. | Admin dashboard sections by data domain. | CSV file preview, rejected row report, suspend/archive safety, never expose API keys. |
| Data / reports | Generate class analytics and export evidence. | `/api/teacher/reports/classes/{id}`, `/generate`, `/export.csv`, `/export.pdf`, `/exports` | Analytics dashboard + export rail. | Report document preview. | Class comparison table with drilldown. | Show completion, rubric breakdown, weaknesses, export audit, CSV/PDF status and errors. |

The selected option for each page must be confirmed before implementation. API gaps discovered during UI design should be added to the backend contract before final visual work begins.

## Phase 0 Note

Phase 0 includes only a local foundation homepage with backend health status. Product screens begin after their specs are completed.

## Phase 1-2 Baseline Screens

- Login page replaces the Phase 0 foundation screen.
- Student home, teacher dashboard and admin console are role-protected.
- Admin console includes basic user list, class list and CSV import textarea.
- UI polish is intentionally deferred; Phase 2 prioritises working data and access-control flows.

## Phase 3 Baseline Screens

- Teacher dashboard includes assigned classes, active tasks, task builder, rubric builder and class assignment flow.
- Task builder captures title, level, instruction, writing mode, word limits, due date, rubric and status.
- Rubric builder captures title, level, total score and ordered dimensions for Content, Language and Organisation.
- Assignment flow lets teachers assign a task only to one of their assigned classes.
- Student home lists assigned published tasks with Practice Mode / Exam Mode labels and hides draft or other-class tasks.

The Phase 3 UI remains utilitarian. Visual polish is deferred until the writing editor and suggestion surfaces exist.

## Phase 4 Baseline Screens

- Practice Mode page uses a top bar, main TipTap writing editor, word count, autosave status, instruction panel and submit button.
- Practice Mode shows a disabled suggestion placeholder only; real grammar suggestions start in Phase 5.
- Exam Mode page uses a restricted writing layout with task prompt, timer when configured, word count, autosave status and submit button.
- Exam Mode does not render suggestion or AI rewrite controls.
- Exam Mode blocks paste and records paste/focus events.
- Submitted writing displays in read-only mode.
