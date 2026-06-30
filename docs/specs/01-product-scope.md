# 01 Product Scope

Status: UAT core controlled-pilot baseline implemented. Production rollout remains out of scope until deployment and operations work is completed.

## Authoritative Sources

- `docs/source/Product Requirements Document(1).docx`
- `docs/source/Technical Proposal.docx`
- `docs/source/English_AI_Writing_Platform_Technical_Proposal_UIUX(2).docx`
- `docs/specs/00-spec-driven-development.md`

## Controlled Pilot Scope

- One-school English AI Writing Platform for W F Joseph Lee Primary School.
- Target users: P4 to P6 students, teachers, school administrators and system administrators.
- Target pilot volume: approximately 470 students.
- Annual writing scope: 11 writing topics across P4, P5 and P6.
- Core modules: student portal, teacher portal, admin console, Practice Mode, Exam Mode, grammar suggestions, AI-assisted marking, teacher review/override, feedback release, post-writing exercises, class reports and CSV/PDF export.
- Local/UAT runtime: Next.js web app, FastAPI API, OpenAuth-compatible auth service, PostgreSQL, Redis, LanguageTool-compatible grammar service and marking worker through Docker Compose.
- Parent portal, LMS integration, Word add-in, Google Docs add-on, plagiarism detection, handwriting OCR and native mobile apps are out of scope.

## Current UAT Evidence

- `docs/uat-readiness.md` records passing UAT-core browser E2E for login, admin import, teacher task/rubric/assignment, Practice suggestions, Exam timer/paste block, real LLM marking, teacher override/release, student feedback and class report export.
- `docs/uat-evidence/` stores stress/export evidence for the local controlled-pilot load pass.
- `docs/specs/14-requirements-traceability.md` maps PRD, Technical Proposal, spec-driven and UI requirements to current implementation status and remaining gaps.

## Remaining Scope Before Production

- Productize UI to a school-pilot presentation standard.
- Add fuller NLP metrics beyond current minimal marking metrics.
- Harden worker operations, monitoring and dead-letter handling.
- Complete production deployment, backup, logging and incident runbooks.
