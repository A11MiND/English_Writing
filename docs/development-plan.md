# Development Plan

Status: active progress tracker for the English AI Writing Platform.

This file is the visible checkpoint for what is done, what is next, and what evidence exists. Update it after each implementation batch so progress is not only stored in chat history.

## Current Progress

| Area | Status | Current Evidence | Next Action |
| --- | --- | --- | --- |
| Phase 0-8 Core Workflow | Done | API, web and E2E passing evidence in `docs/uat-readiness.md`. | Keep regression green while productizing UI. |
| Spec / PRD Traceability | Done | `docs/specs/14-requirements-traceability.md` maps PRD, Technical Proposal, spec-driven and UI requirements to current status. | Keep this updated after each implementation batch. |
| UI API Support | Done | Student task state, dashboard summary, marking filters, rubric count, task detail and exam events are implemented. | Wire these contracts into productized pages. |
| UI Productization | Doing | Matrix in `docs/design/ui-productization-matrix.md`; shared shell, page sections, writing editor and feedback first pass implemented. Catalyst is the reference style, not copied source. | Productize report visualizations, marking review details and mobile QA. |
| Security Gate | Doing | School, student and teacher scoping tests exist. | Add more route-level DB tests during UI integration. |
| Stress / UAT Evidence | Done for queue/load, partial for worker drain | Evidence under `docs/uat-evidence/`; full 470-essay LLM drain has not been run. | Run full provider-costed worker drain only with approval. |
| Deployment | Later | Docker Compose local environment is working. | Decide Render, Vercel or other cloud target later. |

## Working Rules

- Future development should happen from `/Users/allmind/Desktop/Edcosys2025/EngWriting` after migration.
- Keep `.env` local and untracked.
- Do not use runtime mocks for product behavior; real services should either work or fail clearly.
- Use project-owned React, Tailwind CSS and Headless UI components for the Catalyst-inspired UI direction.
- Record each substantial implementation batch in this file and in `docs/uat-readiness.md` when there is test evidence.

## Next Batch

| Priority | Work | Success Criteria |
| --- | --- | --- |
| 1 | Productize report visualizations. | Report preview uses clear score distribution, rubric breakdown and weakness presentation. |
| 2 | Continue Teacher/Admin detail polish. | Forms, tables and review states are easier to scan without changing APIs. |
| 3 | Add UI-focused regression coverage. | Playwright covers productized navigation and core UAT flows. |
| 4 | Add fuller NLP metrics layer. | Marking pipeline includes readability, lexical and sentence metrics as structured evidence. |
| 5 | Harden marking worker operations. | Worker has DLQ/backoff/metrics and a clear provider-costed 470-job drain plan. |

## Migration Checkpoint

2026-06-30:

- Migrated project to `/Users/allmind/Desktop/Edcosys2025/EngWriting`.
- Initialized local Git repository.
- Created checkpoint commit `b8b4d17 foundation-uat-api-support-checkpoint`.
- Verified `.env`, dependency directories and local caches are ignored by Git.
- Started the migrated Docker Compose stack from the new directory.
- Ran migrations, backend tests, frontend tests, lint and Playwright E2E successfully from the migrated directory.

## Spec Alignment Checkpoint

2026-06-30:

- Added `docs/specs/14-requirements-traceability.md`.
- Updated product scope, architecture and deployment specs to reflect the actual UAT-core implementation state.
- Confirmed the largest remaining gaps are UI productization, fuller NLP metrics, worker hardening and production operations.

## UI Productization Checkpoint

2026-06-30:

- Reworked the shared `AppShell` into a Catalyst-inspired sidebar and topbar layout using project-owned Tailwind components.
- Added reusable page-section classes for panels, metrics, navigation, badges and tables.
- Updated Student home with task-state metrics and clearer Practice/Exam task cards.
- Updated Admin console with AI status, CSV import, class management and account management anchors.
- Updated Teacher dashboard with overview metrics and focused Rubrics, Tasks, Reports and Marking anchors.
- Remaining UI work: productize Practice/Exam editor workspace, feedback page, report visualizations and focused mobile QA.

2026-07-01:

- Productized Practice and Exam writing workspaces into a stable editor canvas with sticky instruction/suggestion side panel.
- Preserved TipTap editing, autosave, Practice Mode suggestions, Exam Mode timer, paste blocking and all existing E2E selectors.
- Productized released feedback with metric score cards, teacher-feedback panel and post-writing exercise panel.
- Remaining UI work: report visualizations, marking review detail layout, Admin/Teacher table polish and mobile QA screenshots.
