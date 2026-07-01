# Page IA Matrix

Status: working product-structure spec for replacing feature-pile pages with task-focused screens.

## Principle

Each page must answer one user question first. Secondary tools can exist, but they should sit behind tabs, filters, drawers, or detail panels instead of appearing as one long function list.

For this product, the user group is primary school teachers and P4-P6 pupils. The UI should not feel like a generic admin console. It should reduce classroom workload, use clear school language, protect students from confusion, and make teacher control explicit.

## Primary School UX Constraints

| Constraint | Product rule |
| --- | --- |
| Simple wording | Use concrete labels like `Set writing task`, `Mark writing`, `Submit writing`, `View feedback`; avoid abstract names like `workspace`, `engine`, `queue` in visible UI. |
| Few steps | Teacher task assignment should feel like choose class, choose writing, publish. Student writing should feel like open task, write, submit. |
| Clear next action | Every role home must show what to do next before showing history or tools. |
| Low student load | Student pages should show few choices, large actions, friendly text, and no dense tables. |
| Teacher efficiency | Teacher pages may be denser but must separate tasks: setup, marking, reports, rubrics and admin should not appear as one endless page. |
| Safe feedback | Student errors and empty states should be gentle and actionable. Teacher release remains the final control. |
| Prevent mistakes | Publish, release feedback, archive and destructive actions should be visibly deliberate. |
| Visible waiting | Long operations should say what is happening, for example `Saving...`, `Generating report...`, `Running AI marking...`. |
| Privacy by default | Do not expose class-wide scores to students. Teacher views must remain class-scoped. |

## Teacher And Student UX Priorities

| Audience | Design priority | Product implication |
| --- | --- | --- |
| Teachers | Reduce teaching workload. | Home page starts with today's attention items, pending marking and class progress before setup tools. |
| Teachers | Classroom use must be fast. | Core actions need large, obvious controls with minimal modal friction: start writing, publish task, review submissions, export report. |
| Teachers | Batch work matters. | Task assignment, marking filters, report export and account management should prefer class-level actions over one-student-at-a-time flows. |
| Teachers | Data must explain what to do. | Reports should translate scores and weaknesses into teaching signals, not just charts. |
| Teachers | Prevent accidental release or deletion. | Publish, release feedback, archive and destructive actions require clear confirmation and result feedback. |
| Students | Next task must be obvious. | Student Home shows `To do` first; history and older work are secondary. |
| Students | Reading burden must stay low. | Student labels should be short, direct and concrete; avoid technical status words. |
| Students | Click targets must be forgiving. | Main actions use large buttons and generous spacing, especially in writing and feedback pages. |
| Students | Feedback should protect confidence. | Error and empty states should say how to fix the issue, not simply say failure. |
| Students | Focus must be protected. | Writing screens avoid unrelated navigation, rankings, popups and decorative distractions. |

## Design Review Checklist

Use this before accepting a page as productized:

- Can a teacher understand what needs attention within 10 seconds?
- Can a teacher assign a writing task in roughly three steps: choose class, choose or create task, publish?
- Can a teacher quickly see which students have not submitted or still need review?
- Can a student tell the next action without reading a long instruction block?
- Can a student submit writing with one clear final action and a friendly confirmation?
- Can a student recover from mistakes through autosave, visible draft state or clear guidance?
- Are button labels concrete and consistent, for example `Submit`, `Start writing`, `View feedback`, `Export CSV`?
- Are icons paired with text, especially for student-facing actions?
- Are loading states visible for save, report generation, AI marking and export?
- Are student scores, names, emails and class-wide comparisons hidden unless the role is allowed to see them?
- Are destructive or high-impact actions protected by confirmation or deliberate secondary action?
- Does the page still work on a small laptop/tablet without horizontal overflow?

## Page Decisions

| Page | Primary user question | Primary actions | Data needed | Default visible content | Hidden or secondary content | Backend APIs |
| --- | --- | --- | --- | --- | --- | --- |
| Login | Can I get into my correct workspace? | Sign in. | Auth state, account status, role. | School identity, login form, error state. | Local health/debug details. | `POST /api/auth/login`, `GET /api/auth/session` |
| Student Home | What do I need to do next? | Continue open writing, start exam, view released feedback. | Profile, assigned tasks, draft/submission/release state. | Profile summary, one action queue grouped by To do and Feedback ready, with only a few tasks shown first. | Full task list behind `Show all`; submitted/history list behind Done work. | `GET /api/student/profile`, `GET /api/student/tasks` |
| Practice Editor | Can I write with useful grammar support? | Type, full check, accept/dismiss suggestion, submit. | Writing task, draft/submission, suggestions. | Editor canvas, autosave/word count, instruction, suggestion rail. | Released feedback link only after submit. | Writing workspace/draft/submit APIs, `POST /api/suggestions/check` |
| Exam Editor | Can I complete the timed writing task safely? | Type, submit, auto-submit. | Task, timer, draft/submission, exam events. | Editor canvas, timer, exam restrictions. | Suggestions and rewrite controls are absent. | Writing workspace/draft/submit APIs, exam event API |
| Student Feedback | What did I do well and what should I practise? | Complete post-writing exercises. | Released teacher review, AI feedback, exercises. | Scores, teacher review, focused exercises. | Raw AI metadata and unreleased feedback. | `GET /api/student/submissions/{id}/feedback`, exercise completion API |
| Teacher Overview | What needs my attention today? | Go to Marking, Tasks, Reports, Rubrics. | Classes, tasks, marking queue, report state. | Metrics, pending marking list, quick workbench navigation. | Creation forms and long lists. | Teacher class/task/rubric/marking/report APIs |
| Teacher Tasks | Can I create, assign, and manage writing tasks? | Create task, assign to class, publish/close/archive. | Rubrics, classes, tasks. | Task builder, assignment panel, active task list. | Rubric builder and report details. | Task/rubric/class/assignment APIs |
| Teacher Rubrics | Can I maintain school marking criteria? | Create rubric, duplicate, archive. | Rubrics, dimensions, used-by counts. | Rubric builder and rubric list. | Task assignment and marking queue. | Rubric APIs |
| Teacher Marking | Which submissions need review and release? | Run/retry marking, override scores, release feedback. | Submissions, AI marking results, teacher review draft. | Marking queue and selected submission review cards. | Report generation, task creation. | Marking run/review/release APIs |
| Teacher Reports | What is the class performance and can I export it? | Generate report, preview, export CSV/PDF. | Class report summary, breakdown, distribution, weaknesses, completion rows, export audit. | Class selector, report insights, export controls. | Task/rubric creation and marking forms. | Report APIs |
| Admin Overview | Is the school tenant ready for pilot? | Check AI status, go to import/classes/accounts. | AI service status, users, classes. | AI status and admin navigation. | CSV paste details and account table. | Admin AI/classes/users APIs |
| Admin Import | Can I safely import users? | Upload/paste CSV, preview, submit, inspect rejected rows. | CSV parse rows, import result. | Import form and validation result. | Account status actions. | Import API |
| Admin Classes | Can I maintain classes? | Create class, view membership counts. | Classes, teacher/student counts. | Class form and class table. | User import form. | Class APIs |
| Admin Accounts | Can I manage user access? | Suspend, restore, archive. | Users, role, status, class/staff code. | Account table with status actions. | CSV import controls. | User list/status APIs |

## First Refactor Scope

1. Student Home: show an action queue instead of every task. Submitted history is secondary.
2. Teacher Dashboard: add a workbench switcher and render only the active workspace by default.
3. Update E2E to navigate to workbench areas explicitly.

## Acceptance For This Refactor

- Student Home first viewport contains profile summary and a short next-action list, not a long historical task feed.
- Teacher Dashboard first viewport contains metrics and workbench navigation, not every form/list.
- Existing UAT flows still pass after selecting the relevant workbench.
- Mobile width does not horizontally overflow.
