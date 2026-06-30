# Technical Proposal

# English AI Writing Platform 2026–2027

# School-based AI Writing, Grammar Feedback, Assessment and Reporting Platform

Prepared by: Edcosys Version: 1.0 Target School: W F Joseph Lee Primary School Target Levels: P4 to P6 Target Student Volume: Approximately 470 students Annual Writing Topics: 11 topics Authentication: OpenAuth Frontend: Next.js, TypeScript, Tailwind CSS Backend: FastAPI, Python Database: PostgreSQL Cache / Queue: Redis AI Function: Writing feedback, grammar explanation, rubric-based marking, post-writing exercise generation, class analytics

## 1. Technical Positioning

The platform shall be implemented as a standalone web-based English AI Writing Platform for one school tenant.

The platform shall provide two writing modes:

Practice Mode Students write in a Grammarly-like editor. The system provides inline grammar, spelling, punctuation, vocabulary and clarity suggestions while the student writes. Full-text overview feedback may be generated after a short waiting period or when the student requests a full check.

Exam Mode Students write in a restricted writing interface. Real-time suggestions are disabled. The system performs AI marking and feedback generation after submission.

The system shall not rely on large language model calls for every keystroke. Real-time writing feedback shall use a hybrid architecture:

Fast deterministic checks.

Self-hosted grammar-checking service.

Cached paragraph-level analysis.

Delayed LLM analysis for full-text overview, content, organisation and rubric-based feedback.

The system shall preserve teacher control. AI-generated marking shall be reviewable, editable and overridable by teachers.

## 2. Design Principles

### 2.1 Cost Control

The system shall avoid sending the full essay to an LLM on every edit.

The following requests shall not use LLM by default:

Single-word spelling checks.

Basic punctuation checks.

Basic grammar pattern checks.

Repeated checks on unchanged paragraphs.

Autosave.

Word count.

Basic readability metrics.

Basic lexical metrics.

The following requests may use LLM:

Full essay overview.

Content relevance feedback.

Organisation feedback.

Rubric-based marking.

Personalised post-writing exercises.

Explanation of selected grammar suggestions.

Teacher-facing class weakness summary.

### 2.2 Latency Control

Real-time suggestions shall be generated through a staged pipeline.

Target behaviour:

Immediate local UI update: less than 100 ms.

Autosave request: background operation, no typing block.

Rule-based grammar check: returned within short interactive delay.

LLM overview: asynchronous, displayed when ready.

AI marking: asynchronous after submission.

### 2.3 Teacher Control

AI shall not be the final authority for assessment.

The system shall support:

AI-generated score.

AI-generated explanation.

Teacher score override.

Teacher feedback edit.

Teacher final release to student.

Audit log of teacher override.

### 2.4 Maintainability

The system shall be simple enough for one developer to maintain.

The architecture shall avoid unnecessary microservices. Separate services shall only be used when there is a clear technical need:

OpenAuth as authentication service.

Application backend as main API service.

Worker service for AI marking and report generation.

Grammar service for self-hosted grammar checking.

PostgreSQL for persistent data.

Redis for cache, rate limit and job queue.

## 3. Overall System Architecture

### 3.1 Logical Architecture

[Student / Teacher Browser] | | HTTPS v [Next.js Web Application] | | OAuth Redirect / Token Verification v [OpenAuth Service] | | Authenticated Session v [FastAPI Application API] | | SQL v [PostgreSQL Database] [FastAPI Application API] | | Cache / Rate Limit / Queue v [Redis] [FastAPI Application API] | | Grammar Check Request v [Self-hosted Grammar Service] [Worker Service] | | LLM Request v [LLM Provider API] [Worker Service] | | File / Export Output v [Object Storage]

### 3.2 Runtime Components

The production runtime shall include:

Next.js frontend.

FastAPI backend.

OpenAuth authentication server.

PostgreSQL database.

Redis cache and job queue.

Grammar checking service.

Background worker.

Object storage for exports and uploaded assets.

Logging and monitoring service.

### 3.3 Request Types

The platform shall distinguish between four request types:

Interactive requests Used for dashboard, task loading, editor loading, autosave and suggestion retrieval.

Asynchronous AI requests Used for full essay overview, AI marking, exercise generation and report generation.

Administrative requests Used for CSV import, account management, rubric management and export.

Support requests Used for teacher support tickets and student issue escalation.

## 4. Technology Stack

### 4.1 Frontend

Technology:

Next.js.

TypeScript.

Tailwind CSS.

ProseMirror or TipTap for the writing editor.

React Query or equivalent data-fetching layer.

Zod for frontend schema validation.

Playwright for E2E testing.

Reason:

Next.js and TypeScript match the existing development baseline.

ProseMirror / TipTap is suitable for inline highlights, text position mapping, suggestions and editor state management.

Tailwind CSS allows fast UI implementation with consistent design.

Playwright supports browser-based E2E testing of teacher and student flows.

### 4.2 Backend

Technology:

FastAPI.

Python.

SQLAlchemy.

Alembic.

Pydantic.

PostgreSQL.

Redis.

Celery, RQ or Dramatiq for background jobs.

Reason:

FastAPI matches the existing AI4School backend baseline.

Python is suitable for NLP, grammar, AI pipeline and data analysis.

PostgreSQL is suitable for production data.

Redis supports cache, rate limit and asynchronous processing.

Background jobs prevent AI marking from blocking student submission.

### 4.3 Authentication

Technology:

OpenAuth.

OAuth code flow.

HTTP-only secure cookies.

Application-level RBAC in FastAPI.

Design:

OpenAuth handles login, password flow, token issuance and authentication callback.

Application database remains the source of truth for school, role, class and account status.

FastAPI verifies the authenticated user session before processing protected API requests.

Every query must filter by school_id.

Student requests must filter by student_id.

Teacher requests must filter by assigned_class_id.

### 4.4 Grammar and NLP

Technology:

Self-hosted LanguageTool for grammar, spelling and punctuation.

spaCy for tokenisation, POS tagging, dependency parsing and noun phrase extraction.

TextDescriptives or custom Python metrics for readability and linguistic statistics.

Custom metric layer for lexical density, sentence length, grammar error rate and cohesion proxies.

Design:

LanguageTool handles low-cost, high-frequency grammar suggestions.

spaCy handles linguistic features required by scoring and analytics.

Text metrics are stored with marking results.

LLM receives both the student essay and computed metrics during marking.

### 4.5 LLM Layer

Technology:

LLM provider API.

Prompt templates stored with version number.

JSON schema validation for all LLM outputs.

Retry and fallback logic.

Cost logging per request.

Design:

LLM calls must be asynchronous for marking and full overview.

LLM outputs must be validated before saving.

Invalid outputs must be retried.

If retry fails, the marking status shall be set to AI_MARKING_FAILED.

Teacher can manually mark failed submissions.

## 5. Practice Mode Technical Design

### 5.1 Core User Experience

Practice Mode shall provide a Grammarly-like writing experience.

The student sees:

Writing task title.

Writing instruction.

Rich text or plain text editor.

Word count.

Autosave status.

Inline highlights.

Suggestion side panel.

Full essay overview panel.

Submit button.

### 5.2 Editor Selection

The editor shall be implemented with ProseMirror or TipTap.

Required editor capabilities:

Text position mapping.

Inline decorations.

Suggestion highlights.

Accept suggestion.

Dismiss suggestion.

Undo / redo.

Paste handling.

Read-only mode after submission.

Autosave integration.

Change detection at paragraph or sentence level.

### 5.3 Real-time Suggestion Pipeline

The pipeline shall not call LLM on every keystroke.

Flow:

Student types text -> Editor transaction generated -> Changed range detected -> Debounce timer starts -> Extract changed sentence / paragraph -> Hash text chunk -> Check Redis cache -> If cached, return cached suggestions -> If not cached, call grammar service -> Normalise suggestion result -> Store result in Redis -> Return suggestion list -> Frontend maps suggestions to editor decorations

### 5.4 Debounce Rules

The system shall use debounce to prevent excessive requests.

Recommended rules:

Do not check while the student is continuously typing.

Trigger grammar check after 800 ms to 1,500 ms of typing inactivity.

Trigger paragraph check when the student finishes a sentence.

Trigger full overview only after explicit user action or after longer idle time.

Do not send identical paragraph text twice.

Do not check text shorter than a minimum threshold unless punctuation or spelling check is required.

### 5.5 Cache Strategy

Cache key:

grammar:{language}:{normalized_text_hash}:{rule_config_version}

Cache value:

Suggestion category.

Original text.

Suggested text.

Offset within checked chunk.

Length.

Explanation.

Severity.

Rule ID.

Timestamp.

Cache TTL:

Short text grammar cache: 24 hours.

Paragraph grammar cache: 24 hours.

Full essay overview cache: task-specific and submission-specific.

### 5.6 Suggestion Types

Real-time suggestions:

Spelling.

Punctuation.

Capitalisation.

Basic grammar.

Repeated words.

Article usage.

Subject-verb agreement.

Sentence clarity.

Delayed suggestions:

Content development.

Organisation.

Coherence.

Task relevance.

Tone.

Vocabulary enhancement.

Full essay overview.

### 5.7 LLM Usage in Practice Mode

LLM shall only be used for:

Full essay overview.

Explain selected suggestion.

Rewrite selected sentence when student explicitly requests.

Content and organisation feedback.

Pre-submission improvement advice.

LLM shall not be used for:

Every keystroke.

Every word change.

Every autosave.

Every spelling check.

Every punctuation check.

### 5.8 Handling Modified Sentences

When the student modifies the first sentence of a 300-word essay:

The editor detects the changed range.

The frontend identifies the affected sentence and paragraph.

Existing suggestions overlapping the changed range are invalidated.

Suggestions outside the changed range remain visible.

The changed paragraph is sent for grammar check after debounce.

Full essay overview is marked stale.

Full essay overview is refreshed only after explicit request or idle trigger.

This avoids rechecking the entire 300-word essay on every small edit.

## 6. Exam Mode Technical Design

### 6.1 Core User Experience

Exam Mode shall provide a restricted writing environment.

The student sees:

Task title.

Writing prompt.

Timer.

Word count.

Plain writing editor.

Submit button.

Exam mode notice.

Real-time AI suggestions shall be disabled.

### 6.2 Exam Mode Controls

The system shall implement browser-level controls:

Disable real-time suggestion panel.

Disable AI rewrite.

Disable grammar feedback.

Disable paste into editor.

Log paste attempt.

Log window blur.

Log window focus.

Log fullscreen exit when fullscreen is enabled.

Autosave writing periodically.

Auto-submit when timer expires.

### 6.3 Exam Mode Limitation

The platform is a web application. It shall not claim OS-level secure examination browser capability.

The following cannot be guaranteed by a normal browser web application:

Preventing student from using another device.

Preventing screenshot.

Preventing all browser-level manipulation.

Preventing external AI usage outside the platform.

Locking down the operating system.

The system shall present Exam Mode as a controlled writing mode, not a secure exam browser.

## 7. AI Marking Technical Design

### 7.1 Marking Philosophy

The marking engine shall use a hybrid scoring design.

The system shall not rely on a single LLM prompt as the only scoring mechanism.

The marking engine shall combine:

School rubric.

Student essay.

Task instruction.

NLP metrics.

Grammar-checking result.

LLM judgement.

Teacher review.

### 7.2 Marking Pipeline

Student submits essay -> Submission saved -> Marking job created -> Worker fetches task, rubric and essay -> Grammar service checks essay -> NLP service computes metrics -> LLM receives essay + rubric + metrics -> LLM returns structured JSON -> Backend validates JSON schema -> Score normalisation applied -> MarkingResult saved -> Teacher review status set to PENDING_REVIEW

### 7.3 NLP Metrics

The system shall compute the following metrics:

Word count.

Sentence count.

Average sentence length.

Paragraph count.

Grammar error count.

Grammar error rate per 100 words.

Spelling error count.

Punctuation error count.

Lexical density.

Type-token ratio.

Content-word ratio.

Connective count.

Transition phrase count.

Repeated word count.

Noun phrase count.

Verb usage distribution.

Readability indicator.

Dependency distance indicator.

### 7.4 Rubric Dimensions

Version 1.0 shall support the following rubric dimensions:

Content.

Language.

Organisation.

Optional dimension:

Task Achievement.

### 7.5 LLM Marking Input

The LLM marking input shall include:

Student level.

Writing task instruction.

Expected writing genre.

Word limit.

Rubric dimensions.

Rubric descriptors.

Student essay.

Grammar error summary.

NLP metrics.

Required JSON output schema.

The LLM marking input shall not include:

Student name.

Student email.

HKID.

Parent information.

Unnecessary class personal data.

### 7.6 LLM Marking Output

The LLM shall return JSON with the following fields:

content_score.

language_score.

organisation_score.

total_score.

confidence_level.

content_feedback.

language_feedback.

organisation_feedback.

strengths.

weaknesses.

sentence_level_comments.

recommended_exercises.

warning_flags.

### 7.7 Consistency Controls

The following controls shall be implemented:

Fixed model version during each school term.

Fixed prompt version during each marking batch.

Temperature set to 0 or lowest available deterministic setting.

JSON schema validation.

Score range validation.

Rubric descriptor included in prompt.

NLP metrics included as evidence.

Teacher override captured for future calibration.

Outlier detection for abnormal score distribution.

Re-marking function limited to authorised teacher or system administrator.

### 7.8 Confidence and Escalation

The system shall mark a submission as requiring teacher attention when:

LLM output is invalid after retry.

Essay is too short.

Essay is off-topic.

Grammar error rate is unusually high.

LLM confidence is low.

Total score differs significantly from metric-based expectation.

Student writing contains sensitive content.

AI provider request fails.

## 8. Data Architecture

### 8.1 Core Tables

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

### 8.2 Key Data Rules

Every school-owned table shall include school_id.

Every student submission shall include student_id.

Every writing task shall include created_by.

Every teacher review shall include reviewed_by.

Every AI result shall include model name, model version, prompt version and timestamp.

Every export shall be logged.

Every teacher override shall be logged.

## 9. API Architecture

### 9.1 API Groups

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

### 9.2 Suggestion API

Endpoint:

POST /api/suggestions/check

Input:

task_id.

draft_id.

text_chunk.

chunk_start_offset.

language.

mode.

client_revision_id.

Output:

suggestions.

checked_text_hash.

stale_overview.

request_id.

### 9.3 Full Overview API

Endpoint:

POST /api/suggestions/overview

Input:

task_id.

draft_id.

full_text.

client_revision_id.

Output:

job_id.

status.

### 9.4 Marking API

Endpoint:

POST /api/submissions/{submission_id}/mark

Behaviour:

Create marking job.

Return job ID.

Worker processes marking asynchronously.

Teacher views result after completion.

### 9.5 Report API

Endpoint:

POST /api/reports/class

Input:

class_id.

task_id.

report_type.

Output:

report_id.

status.

export_url when ready.

## 10. High Concurrency and High Availability Design

### 10.1 Expected School Usage Pattern

The school has approximately 470 students.

Expected peak scenarios:

Whole level login during class.

Multiple classes writing at the same time.

Many autosave requests during writing.

Many grammar suggestion requests during Practice Mode.

Many submissions at the end of Exam Mode.

Batch AI marking after submission deadline.

### 10.2 Concurrency Strategy

The system shall handle concurrency through:

Stateless backend API.

Managed PostgreSQL.

Redis cache.

Queue-based AI processing.

Debounced grammar checks.

Paragraph-level grammar check instead of full-essay real-time check.

Rate limit per user.

Rate limit per class.

Async workers for AI marking.

Autosave batching.

### 10.3 Avoiding LLM Bottleneck

The platform shall not put LLM calls in the synchronous request path for normal typing.

Synchronous path:

Load task.

Save draft.

Check grammar chunk.

Submit essay.

Load result.

Asynchronous path:

Full essay overview.

AI marking.

Post-writing exercise generation.

Class report generation.

PDF export.

### 10.4 Rate Limiting

Recommended limits:

Autosave: one request every 5 to 10 seconds per active draft.

Grammar check: one active request per student at a time.

Full overview: limited per student per task.

AI marking: queued by submission.

Report generation: limited per teacher.

### 10.5 Failure Handling

If grammar service fails:

Editor remains usable.

Autosave continues.

Suggestion panel displays temporary unavailable message.

Error is logged.

Retry is attempted.

If LLM provider fails:

Submission remains saved.

Marking status becomes PENDING_RETRY or AI_MARKING_FAILED.

Teacher can retry marking.

Teacher can manually mark.

If Redis fails:

Critical user flows continue without cache where possible.

AI jobs may be paused until queue is restored.

Error is logged.

If PostgreSQL fails:

Application enters degraded state.

New writes are blocked.

System displays service unavailable message.

Administrator is alerted.

### 10.6 Backup and Recovery

Required backup controls:

Daily PostgreSQL backup.

Manual backup before production data migration.

Export function for school data.

Environment variable backup excluded from repository.

Restore procedure documented.

Production secrets rotated if exposed.

## 11. Deployment Design

### 11.1 Recommended Deployment for One-person Maintenance

Recommended simple deployment:

Frontend on Vercel or similar managed frontend hosting.

Backend on Render, Fly.io, Railway, AWS ECS or equivalent container hosting.

PostgreSQL on managed database service.

Redis on managed Redis service.

OpenAuth as separate Node service.

Grammar service as containerised service.

Worker service as containerised background worker.

Object storage on S3-compatible service.

### 11.2 Environment Separation

Required environments:

Local development.

UAT environment.

Production environment.

Each environment shall have:

Separate database.

Separate Redis.

Separate environment variables.

Separate OpenAuth client configuration.

Separate AI provider key or usage limit.

### 11.3 CI/CD

Minimum CI/CD requirements:

TypeScript build check.

Python unit test.

Database migration check.

Lint check.

E2E test on UAT branch before release.

Manual production deployment approval.

## 12. Development Flow for One Developer

This project does not require a separate project manager. Development shall follow a technical implementation sequence.

### Phase 0: Technical Foundation

Deliverables:

Repository setup.

Frontend skeleton.

Backend skeleton.

Database schema baseline.

Environment configuration.

Docker compose for local development.

### Phase 1: Authentication and Core Data

Deliverables:

OpenAuth setup.

Login callback.

Session handling.

Role mapping.

User table.

School table.

Class table.

CSV import for users.

RBAC middleware.

### Phase 2: Teacher and Student Core Flow

Deliverables:

Teacher dashboard.

Student dashboard.

Class management.

Writing task management.

Rubric management.

Task assignment.

### Phase 3: Writing Editor

Deliverables:

Practice Mode editor.

Exam Mode editor.

Autosave.

Word count.

Submit flow.

Submission locking.

Exam event logging.

### Phase 4: Real-time Suggestion Engine

Deliverables:

Grammar service integration.

Debounced suggestion API.

Redis caching.

Inline highlights.

Suggestion side panel.

Accept suggestion.

Dismiss suggestion.

Full overview stale indicator.

### Phase 5: AI Marking Engine

Deliverables:

Marking worker.

Grammar result aggregation.

NLP metric extraction.

LLM marking prompt.

JSON schema validation.

Marking result storage.

Teacher review page.

Teacher override.

### Phase 6: Exercises and Reports

Deliverables:

Post-writing exercise generation.

Student exercise page.

Class report page.

Score distribution.

Common weakness analysis.

CSV export.

PDF export.

### Phase 7: Hardening and Release

Deliverables:

E2E test suite.

UAT test script.

Stress test script.

Bug fixing.

Production deployment.

Backup setup.

User guide.

Acceptance checklist.

## 13. Development Effort Estimate

### 13.1 Estimation Basis

One man-day equals 8 working hours.

The estimate assumes:

One developer.

Existing AI4School experience can be reused.

Existing code may inspire structure but this platform is a standalone product.

Effective execution speed is calculated at 80%.

Weekly available time is 24 hours.

Effective weekly delivery capacity is approximately 2.4 man-days.

Formula:

24 hours per week / 8 hours per man-day * 80% = 2.4 effective man-days per week

### 13.2 MVP Scope

MVP means the school can run a controlled pilot with selected classes.

MVP includes:

OpenAuth login.

Student and teacher accounts.

Class management.

Writing task creation.

Rubric creation.

Practice Mode editor.

Basic inline grammar suggestions.

Exam Mode editor.

Submission.

AI marking.

Teacher review.

Student feedback view.

Basic class report.

CSV export.

UAT environment.

MVP excludes:

Full PDF export polish.

Advanced analytics.

Advanced support ticket workflow.

Multi-school deployment.

Full high-availability setup.

Advanced AI calibration dashboard.

Estimated MVP effort:

Area

Man-days

Architecture setup and repo foundation

3

OpenAuth integration and session handling

5

Database schema and RBAC

6

User import and class management

6

Teacher task and rubric workflow

8

Student dashboard and submission flow

5

Practice Mode editor basic version

10

Real-time grammar suggestion basic version

10

Exam Mode basic version

6

AI marking basic pipeline

10

Teacher review and feedback release

6

Basic class report and CSV export

5

UAT deployment and bug fixing

8

MVP E2E tests

5

MVP stress test setup

3

Total

96 man-days

MVP calendar time at 2.4 effective man-days per week:

96 / 2.4 = 40 weeks

This is the safe one-person freelance estimate.

If the developer works at full 24 hours weekly without applying the 80% effectiveness reduction, the MVP calendar time is:

96 / 3 = 32 weeks

### 13.3 Reduced MVP for Quotation Demo

A reduced version can be built faster if the goal is quotation demonstration rather than full school rollout.

Reduced MVP includes:

Login.

Teacher dashboard.

Student dashboard.

One class.

One writing task.

One rubric.

Practice Mode editor.

Basic grammar suggestion side panel.

Exam Mode submission.

AI marking.

Basic teacher review.

Reduced MVP excludes:

CSV import.

Full support workflow.

PDF export.

Advanced class report.

Stress hardening.

Full audit log.

Production-grade backup.

Estimated reduced MVP effort:

Area

Man-days

Foundation

3

Auth

4

Core schema

4

Basic teacher/student dashboard

5

Task/rubric basic flow

6

Practice editor

8

Grammar suggestion basic flow

8

Exam mode basic flow

4

AI marking basic flow

6

Teacher review

4

Demo deployment and bug fixing

6

Total

58 man-days

Calendar time at 2.4 effective man-days per week:

58 / 2.4 = 24 weeks

Calendar time at raw 3 man-days per week:

58 / 3 = 19 weeks

### 13.4 Production Version

Production version includes:

Full account import.

Full class assignment.

Stable Practice Mode.

Stable Exam Mode.

Full AI marking pipeline.

Full teacher override workflow.

Post-writing exercises.

Class analytics.

CSV and PDF export.

Audit log.

Support ticket flow.

Backup.

Monitoring.

Stress testing.

UAT sign-off.

Estimated production effort:

Area

Man-days

Foundation and environment

5

OpenAuth production integration

7

RBAC and tenant isolation

8

User import and account admin

8

Class management

5

Task management

8

Rubric management

8

Practice Mode editor

14

Real-time suggestion engine

16

Full overview feedback

6

Exam Mode

8

AI marking pipeline

14

NLP metrics layer

8

Teacher review and override

8

Student feedback view

5

Post-writing exercises

7

Class report and analytics

10

CSV and PDF export

6

Audit log

5

Support ticket workflow

5

Deployment and backup

7

Monitoring and logging

5

E2E test suite

10

UAT support and bug fixing

12

Stress testing and tuning

6

Documentation

5

Total

211 man-days

Calendar time at 2.4 effective man-days per week:

211 / 2.4 = 88 weeks

Calendar time at raw 3 man-days per week:

211 / 3 = 70 weeks

### 13.5 Practical Delivery Recommendation

For this school quotation, do not commit to full production Grammarly-level implementation as a one-person freelance project.

Recommended commitment:

Phase 1: Controlled pilot.

Phase 2: School rollout.

Phase 3: Hardening and analytics.

Recommended quotation delivery scope:

Version

Scope

Man-days

Calendar at 2.4 MD/week

Demo

One class, one task, basic AI marking

35–45

15–19 weeks

Controlled Pilot

Core school workflow, limited classes

70–90

29–38 weeks

School Rollout

470 students, 11 topics, reports, UAT

120–150

50–63 weeks

Production-grade Advanced Version

Grammarly-like polish, analytics, monitoring

180–220

75–92 weeks

If delivery must happen within 8 to 12 calendar weeks, the scope must be reduced to a demo or narrow pilot.

## 14. Acceptance Standards

### 14.1 Functional Acceptance

The system shall be accepted only when the following functions pass testing:

Teacher login.

Student login.

CSV user import.

Class creation.

Student-class assignment.

Teacher-class assignment.

Writing task creation.

Rubric creation.

Task assignment.

Practice Mode writing.

Inline suggestion display.

Accept suggestion.

Dismiss suggestion.

Autosave.

Exam Mode writing.

Paste blocking in Exam Mode.

Submission locking.

AI marking.

Teacher score override.

Feedback release.

Student feedback view.

Post-writing exercise generation.

Class report generation.

CSV export.

PDF export.

Audit log.

Support ticket.

### 14.2 Data Protection Acceptance

The system shall pass the following data protection checks:

Student cannot access another student’s writing.

Teacher cannot access unassigned class.

School data is filtered by school_id.

Student name is not sent to LLM provider.

Student email is not sent to LLM provider.

AI request uses submission ID instead of personal identity.

Teacher override is logged.

Export action is logged.

Suspended account cannot access the system.

Archived account cannot login.

### 14.3 AI Marking Acceptance

AI marking shall be accepted when:

Output follows the required JSON schema.

Scores are within rubric score ranges.

Total score equals dimension score calculation.

Feedback covers content, language and organisation.

Teacher can override every score.

Failed AI marking can be retried.

Failed AI marking does not delete submission.

Model version and prompt version are recorded.

### 14.4 Practice Mode Acceptance

Practice Mode shall be accepted when:

Student can type continuously without editor freezing.

Autosave does not block typing.

Suggestions appear after typing pause.

Suggestions are attached to the correct text span.

Accept suggestion updates the text.

Dismiss suggestion removes the suggestion.

Editing a sentence invalidates only affected suggestions.

Full essay overview can be regenerated.

Submitted essay becomes locked.

### 14.5 Exam Mode Acceptance

Exam Mode shall be accepted when:

Real-time suggestions are disabled.

AI rewrite is disabled.

Paste is blocked.

Paste attempt is logged.

Window blur is logged.

Timer works.

Auto-submit works when timer expires.

Manual submit works.

Submission is locked after submit.

AI marking starts after submission.

## 15. Testing Standards

### 15.1 Unit Testing

Unit tests shall cover:

User role validation.

School tenant filtering.

CSV import validation.

Rubric score calculation.

Word count.

Lexical density calculation.

Grammar result normalisation.

AI output schema validation.

Error code handling.

Permission checks.

Minimum target:

Critical backend business logic covered.

Critical scoring calculation covered.

Critical authorisation checks covered.

### 15.2 Integration Testing

Integration tests shall cover:

OpenAuth callback to application session.

Teacher creates task.

Student receives assigned task.

Student submits writing.

Worker processes marking.

Teacher reviews result.

Student views feedback.

Report generation.

Export generation.

Support ticket submission.

### 15.3 E2E Testing

E2E tests shall use Playwright.

Required E2E scenarios:

Teacher login and logout.

Student login and logout.

Teacher creates class.

Teacher imports students.

Teacher creates writing task.

Teacher creates rubric.

Teacher assigns task to class.

Student opens Practice Mode.

Student receives grammar suggestion.

Student accepts suggestion.

Student submits Practice Mode writing.

Student opens Exam Mode.

Student attempts paste.

Student submits Exam Mode writing.

Teacher reviews AI marking.

Teacher overrides score.

Teacher releases feedback.

Student views feedback.

Teacher generates class report.

Teacher exports CSV.

### 15.4 UAT Testing

UAT shall be performed with school users.

UAT users:

At least one teacher.

At least one school administrator.

At least five student test accounts.

UAT test data:

One P4 class.

One P5 class.

One P6 class.

One Practice Mode task.

One Exam Mode task.

One school rubric.

Sample student essays.

UAT pass criteria:

All critical UAT cases pass.

No critical defect remains unresolved.

Teacher can complete task assignment without developer assistance.

Student can submit writing without developer assistance.

Teacher can review and release feedback.

School confirms report format is acceptable.

### 15.5 Stress Testing

Stress testing shall focus on school classroom usage.

Recommended stress scenarios:

Scenario ST-001: Login Burst

150 students login within 10 minutes.

Target: no failed login caused by system error.

Target: dashboard loads successfully.

Scenario ST-002: Practice Writing

100 concurrent students write in Practice Mode.

Autosave runs in background.

Grammar suggestions are requested with debounce.

Target: editor remains usable.

Target: autosave success rate remains acceptable.

Target: grammar service does not block submission.

Scenario ST-003: Exam Submission Burst

470 students submit within 30 minutes.

Target: all submissions are saved.

Target: no submitted essay is lost.

Target: marking jobs are queued.

Scenario ST-004: AI Marking Batch

470 essays enter marking queue.

Target: all jobs complete or fail safely.

Target: failed jobs can be retried.

Target: teacher can see marking status.

Scenario ST-005: Report Generation

Teacher generates class report after marking.

Target: report loads successfully.

Target: CSV export works.

Target: PDF export works.

### 15.6 Security Testing

Security tests shall cover:

Student accesses another student submission.

Teacher accesses unassigned class.

Suspended user login.

Archived user login.

Missing school_id filtering.

Invalid token.

Expired session.

CSV injection attempt.

HTML/script injection in writing content.

Prompt injection in student essay.

File upload type validation.

Export access control.

## 16. Maintenance Design

### 16.1 One-person Maintenance Reality

The most difficult part of this project is not initial development. The most difficult part is maintenance.

Likely maintenance issues:

Student login problems.

Forgotten password.

Wrong class assignment.

Teacher cannot find task.

Student cannot submit.

AI marking failure.

Grammar suggestion mismatch.

Report export failure.

School requests rubric changes.

School requests extra writing topics.

### 16.2 Maintenance Controls

The system shall include:

Admin dashboard.

User search.

Bulk password reset.

Reassign student class.

Reopen submission.

Retry AI marking.

View marking job status.

View AI usage.

View support tickets.

Export logs.

### 16.3 Support Boundary

The supplier shall define support boundary in quotation.

Recommended support boundary:

Teacher support by email or ticket.

Student support through teacher escalation.

Business-hour support only.

No 24/7 support.

Extra writing topics charged separately.

Extra rubric redesign charged separately.

LMS integration excluded.

Parent support excluded.

## 17. Recommended Scope for Quotation

The quotation should not sell the product as “a complete Grammarly replacement”.

The quotation should describe the platform as:

“An English AI Writing Platform with Grammarly-like practice writing interface, controlled exam writing mode, AI-assisted rubric marking, teacher review workflow, individualised feedback, post-writing exercises and class-level reporting.”

Recommended included items:

One school tenant.

Approximately 470 students.

Teacher accounts.

P4 to P6 class setup.

11 annual writing topics.

Practice Mode.

Exam Mode.

AI-assisted marking.

School-based rubric.

Individual feedback.

Post-writing exercises.

Class report.

CSV export.

UAT.

Production deployment.

Recommended excluded items:

Full Grammarly-level proprietary grammar engine.

Browser extension.

Microsoft Word add-in.

Google Docs add-on.

LMS integration.

Parent portal.

Plagiarism detection.

Handwriting OCR.

OS-level exam lockdown.

Unlimited AI usage.

Unlimited support.

24/7 maintenance.

## 18. Final Technical Recommendation

The project is technically feasible for one developer only if the delivery scope is controlled.

The correct architecture is not “LLM for everything”.

The correct architecture is:

Editor-first frontend.

Debounced paragraph-level grammar checking.

Self-hosted grammar engine for real-time suggestions.

LLM for overview, marking and personalised exercises.

NLP metrics for scoring evidence.

Queue-based marking pipeline.

Teacher-in-the-loop review.

Simple managed deployment.

Strong data isolation.

Clear maintenance boundary.

For quotation purposes, the safest delivery commitment is a controlled school pilot, not a full Grammarly-grade production platform.
