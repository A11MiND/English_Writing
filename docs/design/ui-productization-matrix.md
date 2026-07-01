# UI Productization Matrix

Status: design planning draft for review before implementation.

## Design Brief

Build a school-pilot-ready English AI Writing Platform for W F Joseph Lee Primary School. The UI should feel like a serious education operations product: quiet, dense, readable, and workflow-driven. Catalyst by Tailwind Labs is the visual reference for component quality, spacing discipline, responsive sidebar layout, forms, tables, badges, dropdowns and dialogs. Do not copy Catalyst proprietary source; implement our own React/Tailwind components inside this codebase.

Interactivity target: full working UAT flows, not static mockups.

## Catalyst-Inspired Implementation Ledger

Reference: Tailwind Plus Catalyst screenshots supplied by the user on 2026-07-01.

| Reference trait | Local implementation rule |
| --- | --- |
| Rounded application frame on a neutral gray canvas | Use one full-height app frame with light gray sidebar and white content workspace. |
| Left sidebar with icon + text navigation | Use role-safe sidebar items with code-owned SVG icons and visible labels. |
| Bottom user block in sidebar | Show role user identity in sidebar footer; keep logout in the top action area. |
| Overview metrics with thin top rules | Prefer subtle divided metrics over floating card grids for dashboards. |
| Forms, buttons and tables with restrained borders and small shadows | Standardize `btn`, `form-control`, `table-shell`, `status-pill` and panel classes globally. |
| Professional density | Teacher/Admin pages can be denser and table-first; Student pages keep fewer choices and larger task actions. |
| Proprietary Catalyst source | Do not copy source or component APIs from Catalyst; build project-owned React/Tailwind components. |

## Page Inventory

| # | Surface | Route / component | Primary role | Current status | Productization priority |
| --- | --- | --- | --- | --- | --- |
| 1 | Login | `/`, `LoginPage` | All | Functional | High |
| 2 | Role redirect / platform home | `/`, session redirect | All | Minimal | Medium |
| 3 | Student home | `/student`, `StudentHome` | Student | Functional | High |
| 4 | Practice editor | `/student/tasks/:id`, `WritingEditor` | Student | Functional | High |
| 5 | Exam editor | `/student/tasks/:id`, `WritingEditor` | Student | Functional | High |
| 6 | Student feedback | `/student/submissions/:id`, `StudentFeedback` | Student | Functional | High |
| 7 | Teacher overview | `/teacher`, `TeacherDashboard` | Teacher | Functional but crowded | High |
| 8 | Task builder / assignment | `/teacher`, `TeacherDashboard` section | Teacher | Functional | High |
| 9 | Rubric builder | `/teacher`, `TeacherDashboard` section | Teacher | Functional | Medium |
| 10 | Marking review | `/teacher`, `TeacherDashboard` section | Teacher | Functional | High |
| 11 | Data / reports | `/teacher`, `TeacherDashboard` section | Teacher | Functional | High |
| 12 | Admin management | `/admin`, `AdminConsole` | School admin | Functional | High |

## Presentation Options

These options are reused across pages so we can compare design directions consistently.

| Option | Shape | Best for | Tradeoff |
| --- | --- | --- | --- |
| A. Catalyst operations shell | Left sidebar, top user bar, dense content panels, tables, badges, dialogs. | Teacher/Admin workflows, repeated daily operations. | Can feel utilitarian if student writing screens are not softened. |
| B. Task-focused workspace | Single dominant work area with contextual right rail and minimal navigation. | Practice Mode, Exam Mode, Marking Review. | Less useful for overview-heavy pages unless paired with dashboard entry points. |
| C. Guided wizard / stepper | Sequential flow with validation at each step. | CSV import, task creation, report generation, first-time admin setup. | Slower for expert users if every task is forced through a wizard. |

Recommended system direction: combine A for shell/admin/teacher dashboards, B for writing and marking workspaces, and C only where validation reduces user mistakes.

## Page Matrix

| Surface | User goal | Data displayed | User actions | Backend APIs | Option A | Option B | Option C | Recommended direction | UX improvements |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Login | Sign in and land in the correct role workspace. | School name, login state, error state, account status. | Submit credentials. | `POST /api/auth/login`, `GET /api/auth/session`, `POST /api/auth/logout` | Center auth card in Catalyst-style shell. | Split screen with school context and form. | Compact modal-style form. | B: split screen, because it gives the school identity room without becoming marketing. | Show suspended/archived/invalid credentials clearly; loading button state; no token storage; role redirect feedback. |
| Role redirect / platform home | Resume current session or send user to login. | Current user role, health status if unauthenticated dev mode. | Continue to role home, logout. | `GET /api/auth/session`, `GET /api/health` | Small status page. | Automatic redirect with loading state. | Role card chooser. | B for production; A for local health only. | Avoid a fake landing page; show concise loading and fallback error if session probe fails. |
| Student home | Understand assigned work and what needs action. | Profile, class, assigned tasks, mode, due date, submitted/locked status, feedback links. | Open Practice, open Exam, view feedback. | `GET /api/student/profile`, `GET /api/student/tasks`, later optional submission-status summary API. | Task table grouped by mode. | Task cards with progress and action buttons. | Calendar/deadline list. | B: task cards grouped into To write / Submitted / Feedback available. | Make Practice vs Exam visually distinct; show lock/submitted state; avoid showing draft/unassigned tasks; surface feedback availability. |
| Practice editor | Write fluently with autosave and grammar suggestions. | Task prompt, word range, editor content, word count, autosave state, suggestions, stale/full-check state. | Type, autosave, full check, accept/dismiss suggestions, submit. | `GET /api/student/tasks/{task_id}/writing`, `PUT /api/student/tasks/{task_id}/draft`, `POST /api/suggestions/check`, `POST /api/student/tasks/{task_id}/submit` | App shell + editor page. | Full workspace: editor center, suggestions right rail, prompt/metadata top bar. | Tabbed writing/checking flow. | B: dedicated writing workspace. | Strong autosave visibility; suggestion spans stable; submit confirmation; locked read-only state; no LLM on keystrokes. |
| Exam editor | Complete a timed restricted browser writing task. | Prompt, timer, word count, autosave, exam event state, locked submission. | Type, autosave, submit, timer auto-submit; paste blocked. | Writing workspace APIs, `POST /api/student/tasks/{task_id}/exam-events` | Same as Practice with suggestions hidden. | Focus mode with timer top bar and prompt side panel. | Step-based start confirmation then editor. | B with a pre-start confirmation if time permits. | No suggestion/rewrite controls; paste block feedback; blur/focus status; clear timer warning; auto-submit state. |
| Student feedback | Understand released feedback and complete exercises. | Task/submission summary, scores, teacher review, AI feedback, strengths, weaknesses, exercises. | Complete exercises. | `GET /api/student/submissions/{submission_id}/feedback`, `POST /api/student/exercises/{exercise_id}/complete` | Report-style page with sections. | Essay-centric view with feedback rail. | Score-first tabbed view. | A now; B later if sentence-level comments become richer. | Separate teacher final review from AI feedback; show only released feedback; exercise completion status; avoid overwhelming pupils. |
| Teacher overview | See classes, pending marking, report status and next actions. | Assigned classes, tasks, submissions, AI marking statuses, unreleased feedback count. | Navigate to task, marking, report sections. | `GET /api/teacher/classes`, `GET /api/teacher/tasks`, `GET /api/teacher/marking/submissions`, reports APIs. | Dashboard with metrics and queues. | Class-first workspace. | Task-first workspace. | A with class/task filters. | Reduce current crowded single-page feel; surface pending work; sticky filters for class/task/mode. |
| Task builder / assignment | Create task, publish it, assign to class. | Rubrics, classes, current task fields, assignment state. | Create/edit/publish/archive task; assign class. | `GET/POST/PATCH /api/teacher/tasks`, `POST /api/teacher/tasks/{task_id}/assignments`, `GET /api/teacher/rubrics`, `GET /api/teacher/classes` | Table plus side panel editor. | Inline form with live preview. | Wizard: details -> rubric -> assignment -> publish. | C for create flow, A for management list. | Prevent publish without rubric; validate Exam duration; clear draft/published/closed/archive states; show assigned classes. |
| Rubric builder | Maintain school rubric dimensions. | Rubric list, dimensions, score ranges, status. | Create, duplicate, archive, edit-before-use. | `GET/POST/PATCH /api/teacher/rubrics`, `POST /api/teacher/rubrics/{rubric_id}/duplicate` | Rubric table + detail panel. | Dimension card editor. | Rubric template wizard. | A with detail panel; C only for new rubric. | Show total score consistency; clarify archive vs delete; warn when rubric is used by tasks. |
| Marking review | Review AI output, override scores, release feedback. | Submission, essay text, AI result, confidence, warning flags, teacher review form, release state. | Run/retry marking, save review, release feedback. | `GET /api/teacher/marking/submissions`, `POST /api/teacher/marking-results/{id}/run`, `/retry`, `/review`, `/release` | Queue table + detail drawer. | Submission review workspace with essay left and marking right. | Stepper: AI result -> teacher review -> release. | B for actual review; A for queue landing. | Validate 0-5 dimensions; show failed AI state; make release a deliberate final action; show audit/override state. |
| Data / reports | See class analytics and export evidence. | Completion, rubric breakdown, distribution, weaknesses, completion rows, export audit. | Generate report, preview, export CSV/PDF. | `GET /api/teacher/reports/classes/{class_id}`, `POST /generate`, `GET /export.csv`, `GET /export.pdf`, `GET /exports` | Analytics dashboard + table. | Report document preview. | Export wizard. | A now; B for PDF preview later. | Show export status/filename/size; audit history; CSV/PDF errors; assigned-class filter. |
| Admin management | Maintain users, classes and service status. | Users, statuses, classes, import preview/result, AI status. | Import CSV, create class, suspend/restore/archive accounts. | `GET /api/admin/users`, `POST /api/admin/import/users`, `GET/POST /api/admin/classes`, `PATCH /api/admin/users/{id}/status`, `GET /api/admin/ai/status` | Account table with import panel. | Admin dashboard cards by domain. | Import wizard with row validation report. | A for account/class management, C for CSV import. | File metadata and parse preview; rejected rows grouped by reason; destructive action confirmation; never expose API keys. |

## API And Data Gaps To Resolve Before UI Build

| Gap | Why it matters for UI | Suggested backend contract |
| --- | --- | --- |
| Student task status summary | Student home needs to show Submitted / Draft saved / Feedback ready without opening each task. | Done: `GET /api/student/tasks` now includes `draft_status`, `draft_saved_at`, `submission_id`, `submission_status`, `submitted_at`, `locked`, `feedback_released`. |
| Teacher dashboard counts | Overview needs metrics without deriving from huge lists. | Done: `GET /api/teacher/dashboard-summary?class_id=&task_id=` returns assigned class count, active task count, submitted count, pending marking count, unreleased feedback count and marking status counts. |
| Marking queue filters | Marking review needs class/task/status filters. | Done: `GET /api/teacher/marking/submissions` accepts `class_id`, `task_id`, `status`. Pagination remains future work. |
| Rubric used-by task count | UI needs to warn before edits/archive. | Done: `GET /api/teacher/rubrics` includes `used_by_task_count`, counted from school-scoped writing tasks. |
| Task detail endpoint | Edit screen should load one task cleanly. | Done: `GET /api/teacher/tasks/{task_id}` returns task detail with assigned classes. |
| Exam event review | Teachers may need to inspect paste/blur events. | Done: `GET /api/teacher/submissions/{submission_id}/exam-events`, scoped by assigned class, returns ordered local exam audit events. |
| Feedback availability on Student home | Pupils need direct feedback action only when released. | Add released feedback metadata to task/submission summary. |
| Report task filter | UI should generate reports by task or all tasks. | Existing report APIs already accept `task_id`; expose task selector clearly in frontend. |

## UX Improvements By Feature Area

| Feature | Current risk | UX improvement |
| --- | --- | --- |
| Authentication | User may not know why login failed. | Distinguish invalid credentials, suspended, archived, OpenAuth unavailable. |
| CSV import | Admin can paste malformed CSV and only see broad errors. | Dedicated import stepper: upload -> parse preview -> submit -> rejected-row report. |
| Practice suggestions | Students may over-trust suggestions or lose context after edits. | Show affected sentence, replacement preview, accept/dismiss, stale overview indicator. |
| Exam mode | Students may misunderstand “restricted browser” as secure lockdown. | Use precise copy: suggestions disabled, paste blocked, focus events logged; no OS lockdown claim. |
| AI marking | Teachers may think AI is final. | Position teacher review as final control; release button separate and explicit. |
| Feedback | Students may confuse AI feedback with teacher judgement. | Label teacher final score/review first, AI guidance second. |
| Reports | Export success can be invisible. | Show filename, format, size, timestamp and audit list after each export. |
| Account status | Suspend/archive can be accidental. | Confirmation dialog with effect description; restore action visible. |

## Recommended Build Order

1. Add API gaps needed for UI state: student task status summary, teacher dashboard summary, marking filters.
2. Build shared UI primitives in `apps/web/src/components/ui/`: button, input, textarea, select, table, badge, alert, dialog, sidebar shell, page heading.
3. Split `TeacherDashboard` into focused sections: overview, task builder, marking review, reports.
4. Productize Student home, Practice editor and Exam editor.
5. Productize Admin CSV import and account management.
6. Productize reports and feedback pages.
7. Run Playwright visual screenshots for desktop and mobile before sign-off.

## Open Decisions For User Review

- Student home should use task cards grouped by status, not a dense table.
- Practice editor should use a dedicated writing workspace with right suggestion rail.
- Exam editor should use a focused workspace with top timer and no suggestion rail.
- Teacher dashboard should become an operations shell with separate review/report/task areas.
- Admin CSV import should become a guided import flow.

Confirm or revise these before implementation.
