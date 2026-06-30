# 14 Requirements Traceability

Status: UAT core alignment snapshot on 2026-06-30.

## Authoritative Sources

- `docs/source_extracted/Product Requirements Document(1).md`
- `docs/source_extracted/Technical Proposal.md`
- `docs/source_extracted/Spec-driven Development Specification.md`
- `docs/source_extracted/English_AI_Writing_Platform_Technical_Proposal_UIUX(2).md`
- `docs/design/ui-productization-matrix.md`
- `docs/uat-readiness.md`

## Alignment Summary

| Requirement Area | Current Status | Evidence | Remaining Gap |
| --- | --- | --- | --- |
| One-school P4-P6 controlled pilot | UAT core implemented | Seed school, classes, users, tasks and UAT fixture tooling | Production deployment and live school data onboarding are not complete. |
| Authentication and RBAC | UAT core implemented | OpenAuth-compatible local service, HTTP-only sessions, role checks, account status tests | Production OpenAuth provider/version lock and password reset/email flow remain. |
| Core school data | UAT core implemented | Admin CSV import, duplicate/invalid row tests, class membership tests | Admin import UX needs productization and support workflow copy. |
| Task and rubric workflow | UAT core implemented | Teacher task/rubric APIs, used-rubric lock behavior, assignment enforcement | UI needs wizard/detail panels and clearer draft/publish/archive controls. |
| Practice Mode | UAT core implemented | TipTap editor, autosave, LanguageTool suggestions, Redis cache, E2E accept/submit | Visual polish and suggestion UX need productization. |
| Exam Mode | UAT core implemented | Timer, paste block, focus/paste event logging, auto-submit E2E | Teacher-facing exam event review UI needs integration. |
| Grammar service | UAT core implemented | LanguageTool-compatible adapter, normalized suggestions, cache tests | Production service sizing/monitoring remain. |
| AI marking | UAT core implemented | Redis job creation, worker path, real LLM provider adapters, schema validation, teacher override/release | NLP metrics are still minimal; worker DLQ/backoff/metrics and 470-job live drain remain. |
| Feedback and exercises | UAT core implemented | Released-feedback gating, exercise generation/completion tests | Teacher completion summary and exercise customization remain. |
| Reports and export | UAT core implemented | Class report, CSV/PDF export, audit log, E2E download | PDF visual design and production export styling need polish. |
| Security | UAT core implemented | Tenant/student/teacher scope tests, HTML sanitizer, prompt-injection test, no browser token storage | Production headers, audit retention and operational monitoring remain. |
| Stress / scale | Local UAT evidence captured | 150 logins, 100 concurrent writing users, 470 submissions, 470 queued jobs | Full live LLM worker drain and production capacity test are not run. |
| UI / UX | Functional baseline | Required pages exist and UI matrix defines target patterns | Catalyst-inspired product UI is the largest remaining product gap. |
| Deployment / operations | Local baseline | Docker Compose stack runs from `EngWriting`; migrations/tests pass | Managed services, backups, logs, runbooks and provider ops are not implemented. |

## Do-Not-Build Scope Confirmation

The implementation continues to exclude parent portal, LMS integration, Word add-in, Google Docs add-on, plagiarism detection, handwriting OCR, native mobile application and OS-level secure exam lockdown. These exclusions match the PRD and Technical Proposal controlled-pilot scope.

## Next Alignment Actions

1. Productize UI according to `docs/design/ui-productization-matrix.md`.
2. Add a fuller NLP metrics service layer and persist metrics used for marking evidence.
3. Harden the marking worker with dead-letter queue, retry backoff and metrics.
4. Add production deployment/operations plan with managed PostgreSQL/Redis, backups, logs and runbooks.
5. Run a separately approved provider-costed worker drain test for 470 essays.
