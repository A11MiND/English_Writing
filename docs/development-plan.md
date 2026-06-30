# Development Plan

Status: active progress tracker for the English AI Writing Platform.

This file is the visible checkpoint for what is done, what is next, and what evidence exists. Update it after each implementation batch so progress is not only stored in chat history.

## Current Progress

| Area | Status | Current Evidence | Next Action |
| --- | --- | --- | --- |
| Phase 0-8 Core Workflow | Done | API, web and E2E passing evidence in `docs/uat-readiness.md`. | Keep regression green while productizing UI. |
| UI API Support | Done | Student task state, dashboard summary, marking filters, rubric count, task detail and exam events are implemented. | Wire these contracts into productized pages. |
| UI Productization | Doing | Matrix in `docs/design/ui-productization-matrix.md`. Catalyst is the reference style, not copied source. | Build a Catalyst-inspired app shell and page sections. |
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
| 1 | Migrate project to Desktop `EngWriting` and create local Git checkpoint. | Target directory has a clean first commit and `.env` remains untracked. |
| 2 | Productize shared app shell. | Student, Teacher and Admin pages use one consistent sidebar/topbar layout. |
| 3 | Split Teacher dashboard into focused workspaces. | Overview, task/rubric, marking and reports are easier to scan and use. |
| 4 | Productize Student home and writing editors. | Practice and Exam flows are visually distinct and preserve all current behavior. |
| 5 | Add UI-focused regression coverage. | Playwright covers the productized navigation and core UAT flows. |
