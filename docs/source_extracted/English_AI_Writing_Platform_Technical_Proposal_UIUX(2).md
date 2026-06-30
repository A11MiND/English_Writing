# English AI Writing Platform 2026-2027

Technical Proposal with UI/UX Screen Appendix

Prepared by: Edcosys

Target School: W F Joseph Lee Primary School

School Ref. No.: Q17/2526

Target Levels: P4 to P6

Target Student Volume: Approximately 470 students

Annual Writing Topics: P4: 4 topics; P5: 4 topics; P6: 3 topics

Authentication: OpenAuth

Frontend: Next.js, TypeScript, Tailwind CSS

Backend: FastAPI, SQLAlchemy

Database: PostgreSQL

Version: 1.1

Date: 27 June 2026

UI/UX image policy: screenshots only. The Grammarly screens are client-provided reference screenshots. The platform screens are captured from local browser-rendered prototype pages. No AI-generated images are used in this document.

# 1. Quotation Requirement Reference

The school quotation form requests an English AI Writing Platform covering school-based writing tasks, student accounts, teacher accounts, entry/token control, instant auto-marking, school-based rubrics, individualised feedback, post-writing exercises, class-based reports and technical support.

Figure 1. School written quotation form reference provided by client.

# 2. PRD Review Notes

Item

Review Comment

Required Adjustment

AI grading with HMIT

The intended term should be HITL: Human-in-the-loop.

Use teacher-supervised AI marking and teacher override as the final assessment control.

Practice Mode

Do not call LLM on every keystroke.

Use editor delta detection, debounce, self-hosted grammar checking, cache and delayed LLM overview.

LLM marking

Prompt-only scoring is not sufficient for consistency.

Combine rubric, LLM judgement, NLP metrics and teacher review.

Exam Mode

A normal web application cannot provide OS-level exam lockdown.

Describe it as restricted browser writing mode, not secure exam browser.

Maintenance

470 students can generate support load.

Route student support through teacher escalation and build admin tools for reset/retry/export.

# 3. Technical Architecture

## 3.1 Architecture Summary

Layer

Technology / Component

Purpose

Frontend

Next.js, TypeScript, Tailwind CSS, ProseMirror or TipTap

Student editor, teacher dashboard, admin console and reports.

Authentication

OpenAuth

Self-hosted authentication provider and OAuth login flow.

Application API

FastAPI, SQLAlchemy, Pydantic

Business APIs, RBAC, school tenant isolation and data access.

Database

PostgreSQL

Persistent data for users, classes, tasks, submissions, rubrics, marking and audit logs.

Cache / Queue

Redis

Grammar suggestion cache, rate limit and background job queue.

Grammar Service

Self-hosted LanguageTool-compatible grammar checking service

Low-cost real-time grammar, spelling and punctuation suggestions.

NLP Metrics

spaCy-based metric extraction

Word count, lexical density, error rate, type-token ratio and cohesion proxies.

LLM Worker

Background worker with JSON schema validation

Full overview, rubric marking, feedback and post-writing exercises.

Storage

S3-compatible object storage or managed storage

PDF exports, report files and upload assets.

## 3.2 Logical Runtime Flow

Students and teachers access the Next.js web application over HTTPS.

OpenAuth handles sign-in, callback and session establishment.

FastAPI validates authenticated user identity, role, school_id and class permissions for every protected request.

Practice Mode checks changed text chunks through a debounced grammar pipeline. It does not call LLM for every keystroke.

Exam Mode saves submissions and queues AI marking after submission.

Background workers perform LLM overview, marking, exercise generation and report generation asynchronously.

PostgreSQL stores final records; Redis stores short-lived cache, rate limit state and job queue state.

# 4. Practice Mode Design

Practice Mode shall deliver a Grammarly-like writing interface. The core implementation is editor-first: inline highlights, suggestion cards, accept/dismiss actions and a right-side suggestion panel. The real-time part shall use changed-range detection, debounce, grammar service and caching. The LLM shall be reserved for full overview, explanation and content/organisation feedback.

Function

Implementation

LLM Usage

Spelling / punctuation

Self-hosted grammar service and cache

No by default

Basic grammar

Grammar service and deterministic post-processing

No by default

Suggestion explanation

Selected suggestion passed to LLM on request

Yes, on demand

Full essay overview

Asynchronous job after Full Check or idle trigger

Yes

Content relevance

LLM overview using task prompt and rubric context

Yes

Organisation feedback

LLM overview plus paragraph metrics

Yes

## 4.1 Grammarly Reference Screenshots

The following client-provided Grammarly screenshots are inserted as UI/UX reference for the Practice Mode interaction structure. The final platform will use original Edcosys branding and independently implemented interaction logic.

Figure 2. Grammarly document list reference screenshot provided by client.

Figure 3. Grammarly editor and suggestion card reference screenshot provided by client.

## 4.2 Proposed Practice Mode Screen

Figure 4. Proposed Practice Mode: browser screenshot from local HTML prototype.

# 5. UI/UX Screen Appendix

This section inserts the required product screens in their corresponding functional areas. These platform screens are prototype browser screenshots, not AI-generated images.

## 5.1 Login Page

OpenAuth-based sign-in page with school name, email, password, forgot password and privacy notice.

Figure 5. Login page: browser screenshot from local HTML prototype.

## 5.2 Platform Homepage

Landing page showing platform positioning, mode entry points and school-level volume summary.

Figure 6. Platform homepage: browser screenshot from local HTML prototype.

## 5.3 Student Page

Student portal home with assigned tasks, Practice Mode / Exam Mode badges and feedback status.

Figure 7. Student home: browser screenshot from local HTML prototype.

## 5.4 Teacher Page

Teacher dashboard showing active tasks, submission progress, pending marking review and class actions.

Figure 8. Teacher dashboard: browser screenshot from local HTML prototype.

## 5.5 Exam Mode Page

Restricted writing interface with timer, disabled AI suggestions, autosave and submission controls.

Figure 9. Exam Mode page: browser screenshot from local HTML prototype.

## 5.6 Overview / Feedback Page

Student feedback overview with rubric scores, strengths, areas for improvement and post-writing exercise links.

Figure 10. Feedback overview: browser screenshot from local HTML prototype.

## 5.7 Back-office Administration Page

Administrative account management page for user import, validation, status and class assignment controls.

Figure 11. Back-office administration page: browser screenshot from local HTML prototype.

## 5.8 Data and Report Page

Teacher/reporting page showing class analytics, score distribution, common weaknesses and export controls.

Figure 12. Data and reports page: browser screenshot from local HTML prototype.

# 6. Detailed Development Flow

Phase

Main Work

Output

0. Foundation

Repository, local Docker setup, base Next.js/FastAPI structure, database migration baseline.

Runnable local development environment.

1. Authentication and RBAC

OpenAuth integration, callback, session cookie, role mapping, school_id isolation and access middleware.

Login and protected API baseline.

2. Core school data

School, user, teacher, student, class, membership, CSV import and account status.

Admin can import users and manage classes.

3. Task and rubric workflow

Writing task builder, rubric builder, class assignment and dashboard visibility.

Teacher can assign writing tasks.

4. Writing editor

Practice editor, Exam editor, autosave, word count, submit and submission lock.

Students can write and submit.

5. Grammar suggestion engine

Changed-range detection, debounce, grammar service integration, cache, inline highlights and suggestion panel.

Practice Mode Grammarly-like interaction.

6. AI marking

NLP metrics, LLM prompt, JSON schema validation, marking job queue, teacher review and override.

Teacher-supervised AI marking.

7. Feedback and exercises

Student feedback page, personalised exercises and completion tracking.

Students can review and practise improvements.

8. Reports and exports

Class analytics, CSV export, PDF export and audit logging.

Teacher can generate reports.

9. Hardening

E2E, UAT, stress testing, monitoring, backup and production deployment.

Production-ready school pilot.

# 7. Development Time Estimate

Basis: one developer, freelance capacity of 24 hours per week. One man-day equals 8 hours. Applying 80% effective delivery capacity gives approximately 2.4 effective man-days per week.

Version

Scope

Estimated Man-days

Calendar at 24h/week and 80% efficiency

Demo

One class, one task, login, basic editor, basic AI marking and teacher review.

35-45

15-19 weeks

Controlled Pilot

Core school workflow, selected classes, Practice Mode, Exam Mode, AI marking and basic reports.

70-90

29-38 weeks

School Rollout

470 students, 11 topics, user import, stable reports, UAT and production deployment.

120-150

50-63 weeks

Advanced Version

Polished Grammarly-like editor, analytics, monitoring, support tooling and hardening.

180-220

75-92 weeks

Recommendation: for quotation and delivery risk control, commit to a controlled pilot first. Do not commit to a full Grammarly-grade production platform under a short 8-12 week delivery window unless the scope is reduced to a narrow demo.

# 8. Testing Standards and Acceptance Criteria

## 8.1 E2E Testing

Teacher login and logout through OpenAuth.

Student login and logout through OpenAuth.

Teacher creates class, rubric and writing task.

Teacher assigns task to class.

Student opens Practice Mode, receives suggestion, accepts suggestion and submits writing.

Student opens Exam Mode, paste is blocked, timer works and submission is locked.

AI marking job is created and completed.

Teacher reviews AI marking, overrides score and releases feedback.

Student views released feedback and opens post-writing exercise.

Teacher generates class report and exports CSV/PDF.

## 8.2 UAT Standard

UAT shall include at least one school administrator, one teacher and five student test accounts.

UAT shall include one Practice Mode task and one Exam Mode task.

UAT shall include account import, task assignment, student submission, teacher review, feedback release and report export.

All critical UAT cases must pass before production release.

No unresolved critical defect shall remain at acceptance.

## 8.3 Stress Testing

Scenario

Load

Pass Standard

Login burst

150 students login within 10 minutes.

No system-caused login failure; dashboard loads successfully.

Practice writing

100 concurrent students writing with autosave and suggestions.

Editor remains usable; autosave continues; grammar service failure does not block typing.

Exam submission burst

470 students submit within 30 minutes.

All submissions are saved; marking jobs are queued; no essay is lost.

AI marking batch

470 essays queued for marking.

Jobs complete or fail safely; failed jobs can be retried.

Report generation

Teacher generates class report after marking.

Report loads; CSV and PDF export work.

## 8.4 Functional Acceptance

Student cannot access another student submission.

Teacher cannot access unassigned class.

Suspended account cannot access the system.

Practice Mode suggestions map to the correct text span.

Editing a sentence invalidates only affected suggestions.

Exam Mode disables real-time suggestions and AI rewrite.

AI marking output follows the required JSON schema.

Teacher can override AI scores and release final feedback.

Class reports show completion, rubric breakdown, common weaknesses and export controls.

Audit log records login, import, submission, AI marking, teacher override, feedback release and export actions.

# 9. Maintenance Boundary

Teacher support shall be handled through platform ticket or agreed support email.

Student support should be routed through teacher escalation, not direct 470-student support by one developer.

Business-hour support only; no 24/7 support commitment.

Extra writing topics, new rubrics, LMS integration, parent portal, plagiarism detection and OS-level secure exam browser are excluded unless separately quoted.

Admin tooling must include user search, bulk password reset, AI marking retry, class reassignment, export history and audit log review.

# 10. Final Technical Recommendation

The system is technically feasible for a one-developer controlled pilot if the scope is fixed and maintenance boundaries are explicit. The correct design is not an LLM-for-everything wrapper. The platform shall use a hybrid pipeline: editor delta detection, debounce, grammar service, cache, asynchronous LLM overview, NLP metrics and teacher-supervised AI marking. The main delivery risk is the maintenance and support workload after student rollout.
