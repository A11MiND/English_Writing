# Spec-driven Development Specification

# English AI Writing Platform 2026–2027

## 1. Purpose

This document defines the spec-driven development process for the English AI Writing Platform 2026–2027.

The purpose of spec-driven development is to prevent uncontrolled implementation, scope drift, hidden assumptions and ad-hoc coding. The platform shall be developed from explicit specifications, with each implementation task traceable to the PRD, Technical Proposal and UI/UX Screen Appendix.

No major feature shall be implemented without an accepted specification, an API contract, a data model definition and acceptance criteria.

## 2. Source Documents

The implementation shall use the following source documents as the authoritative requirements baseline:

Product Requirements Document(1).docx

Technical Proposal.docx

English_AI_Writing_Platform_Technical_Proposal_UIUX(2).docx

The implementation shall not add features outside these documents unless a new specification change is created and approved by the developer.

## 3. Development Principle

The project shall be implemented as a controlled school pilot first, not as a full Grammarly replacement.

The implementation shall follow these principles:

Build the smallest coherent vertical slice first.

Keep every feature traceable to PRD requirements.

Use explicit database schemas before writing API code.

Use explicit API contracts before writing frontend integration.

Use UI screen specifications before implementing pages.

Use test cases before marking a feature complete.

Use mock or adapter interfaces for external AI services before production integration.

Keep teacher review as the final assessment control.

Do not call LLM on every keystroke.

Do not implement out-of-scope modules.

## 4. Scope Boundary

### 4.1 In Scope for Initial Implementation

The initial implementation shall include:

One school tenant.

OpenAuth-based authentication.

Role-based access control.

Student account management.

Teacher account management.

Class management.

Writing task creation.

Rubric creation.

Student dashboard.

Teacher dashboard.

Practice Mode editor.

Exam Mode editor.

Autosave.

Submission locking.

Grammar suggestion interface.

Full overview job interface.

AI marking job interface.

Teacher review and override.

Feedback release.

Student feedback page.

Post-writing exercise page.

Class report page.

CSV export.

Audit log.

Basic admin console.

E2E testing.

UAT seed data.

### 4.2 Out of Scope

The implementation shall not include:

Microsoft Word add-in.

Google Docs add-on.

Browser extension.

Parent portal.

Plagiarism detection.

Handwriting OCR.

Native mobile app.

Real-time collaborative editing.

OS-level exam lockdown.

LMS integration.

Public API for third-party developers.

Multi-school billing.

AI model training using student submissions.

Unlimited AI usage.

24/7 support workflow.

## 5. Repository Structure

The repository shall use a monorepo structure.

Recommended structure:

english-ai-writing-platform/ docs/ source/ Product Requirements Document(1).docx Technical Proposal.docx English_AI_Writing_Platform_Technical_Proposal_UIUX(2).docx specs/ 00-spec-driven-development.md 01-product-scope.md 02-architecture.md 03-data-model.md 04-api-contract.md 05-auth-rbac.md 06-practice-mode.md 07-exam-mode.md 08-ai-marking.md 09-feedback-exercises.md 10-reports-export.md 11-uiux-screen-spec.md 12-testing-acceptance.md 13-deployment-operations.md adr/ ADR-001-monorepo-structure.md ADR-002-authentication-openauth.md ADR-003-editor-framework.md ADR-004-grammar-service.md ADR-005-ai-worker.md apps/ web/ api/ auth/ workers/ marking-worker/ services/ grammar-service/ packages/ shared/ schemas/ types/ constants/ infra/ docker/ migrations/ seed/ tests/ e2e/ stress/ fixtures/

## 6. Spec Hierarchy

The implementation shall be driven by the following spec hierarchy.

### 6.1 Level 1: Product Specification

File:

docs/specs/01-product-scope.md

Purpose:

Defines product scope, users, roles, modules, in-scope functions and out-of-scope functions.

Must include:

Product statement.

User roles.

Role permissions.

Feature list.

Scope exclusions.

Acceptance criteria.

### 6.2 Level 2: Architecture Specification

File:

docs/specs/02-architecture.md

Purpose:

Defines runtime architecture and component responsibilities.

Must include:

Next.js web app.

OpenAuth service.

FastAPI application API.

PostgreSQL database.

Redis cache and queue.

Grammar service.

AI marking worker.

Object storage.

Logging and monitoring.

Failure handling.

### 6.3 Level 3: Data Model Specification

File:

docs/specs/03-data-model.md

Purpose:

Defines all database tables and relationships before backend implementation.

Required tables:

schools

users

teacher_profiles

student_profiles

classes

class_memberships

writing_tasks

rubrics

rubric_dimensions

assignments

drafts

submissions

grammar_suggestions

marking_results

teacher_reviews

post_writing_exercises

class_reports

support_tickets

audit_logs

ai_usage_logs

exam_events

Data model rules:

Every school-owned table shall include school_id.

Every student-owned entity shall include student_id.

Every teacher-owned review shall include reviewed_by.

Every AI output shall include model_name, model_version, prompt_version and created_at.

Every export action shall be logged.

Every teacher override shall be logged.

### 6.4 Level 4: API Contract Specification

File:

docs/specs/04-api-contract.md

Purpose:

Defines API contracts before frontend and backend integration.

Required API groups:

/api/auth/session

/api/users

/api/classes

/api/tasks

/api/rubrics

/api/drafts

/api/submissions

/api/suggestions

/api/marking

/api/exercises

/api/reports

/api/support

/api/audit

/api/admin

Each endpoint specification must include:

Method.

Path.

Role access.

Request body.

Response body.

Error codes.

Validation rules.

Audit log requirement.

Test case reference.

### 6.5 Level 5: UI/UX Screen Specification

File:

docs/specs/11-uiux-screen-spec.md

Purpose:

Defines each screen before frontend implementation.

Required screens:

Login page.

Platform homepage.

Student dashboard.

Teacher dashboard.

Admin management page.

Practice Mode editor.

Exam Mode editor.

Overview feedback page.

Teacher marking review page.

Student feedback page.

Post-writing exercises page.

Data and report page.

Each screen spec must include:

Screen ID.

User role.

Route.

Required UI elements.

Required interactions.

API dependencies.

Empty states.

Error states.

Loading states.

Acceptance criteria.

## 7. Feature Specification Template

Every feature shall have a feature spec before implementation.

Template:

# Feature Spec: <Feature Name> ## Requirement Source - PRD section: - Technical Proposal section: - UI/UX section: ## User Story As a <role>, I need <capability>, so that <business value>. ## Functional Requirements - FR-001: - FR-002: - FR-003: ## Data Model Impact - Tables: - New columns: - Constraints: - Indexes: - Audit logs: ## API Contract - Endpoint: - Method: - Request: - Response: - Error codes: ## UI Contract - Route: - Components: - Loading state: - Empty state: - Error state: ## Security Rules - Required role: - Required school_id filter: - Required class/student ownership check: ## Acceptance Criteria - AC-001: - AC-002: - AC-003: ## Test Cases - Unit: - Integration: - E2E: - Security:

## 8. Implementation Order

The implementation shall follow this exact sequence.

### Phase 0: Foundation

Implement:

Monorepo.

Docker Compose.

Next.js app.

FastAPI app.

PostgreSQL.

Redis.

Alembic.

Shared type package.

Environment variable templates.

Health check endpoints.

Definition of Done:

Local dev environment starts from one command.

Frontend can call backend health endpoint.

Backend can connect to PostgreSQL.

Backend can connect to Redis.

Migrations can run.

README includes local startup steps.

### Phase 1: Authentication and RBAC

Implement:

OpenAuth service.

OAuth callback.

Session cookie.

User identity resolution.

Role mapping.

School tenant mapping.

RBAC middleware.

Audit log for login events.

Definition of Done:

Teacher can login.

Student can login.

Admin can login.

Suspended user cannot access app.

Archived user cannot access app.

Every protected API validates session.

Every protected API validates role.

### Phase 2: Core School Data

Implement:

School table.

User table.

Teacher profile.

Student profile.

Class table.

Class membership.

CSV import.

Account status management.

Admin page.

Definition of Done:

Admin can create school.

Admin can import teachers.

Admin can import students.

Invalid CSV rows are rejected.

Duplicate email is rejected.

Imported users can login.

Student belongs to correct class.

### Phase 3: Task and Rubric Workflow

Implement:

Writing task model.

Rubric model.

Rubric dimension model.

Assignment model.

Teacher task builder.

Rubric builder.

Task assignment.

Student dashboard visibility.

Definition of Done:

Teacher can create writing task.

Teacher can create rubric.

Teacher can assign task to class.

Student sees assigned task only.

Student cannot see draft task.

Teacher cannot see unassigned class data.

### Phase 4: Writing Editor

Implement:

Practice Mode editor.

Exam Mode editor.

Autosave.

Word count.

Draft model.

Submission model.

Submission locking.

Exam events.

Definition of Done:

Student can write in Practice Mode.

Student can write in Exam Mode.

Autosave works without blocking typing.

Submit locks submission.

Exam Mode disables real-time suggestions.

Exam Mode blocks paste.

Paste attempt is logged.

Timer works when configured.

### Phase 5: Grammar Suggestion Engine

Implement:

Suggestion API.

Changed-range detection.

Debounce logic.

Grammar service adapter.

Redis cache.

Suggestion normalisation.

Inline highlights.

Suggestion panel.

Accept suggestion.

Dismiss suggestion.

Stale overview indicator.

Definition of Done:

Practice Mode displays inline suggestion.

Suggestion maps to correct text span.

Student can accept suggestion.

Student can dismiss suggestion.

Editing one sentence invalidates affected suggestions only.

LLM is not called for normal grammar checks.

Grammar service failure does not block writing.

### Phase 6: AI Marking Engine

Implement:

Marking job queue.

Worker.

Grammar result aggregation.

NLP metric extraction.

LLM marking adapter.

Prompt versioning.

JSON schema validation.

Marking result persistence.

Retry handling.

Teacher review page.

Teacher score override.

Definition of Done:

Submission creates marking job.

Worker generates marking result.

Marking output validates against schema.

Invalid output is retried.

Failed marking does not delete submission.

Teacher can override score.

Override is logged.

Student cannot see feedback before release.

### Phase 7: Feedback and Exercises

Implement:

Student feedback page.

Feedback release workflow.

Post-writing exercise generation.

Exercise completion.

Teacher exercise completion view.

Definition of Done:

Teacher can release feedback.

Student can view released feedback.

Student cannot view unreleased feedback.

Post-writing exercise is generated.

Student can complete exercise.

Teacher can view completion status.

### Phase 8: Reports and Export

Implement:

Class report.

Score distribution.

Rubric dimension breakdown.

Common strengths.

Common weaknesses.

CSV export.

PDF export.

Export audit log.

Definition of Done:

Teacher can generate class report.

Teacher can view assigned class report only.

CSV export works.

PDF export works.

Export action is logged.

### Phase 9: Hardening and Release

Implement:

Unit tests.

Integration tests.

Playwright E2E tests.

Stress test scripts.

Security tests.

Seed data.

Backup script.

Deployment guide.

UAT checklist.

Definition of Done:

Critical E2E tests pass.

UAT seed data is available.

Stress test scripts are runnable.

No unresolved critical defect.

Production deployment checklist is complete.

## 9. Testing Standard

### 9.1 Unit Tests

Required unit tests:

Role validation.

school_id filtering.

class ownership filtering.

student ownership filtering.

CSV import validation.

Rubric score calculation.

Word count.

Lexical density calculation.

Grammar suggestion normalisation.

AI output schema validation.

### 9.2 Integration Tests

Required integration tests:

Login callback to app session.

Teacher creates task.

Teacher assigns task.

Student receives task.

Student submits writing.

Marking job created.

Teacher reviews marking.

Feedback released.

Student views feedback.

Report exported.

### 9.3 E2E Tests

Required Playwright E2E tests:

Teacher login and logout.

Student login and logout.

Admin imports users.

Teacher creates rubric.

Teacher creates task.

Teacher assigns task.

Student opens Practice Mode.

Student receives suggestion.

Student accepts suggestion.

Student submits Practice Mode writing.

Student opens Exam Mode.

Paste is blocked.

Timer works.

Student submits Exam Mode writing.

AI marking job completes.

Teacher overrides score.

Teacher releases feedback.

Student views feedback.

Teacher generates report.

Teacher exports CSV.

### 9.4 Stress Tests

Required stress tests:

150 students login within 10 minutes.

100 concurrent students write with autosave and grammar suggestions.

470 students submit within 30 minutes.

470 essays queued for marking.

Teacher generates class report after marking.

Pass standard:

No essay is lost.

Submission remains saved even if marking fails.

Editor remains usable.

Autosave continues.

Failed AI jobs can be retried.

Report exports work.

## 10. Security Rules

The implementation must enforce:

Every protected endpoint validates session.

Every protected endpoint validates role.

Every school-owned query filters by school_id.

Teacher queries filter by assigned class.

Student queries filter by student_id.

Student name and email are not sent to LLM provider.

Submitted essay is treated as untrusted input.

Prompt injection inside essay shall not override marking instruction.

AI output is schema-validated.

HTML content is sanitised before rendering.

Production secrets are never committed.

Export actions are logged.

## 11. External Service Adapters

External services shall be accessed through adapters.

Required adapters:

AuthAdapter

GrammarCheckAdapter

LLMAdapter

NlpMetricsAdapter

StorageAdapter

EmailAdapter

Each adapter shall have:

Interface.

Production implementation.

Mock implementation.

Unit tests.

The initial implementation may use mock LLM and mock email while preserving the production adapter interface.

## 12. Definition of Done

A feature is complete only when:

Feature spec exists.

Data model is implemented.

API contract is implemented.

Frontend screen is implemented.

Role access is enforced.

school_id isolation is enforced.

Unit tests are added.

Integration or E2E test is added.

Audit logging is added where required.

Error states are handled.

Empty states are handled.

Loading states are handled.

Documentation is updated.

## 13. Development Constraint for Codex

Codex shall not implement a feature by guessing missing requirements.

When information is missing, Codex shall:

Create a TODO_DECISION.md entry.

Propose the smallest safe default.

Implement an adapter or placeholder only when it does not break the architecture.

Avoid adding out-of-scope features.

Keep all implementation traceable to the specs.
