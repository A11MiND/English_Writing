# Product Requirements Document

# English AI Writing Platform 2026–2027

# Product Requirements Specification for School-based AI Writing, Assessment and Reporting Platform

Document Status: Draft for Internal Review Prepared for: Internal Project Assessment / School Quotation Preparation Prepared by: Edcosys Version: 1.0 Date: 27 June 2026 Target School: W F Joseph Lee Primary School School Ref. No.: Q17/2526 Project Name: English AI Writing Platform 2026–2027 Target Levels: Primary 4 to Primary 6 Target Student Volume: Approximately 470 students Annual Writing Topics: P4: 4 topics; P5: 4 topics; P6: 3 topics Authentication System: OpenAuth Frontend Technology: Next.js, TypeScript, Tailwind CSS Backend Technology: FastAPI, SQLAlchemy Database Target: PostgreSQL for production deployment AI Function Type: AI-assisted writing feedback, rubric-based marking, post-writing exercise generation, class-level learning analytics

## 1. Document Control

### 1.1 Purpose of Document

This Product Requirements Document defines the business requirements, user requirements, functional requirements, non-functional requirements, data requirements, security requirements, acceptance criteria, deliverables and implementation boundaries for the English AI Writing Platform 2026–2027.

The document is written for project planning, quotation preparation, technical design, implementation tracking, user acceptance testing and post-delivery support.

### 1.2 Document Scope

This document covers the following modules:

OpenAuth-based authentication and access control.

Student account management.

Teacher account management.

School-based writing task creation.

Practice Mode with AI writing suggestions.

Exam Mode with restricted writing environment and post-submission marking.

AI auto-marking of writings.

Tailored school-based rubrics.

Individualised feedback on content, language and organisation.

Individualised post-writing exercises.

Class-based reports with analysis of strengths and weaknesses.

Technical support workflow for teachers.

Technical support workflow for students.

Data protection, audit logging and operational controls.

UAT and acceptance criteria.

### 1.3 Out of Scope for Version 1.0

The following items are not included in Version 1.0:

Microsoft Word add-in.

Google Docs add-on.

Parent portal.

Plagiarism detection engine.

Handwriting OCR.

Real-time multi-user collaborative editing.

OS-level secure examination browser.

Integration with eClass, Google Classroom, Microsoft Teams, Moodle or other LMS.

Integration with school Student Information System.

Public API for third-party developers.

Multi-school commercial billing system.

AI model training using student submissions.

### 1.4 Reference Implementation Baseline

The project shall reuse applicable design patterns from the existing AI4School architecture:

Teacher portal.

Student portal.

Class management.

Assignment workflow.

Paper creation workflow.

Student submission workflow.

AI grading workflow with HMIT.

AI generation workflow.

Role-based access control concept.

API-driven frontend-backend separation.

The new platform shall be implemented as a standalone writing product instead of a direct extension of the existing AI4School user interface.

## 2. Project Background

The school requires an English AI Writing Platform for Primary 4 to Primary 6 students. The platform shall support school-based writing tasks, student accounts, teacher accounts, entry/token management, instant auto-marking, school-based rubrics, individualised feedback, post-writing exercises, class-level reports and technical support for teachers and students.

The required student volume is approximately 470 students from Primary 4 to Primary 6. The required annual writing task volume is 11 topics: 4 topics for P4, 4 topics for P5 and 3 topics for P6.

The platform shall support two writing modes:

Practice Mode: students write with AI-assisted feedback during writing.

Exam Mode: students write without real-time AI feedback; AI marking and feedback are generated after submission.

## 3. Product Vision

The product shall provide a school-based English writing platform that allows teachers to assign writing tasks, students to complete writing tasks online, AI to provide structured feedback and teachers to review student performance at individual and class levels.

The platform shall improve writing learning efficiency by providing immediate formative feedback, reducing repetitive marking workload and generating structured learning analytics for teachers.

The platform shall preserve teacher control over assessment. AI-generated scores and feedback shall be treated as assistant output. Teachers shall be able to review, adjust and override AI-generated marking results.

## 4. Business Objectives

### BO-001: Reduce Teacher Marking Workload

The system shall generate first-pass marking results for student writings based on school-defined rubrics.

Acceptance Criteria:

Teacher can view AI-generated marks.

Teacher can view AI-generated feedback.

Teacher can manually adjust marks.

Teacher can save final marks.

Teacher can export class marking results.

### BO-002: Provide Immediate Learning Feedback to Students

The system shall provide students with structured feedback on grammar, vocabulary, content, organisation and task achievement.

Acceptance Criteria:

Student can receive feedback after submission in Exam Mode.

Student can receive writing suggestions during Practice Mode.

Feedback is grouped by category.

Feedback includes actionable improvement guidance.

### BO-003: Support School-based Writing Curriculum

The system shall allow teachers to create writing tasks based on school-selected topics and rubrics.

Acceptance Criteria:

Teacher can create a writing topic.

Teacher can assign the topic to a class.

Teacher can configure writing instructions.

Teacher can select or create a rubric.

Teacher can set due date and writing mode.

### BO-004: Provide Class-level Learning Analytics

The system shall generate reports showing class strengths and weaknesses.

Acceptance Criteria:

Teacher can view class average performance.

Teacher can view rubric-dimension breakdown.

Teacher can identify common writing issues.

Teacher can export report data.

### BO-005: Provide Controlled School Deployment

The system shall support one-school deployment for W F Joseph Lee Primary School with student and teacher account control.

Acceptance Criteria:

All accounts belong to the school tenant.

Only authorised users can access school data.

Role-based access is enforced.

User activity is auditable.

## 5. User Roles

### 5.1 System Administrator

The System Administrator is responsible for platform configuration, school setup, deployment operation, data export support and incident handling.

Permissions:

Create school tenant.

Configure school-level settings.

Import teacher accounts.

Import student accounts.

Reset user access.

View system audit logs.

Configure AI usage limits.

Configure support tickets.

Export system-level operational logs.

Disable accounts.

Restrictions:

System Administrator shall not edit student writing content.

System Administrator shall not alter teacher final marks.

System Administrator shall not access student submissions unless required for support and recorded in audit logs.

### 5.2 School Administrator

The School Administrator is a school-side administrative user.

Permissions:

Manage teacher accounts within the school.

Manage student accounts within the school.

Manage class lists.

Assign students to classes.

View school-level usage reports.

Request data export.

Request account suspension.

Restrictions:

School Administrator shall not change AI model prompts.

School Administrator shall not modify system security settings.

School Administrator shall not access other school tenant data.

### 5.3 Teacher

The Teacher is responsible for creating writing tasks, assigning tasks, reviewing submissions, adjusting scores and viewing reports.

Permissions:

Create writing task.

Edit writing task before publication.

Publish writing task.

Assign writing task to class.

Create school-based rubric.

Use existing rubric.

View assigned class submissions.

View AI marking results.

Adjust AI-generated marks.

Add teacher feedback.

Release final feedback to students.

Generate class reports.

Export class reports.

Raise support ticket.

Restrictions:

Teacher shall only access classes assigned to the teacher.

Teacher shall not access system-level settings.

Teacher shall not access other teachers’ private draft tasks unless explicitly shared.

### 5.4 Student

The Student is responsible for completing assigned writing tasks and reviewing feedback.

Permissions:

View assigned writing tasks.

Start Practice Mode task.

Start Exam Mode task.

Save draft in Practice Mode.

Submit writing.

View released feedback.

Complete post-writing exercises.

View own progress.

Raise support request through student support channel.

Restrictions:

Student shall not view other students’ submissions.

Student shall not edit submission after final submission unless teacher reopens the task.

Student shall not access AI marking prompt.

Student shall not access class-level reports.

## 6. Product Modules

### 6.1 Module M-001: OpenAuth Authentication Service

The platform shall use OpenAuth as the authentication provider.

Functional Scope:

Centralised authentication server.

Email and password login for teachers.

Email and password login for students.

Password reset flow.

Email verification flow.

Access token issuance.

Refresh token issuance.

Session validation.

Logout.

Role mapping after successful authentication.

Tenant mapping after successful authentication.

Account status check after successful authentication.

Implementation Requirements:

OpenAuth shall run as a self-hosted authentication service.

The authentication service shall be deployed separately from the writing application.

The writing application shall act as an OAuth client.

The platform shall use OpenAuth subject claims to represent authenticated user identity.

The subject payload shall include user ID, school ID and role.

The application database shall remain the source of truth for user profile, role assignment, class assignment and school tenant assignment.

OpenAuth storage shall store authentication-specific data only.

Application user tables shall store application-specific data only.

Required Subject Schema:

Subject Type: user

Required Subject Properties:

userID

schoolID

role

accountStatus

Role Values:

SYSTEM_ADMIN

SCHOOL_ADMIN

TEACHER

STUDENT

Account Status Values:

ACTIVE

SUSPENDED

ARCHIVED

Acceptance Criteria:

User can login through OpenAuth.

Authenticated user receives a valid session in the writing application.

User role is correctly resolved after login.

Suspended user cannot access the platform.

Archived user cannot login.

Logout invalidates the current application session.

Password reset flow sends verification code through configured email service.

Authentication event is written to audit log.

### 6.2 Module M-002: User and Account Management

The system shall support user account creation, update, suspension and archival.

Functional Requirements:

FR-ACC-001: The system shall allow System Administrator to create a school tenant.

FR-ACC-002: The system shall allow System Administrator to import teachers by CSV.

FR-ACC-003: The system shall allow School Administrator to import students by CSV.

FR-ACC-004: CSV import shall validate required fields before account creation.

FR-ACC-005: CSV import shall reject duplicate email addresses within the same school tenant.

FR-ACC-006: CSV import shall produce an error report for invalid rows.

FR-ACC-007: The system shall allow account suspension.

FR-ACC-008: The system shall allow account archival.

FR-ACC-009: The system shall maintain account creation timestamp.

FR-ACC-010: The system shall maintain last login timestamp.

Required Teacher Fields:

teacher_email

teacher_display_name

role

school_id

assigned_class_ids

Required Student Fields:

student_email

student_display_name

student_level

class_name

school_id

CSV Import Acceptance Criteria:

Import succeeds only when all required fields are present.

Invalid rows are not imported.

Valid rows are imported.

Import result shows total rows, successful rows and rejected rows.

Rejected rows include rejection reason.

### 6.3 Module M-003: Class Management

The system shall support class-level organisation for P4 to P6.

Functional Requirements:

FR-CLS-001: The system shall allow School Administrator to create class records.

FR-CLS-002: The system shall support class level values P4, P5 and P6.

FR-CLS-003: The system shall allow students to be assigned to one class.

FR-CLS-004: The system shall allow teachers to be assigned to one or more classes.

FR-CLS-005: The system shall display class student count.

FR-CLS-006: The system shall prevent deletion of a class with active assignments.

FR-CLS-007: The system shall allow archival of inactive class records.

Acceptance Criteria:

A class can be created with level and class name.

Students can be added to class.

Students can be removed from class before assignment submission.

Teacher can view assigned classes.

Teacher cannot view unassigned classes.

### 6.4 Module M-004: Writing Task Management

The system shall allow teachers to create school-based writing tasks.

Functional Requirements:

FR-TASK-001: Teacher can create a writing task.

FR-TASK-002: Writing task shall include title.

FR-TASK-003: Writing task shall include level.

FR-TASK-004: Writing task shall include writing instruction.

FR-TASK-005: Writing task shall include word limit.

FR-TASK-006: Writing task shall include due date.

FR-TASK-007: Writing task shall include writing mode.

FR-TASK-008: Writing task shall include assigned rubric.

FR-TASK-009: Writing task shall include assigned class.

FR-TASK-010: Teacher can save task as draft.

FR-TASK-011: Teacher can publish task.

FR-TASK-012: Published task cannot be deleted after student submission exists.

FR-TASK-013: Teacher can archive completed task.

Writing Mode Values:

PRACTICE

EXAM

Required Task Fields:

task_id

school_id

title

level

instruction

mode

word_minimum

word_maximum

due_at

rubric_id

created_by

status

Task Status Values:

DRAFT

PUBLISHED

CLOSED

ARCHIVED

Acceptance Criteria:

Teacher can create one P4 task.

Teacher can create one P5 task.

Teacher can create one P6 task.

Student can only see published tasks assigned to the student’s class.

Student cannot see draft tasks.

Student cannot submit after task is closed.

### 6.5 Module M-005: Rubric Management

The system shall support school-based rubrics for AI marking and teacher review.

Functional Requirements:

FR-RUB-001: Teacher can create rubric.

FR-RUB-002: Teacher can edit rubric before use.

FR-RUB-003: Teacher can duplicate existing rubric.

FR-RUB-004: Teacher can archive rubric.

FR-RUB-005: Rubric shall include dimensions.

FR-RUB-006: Each rubric dimension shall include score range.

FR-RUB-007: Each rubric dimension shall include descriptor.

FR-RUB-008: Rubric total score shall be calculated from dimension scores.

FR-RUB-009: Rubric shall support teacher review.

Required Rubric Dimensions for Version 1.0:

Content

Language

Organisation

Optional Rubric Dimension:

Task Achievement

Rubric Field Requirements:

rubric_id

school_id

title

level

dimensions

total_score

status

created_by

created_at

updated_at

Acceptance Criteria:

Teacher can create a rubric with Content, Language and Organisation.

Teacher can set score range for each dimension.

Teacher can assign rubric to writing task.

AI marking result displays dimension-level score.

Teacher can override AI dimension score.

### 6.6 Module M-006: Practice Mode Writing Editor

Practice Mode shall provide AI-assisted writing support during the writing process.

Functional Requirements:

FR-PRAC-001: Student can open assigned Practice Mode task.

FR-PRAC-002: Student can write in a web-based editor.

FR-PRAC-003: The editor shall autosave draft content.

FR-PRAC-004: The editor shall display word count.

FR-PRAC-005: The editor shall display writing instructions.

FR-PRAC-006: The editor shall show AI suggestions during writing.

FR-PRAC-007: AI suggestions shall be displayed as inline highlights.

FR-PRAC-008: AI suggestions shall be displayed in a side panel.

FR-PRAC-009: Student can accept suggestion.

FR-PRAC-010: Student can dismiss suggestion.

FR-PRAC-011: Student can request explanation for suggestion.

FR-PRAC-012: Student can submit final writing.

FR-PRAC-013: System shall preserve original writing version and final submitted version.

Suggestion Categories:

Grammar

Spelling

Punctuation

Vocabulary

Sentence Clarity

Organisation

Content Relevance

Suggestion Card Fields:

suggestion_id

category

original_text

suggested_text

explanation

severity

status

Suggestion Status Values:

OPEN

ACCEPTED

DISMISSED

Acceptance Criteria:

Student can write in editor.

System autosaves draft.

Student can see writing suggestions.

Student can accept suggestion and text is updated.

Student can dismiss suggestion and suggestion is hidden.

Student can submit final writing.

Submitted writing is locked from student editing.

### 6.7 Module M-007: Exam Mode Writing Interface

Exam Mode shall provide a restricted writing environment.

Functional Requirements:

FR-EXAM-001: Student can open assigned Exam Mode task.

FR-EXAM-002: Exam Mode shall display writing prompt.

FR-EXAM-003: Exam Mode shall display timer when duration is configured.

FR-EXAM-004: Exam Mode shall disable real-time AI writing suggestions.

FR-EXAM-005: Exam Mode shall disable suggestion panel.

FR-EXAM-006: Exam Mode shall disable AI rewrite function.

FR-EXAM-007: Exam Mode shall disable copy-and-paste into writing editor.

FR-EXAM-008: Exam Mode shall record browser focus loss event.

FR-EXAM-009: Exam Mode shall autosave writing content.

FR-EXAM-010: Exam Mode shall submit automatically when timer expires.

FR-EXAM-011: Student can manually submit before timer expires.

FR-EXAM-012: Submitted Exam Mode writing shall be locked.

FR-EXAM-013: AI marking shall be triggered after submission.

Anti-cheating Event Types:

PASTE_ATTEMPT

WINDOW_BLUR

WINDOW_FOCUS

FULLSCREEN_EXIT

SUBMISSION

AUTO_SUBMISSION

Acceptance Criteria:

Student cannot receive AI suggestion in Exam Mode.

Paste action is blocked in Exam Mode editor.

Focus loss event is recorded.

Submission is locked after completion.

AI marking starts after submission.

Teacher can view recorded exam events.

### 6.8 Module M-008: AI Auto-marking

The system shall automatically mark submitted writing using the assigned rubric.

Functional Requirements:

FR-MARK-001: AI marking shall be triggered after submission.

FR-MARK-002: AI marking shall use task instruction.

FR-MARK-003: AI marking shall use assigned rubric.

FR-MARK-004: AI marking shall produce dimension-level score.

FR-MARK-005: AI marking shall produce overall score.

FR-MARK-006: AI marking shall produce summary feedback.

FR-MARK-007: AI marking shall produce sentence-level comments.

FR-MARK-008: AI marking shall produce improvement recommendations.

FR-MARK-009: AI marking result shall be saved with model version, timestamp and prompt version.

FR-MARK-010: Teacher can review AI marking result.

FR-MARK-011: Teacher can override AI marking result.

FR-MARK-012: Teacher override shall be logged.

Required Marking Output:

content_score

language_score

organisation_score

total_score

summary_feedback

strengths

weaknesses

sentence_feedback

improvement_recommendations

model_metadata

Acceptance Criteria:

Submission receives AI marking result.

Marking result includes all required rubric dimensions.

Teacher can view AI score.

Teacher can change AI score.

Final released score reflects teacher override when override exists.

Teacher override event is recorded in audit log.

### 6.9 Module M-009: Individualised Feedback

The system shall generate individualised feedback for each student submission.

Functional Requirements:

FR-FBK-001: Feedback shall cover content.

FR-FBK-002: Feedback shall cover language.

FR-FBK-003: Feedback shall cover organisation.

FR-FBK-004: Feedback shall identify strengths.

FR-FBK-005: Feedback shall identify weaknesses.

FR-FBK-006: Feedback shall provide next-step improvement advice.

FR-FBK-007: Feedback shall use student-readable language.

FR-FBK-008: Feedback shall be released to student only after teacher approval or task-level auto-release setting.

Feedback Sections:

Overall Comment

Content Feedback

Language Feedback

Organisation Feedback

Strengths

Areas for Improvement

Next Writing Advice

Acceptance Criteria:

Feedback appears in student result page after release.

Feedback is grouped by section.

Teacher can edit feedback before release.

Student cannot view unreleased feedback.

### 6.10 Module M-010: Post-writing Exercises

The system shall generate individualised post-writing exercises based on student weaknesses.

Functional Requirements:

FR-EXER-001: System shall generate exercises after AI marking.

FR-EXER-002: Exercise generation shall use identified weaknesses.

FR-EXER-003: Exercise shall be linked to the original writing task.

FR-EXER-004: Exercise shall include question prompt.

FR-EXER-005: Exercise shall include expected answer or marking reference.

FR-EXER-006: Student can complete exercise.

FR-EXER-007: Teacher can view exercise completion status.

Exercise Types for Version 1.0:

Sentence correction.

Vocabulary replacement.

Sentence expansion.

Paragraph ordering.

Topic sentence improvement.

Acceptance Criteria:

At least one post-writing exercise is generated after marking.

Student can open exercise.

Student can submit exercise response.

Teacher can view completion status.

### 6.11 Module M-011: Student Dashboard

The system shall provide a student dashboard.

Functional Requirements:

FR-STU-001: Student can view assigned tasks.

FR-STU-002: Student can view task status.

FR-STU-003: Student can continue Practice Mode draft.

FR-STU-004: Student can start Exam Mode task.

FR-STU-005: Student can view submitted tasks.

FR-STU-006: Student can view released feedback.

FR-STU-007: Student can view post-writing exercises.

Task Status Values:

NOT_STARTED

IN_PROGRESS

SUBMITTED

MARKED

FEEDBACK_RELEASED

CLOSED

Acceptance Criteria:

Student dashboard lists assigned tasks.

Student dashboard does not show other class tasks.

Student can access feedback only after release.

Student can access own progress only.

### 6.12 Module M-012: Teacher Dashboard

The system shall provide a teacher dashboard.

Functional Requirements:

FR-TCH-001: Teacher can view assigned classes.

FR-TCH-002: Teacher can view active writing tasks.

FR-TCH-003: Teacher can view submission progress.

FR-TCH-004: Teacher can view pending review items.

FR-TCH-005: Teacher can view class performance summary.

FR-TCH-006: Teacher can export task result.

Acceptance Criteria:

Teacher dashboard displays assigned classes.

Teacher dashboard displays active tasks.

Teacher dashboard displays submitted count.

Teacher dashboard displays marking completion count.

### 6.13 Module M-013: Class-based Report

The system shall provide class-based reports.

Functional Requirements:

FR-RPT-001: Teacher can generate report for a writing task.

FR-RPT-002: Teacher can generate report for a class.

FR-RPT-003: Report shall show average total score.

FR-RPT-004: Report shall show average dimension score.

FR-RPT-005: Report shall show common strengths.

FR-RPT-006: Report shall show common weaknesses.

FR-RPT-007: Report shall show student-level completion status.

FR-RPT-008: Report shall export CSV.

FR-RPT-009: Report shall export PDF.

Report Sections:

Class Overview

Submission Completion

Score Distribution

Rubric Dimension Analysis

Common Strengths

Common Weaknesses

Recommended Teaching Focus

Student-level Table

Acceptance Criteria:

Teacher can view report in browser.

Teacher can export CSV.

Teacher can export PDF.

Report includes all required sections.

Report only includes students in assigned class.

### 6.14 Module M-014: Technical Support for Teachers

The system shall provide support workflow for teachers.

Functional Requirements:

FR-SUP-T-001: Teacher can submit support ticket.

FR-SUP-T-002: Teacher ticket shall include issue category.

FR-SUP-T-003: Teacher ticket shall include description.

FR-SUP-T-004: Teacher ticket shall include screenshot attachment.

FR-SUP-T-005: System Administrator can view teacher tickets.

FR-SUP-T-006: System Administrator can update ticket status.

Teacher Support Categories:

Login issue.

Account issue.

Class issue.

Writing task issue.

Rubric issue.

AI marking issue.

Report export issue.

Data correction request.

Ticket Status Values:

OPEN

IN_PROGRESS

WAITING_FOR_SCHOOL

RESOLVED

CLOSED

Acceptance Criteria:

Teacher can submit ticket.

Ticket appears in support admin panel.

Ticket status can be updated.

Ticket history is retained.

### 6.15 Module M-015: Technical Support for Students

The system shall provide controlled student support workflow.

Functional Requirements:

FR-SUP-S-001: Student can report login issue through school support channel.

FR-SUP-S-002: Student can report task access issue through platform form after login.

FR-SUP-S-003: Student ticket shall be visible to assigned teacher.

FR-SUP-S-004: Teacher can escalate student ticket to System Administrator.

FR-SUP-S-005: System shall not expose student support tickets to other students.

Student Support Categories:

Login issue.

Cannot find task.

Cannot submit writing.

Feedback not visible.

Exercise not visible.

Browser issue.

Acceptance Criteria:

Student can raise support request after login.

Teacher can view student request.

Teacher can escalate request.

Student cannot view other student requests.

## 7. Data Requirements

### 7.1 Core Data Entities

The system shall maintain the following core entities:

School

User

TeacherProfile

StudentProfile

Class

ClassMembership

WritingTask

Rubric

RubricDimension

Submission

Draft

AISuggestion

MarkingResult

TeacherReview

PostWritingExercise

ClassReport

SupportTicket

AuditLog

AIUsageLog

### 7.2 User Data Fields

Required User Fields:

user_id

school_id

email

display_name

role

account_status

created_at

updated_at

last_login_at

### 7.3 Student Data Fields

Required StudentProfile Fields:

student_id

user_id

school_id

level

class_id

student_number

created_at

updated_at

### 7.4 Teacher Data Fields

Required TeacherProfile Fields:

teacher_id

user_id

school_id

assigned_class_ids

created_at

updated_at

### 7.5 Submission Data Fields

Required Submission Fields:

submission_id

task_id

student_id

school_id

submitted_text

submitted_at

status

word_count

mode

ai_marking_status

teacher_review_status

### 7.6 Data Retention

The system shall apply the following retention controls:

Active student accounts shall be retained during the contract period.

Archived student accounts shall be inaccessible to students.

Writing submissions shall be retained during the contract period.

Data export shall be provided to the school before production data deletion.

Production data deletion shall require written school approval.

Audit logs shall be retained for support and security review during the contract period.

### 7.7 Data Export

The system shall support the following export formats:

CSV for student list.

CSV for submission results.

CSV for class report.

PDF for class report.

PDF for individual feedback report.

## 8. Data Protection and Privacy Requirements

### 8.1 Personal Data Scope

The platform processes the following personal data categories:

Student name.

Student email.

Student class.

Student level.

Student writing submission.

Student marks.

Student feedback.

Teacher name.

Teacher email.

Teacher actions in the system.

### 8.2 Data Minimisation

The system shall only collect data required for user authentication, class management, writing assignment, AI marking, feedback generation, reporting and support.

The system shall not collect the following data:

HKID number.

Home address.

Parent phone number.

Student photo.

Biometric data.

Financial data.

### 8.3 AI Processing Control

The system shall apply the following AI processing controls:

Student name shall not be sent to AI model provider.

Student email shall not be sent to AI model provider.

Class name shall not be sent to AI model provider unless required for report generation.

Submitted writing text may be sent to AI model provider for marking and feedback generation.

AI request shall use submission ID instead of student identity.

AI output shall be stored in the platform database.

AI output shall be reviewable by teacher.

AI output shall not be treated as final assessment until released by teacher or task-level auto-release setting.

### 8.4 Model Training Restriction

Student submissions shall not be used to train vendor-owned AI models.

The selected AI provider shall be configured or contractually required not to use submitted student content for model training.

### 8.5 Access Control

The system shall enforce role-based access control.

Access Rules:

Student can access own submissions only.

Teacher can access submissions of assigned classes only.

School Administrator can access account and class administration functions.

System Administrator can access operational configuration and audit logs.

Cross-school data access is prohibited.

### 8.6 Audit Logging

The system shall record the following events:

Login success.

Login failure.

Logout.

Password reset request.

Account creation.

Account suspension.

Student import.

Teacher import.

Task creation.

Task publication.

Submission.

AI marking completion.

Teacher score override.

Feedback release.

Report export.

Support ticket creation.

Support ticket update.

Data export.

Configuration change.

Audit Log Fields:

audit_log_id

school_id

actor_user_id

actor_role

action

target_entity_type

target_entity_id

timestamp

ip_address

user_agent

result

## 9. Security Requirements

### 9.1 Authentication Security

SEC-AUTH-001: Authentication shall be handled by OpenAuth.

SEC-AUTH-002: Application session shall be established only after OpenAuth authentication succeeds.

SEC-AUTH-003: Access token shall not be stored in plain browser local storage for server-rendered application flow.

SEC-AUTH-004: Session cookie shall be HTTP-only.

SEC-AUTH-005: Session cookie shall use Secure flag in production.

SEC-AUTH-006: Session cookie shall use SameSite protection.

SEC-AUTH-007: Password reset shall require verification code.

SEC-AUTH-008: Suspended accounts shall be denied access after authentication callback.

### 9.2 Authorisation Security

SEC-AUTHZ-001: Every API endpoint shall validate authenticated user identity.

SEC-AUTHZ-002: Every API endpoint shall validate user role.

SEC-AUTHZ-003: Every school data query shall filter by school_id.

SEC-AUTHZ-004: Teacher data query shall filter by assigned class.

SEC-AUTHZ-005: Student data query shall filter by student_id.

### 9.3 Application Security

SEC-APP-001: API input shall be validated.

SEC-APP-002: File upload shall validate file type.

SEC-APP-003: File upload shall validate file size.

SEC-APP-004: HTML content shall be sanitised before rendering.

SEC-APP-005: AI-generated content shall be rendered as text unless explicitly formatted by the system.

SEC-APP-006: Error messages shall not expose stack trace in production.

SEC-APP-007: Secrets shall be stored in environment variables or secret manager.

SEC-APP-008: Production database credentials shall not be committed to source code.

### 9.4 AI Security

SEC-AI-001: AI prompt shall separate system instruction, rubric, task instruction and student writing.

SEC-AI-002: Student writing shall be treated as untrusted input.

SEC-AI-003: Prompt injection instruction inside student writing shall not override system marking instruction.

SEC-AI-004: AI output shall be validated against required schema.

SEC-AI-005: Invalid AI output shall be marked as failed and retried.

SEC-AI-006: AI usage shall be logged.

SEC-AI-007: AI cost limit shall be configurable.

## 10. Non-functional Requirements

### 10.1 Capacity

NFR-CAP-001: The system shall support at least 470 active student accounts for the school tenant.

NFR-CAP-002: The system shall support teacher accounts required for P4 to P6 English writing teaching operation.

NFR-CAP-003: The system shall support 11 annual writing topics for the specified academic year.

NFR-CAP-004: The system shall support multiple submissions per student in Practice Mode when teacher reopens task.

### 10.2 Performance

NFR-PERF-001: Student dashboard shall load assigned task list within acceptable classroom operation time.

NFR-PERF-002: Writing editor shall remain usable during autosave.

NFR-PERF-003: Autosave shall not block typing.

NFR-PERF-004: AI marking shall run asynchronously after submission.

NFR-PERF-005: Student shall not need to keep browser open after successful submission.

### 10.3 Availability

NFR-AVL-001: Production service shall be hosted on managed cloud infrastructure.

NFR-AVL-002: Planned maintenance shall be performed outside agreed school usage hours.

NFR-AVL-003: Planned maintenance notice shall be sent to school contact before maintenance.

### 10.4 Compatibility

NFR-COMP-001: The platform shall support latest stable Chrome.

NFR-COMP-002: The platform shall support latest stable Microsoft Edge.

NFR-COMP-003: The platform shall support latest stable Safari on macOS.

NFR-COMP-004: The platform shall provide responsive layout for tablet browser use.

NFR-COMP-005: Native mobile application is out of scope.

### 10.5 Usability

NFR-USE-001: Student writing interface shall show writing prompt and editor on the same page.

NFR-USE-002: Teacher task creation shall follow step-by-step workflow.

NFR-USE-003: Error messages shall use plain English.

NFR-USE-004: Student feedback shall be grouped by category.

NFR-USE-005: Teacher report shall be exportable without technical assistance.

## 11. User Interface Requirements

### 11.1 Student Practice Mode UI

Required Layout:

Top bar with platform logo, task title and save status.

Left or central writing editor.

Right suggestion panel.

Word count indicator.

Submit button.

Feedback category filter.

Required Interactions:

Inline highlight on problematic text.

Click highlight to open suggestion card.

Accept suggestion.

Dismiss suggestion.

Request explanation.

Submit writing.

### 11.2 Student Exam Mode UI

Required Layout:

Task title.

Writing prompt.

Timer.

Word count.

Writing editor.

Submit button.

Exam notice.

Exam Notice Text:

“This is Exam Mode. AI writing suggestions are disabled. Your answer will be marked after submission.”

### 11.3 Teacher Task Builder UI

Required Steps:

Select level.

Enter task title.

Enter writing instruction.

Select Practice Mode or Exam Mode.

Select class.

Select rubric.

Configure due date.

Preview task.

Publish task.

### 11.4 Teacher Marking Review UI

Required Sections:

Student information.

Submitted writing.

AI marking result.

Rubric dimension scores.

Sentence-level comments.

Teacher override fields.

Teacher final feedback.

Release feedback button.

### 11.5 Teacher Report UI

Required Sections:

Class summary.

Completion status.

Average score.

Dimension score chart.

Common strengths.

Common weaknesses.

Recommended teaching focus.

Student table.

Export buttons.

## 12. API Requirements

### 12.1 Authentication API Boundary

OpenAuth shall handle authentication endpoints.

The writing application shall handle application-level user profile and authorisation.

### 12.2 Application API Groups

Required API Groups:

/api/users

/api/classes

/api/tasks

/api/rubrics

/api/submissions

/api/marking

/api/feedback

/api/exercises

/api/reports

/api/support

/api/audit

/api/admin

### 12.3 API Response Standard

All application APIs shall return structured JSON.

Success Response Fields:

success

data

request_id

Error Response Fields:

success

error_code

message

request_id

### 12.4 Required Error Codes

AUTH_REQUIRED

ACCESS_DENIED

VALIDATION_ERROR

NOT_FOUND

DUPLICATE_RECORD

TASK_CLOSED

SUBMISSION_LOCKED

AI_MARKING_FAILED

EXPORT_FAILED

SUPPORT_TICKET_NOT_FOUND

## 13. Reporting Requirements

### 13.1 Individual Student Report

Required Fields:

Student name.

Class.

Task title.

Submission date.

Total score.

Content score.

Language score.

Organisation score.

Overall feedback.

Strengths.

Weaknesses.

Recommended exercises.

### 13.2 Class Report

Required Fields:

School name.

Class name.

Level.

Task title.

Total students.

Submitted students.

Not submitted students.

Average total score.

Average content score.

Average language score.

Average organisation score.

Common strengths.

Common weaknesses.

Recommended teaching focus.

## 14. Operational Requirements

### 14.1 Deployment

The production deployment shall include:

Web frontend.

Application backend.

OpenAuth authentication service.

Production database.

Object storage for uploaded files.

Logging service.

Environment configuration.

Backup configuration.

### 14.2 Backup

Backup Requirements:

Production database backup shall be configured.

Backup restoration procedure shall be documented.

Backup access shall be restricted.

Backup files shall not be publicly accessible.

### 14.3 Monitoring

Monitoring Requirements:

Application error logging.

API request error logging.

AI marking failure logging.

Login failure logging.

Export failure logging.

Support ticket logging.

### 14.4 Support

Support Channels:

Teacher support ticket inside platform.

Student issue escalation through teacher.

Administrative email for school coordinator.

Support Categories:

Login.

Account.

Class.

Task.

Submission.

Marking.

Report.

Export.

System availability.

## 15. Acceptance Criteria

### 15.1 System Acceptance

The system shall be accepted when the following criteria are met:

OpenAuth login works for teacher.

OpenAuth login works for student.

Teacher can create class.

Teacher can create writing task.

Teacher can create rubric.

Teacher can assign task to class.

Student can complete Practice Mode writing.

Student can complete Exam Mode writing.

AI marking result is generated.

Teacher can review and override AI marking.

Student can view released feedback.

Post-writing exercise is generated.

Class report is generated.

CSV export works.

PDF export works.

Audit log records key actions.

Suspended account cannot access system.

Student cannot access other student submission.

Teacher cannot access unassigned class.

Support ticket workflow works.

### 15.2 UAT Test Scenarios

UAT-001: Teacher Login

Steps:

Open teacher login page.

Enter valid teacher email and password.

Complete OpenAuth login.

Redirect to teacher dashboard.

Expected Result:

Teacher dashboard is displayed.

UAT-002: Student Login

Steps:

Open student login page.

Enter valid student email and password.

Complete OpenAuth login.

Redirect to student dashboard.

Expected Result:

Student dashboard is displayed.

UAT-003: Create Writing Task

Steps:

Teacher opens task builder.

Selects level P4.

Enters title and instruction.

Selects Practice Mode.

Selects class.

Selects rubric.

Publishes task.

Expected Result:

Task appears in assigned student dashboard.

UAT-004: Practice Mode Submission

Steps:

Student opens Practice Mode task.

Types writing response.

Reviews suggestions.

Accepts one suggestion.

Submits writing.

Expected Result:

Submission is saved and locked.

UAT-005: Exam Mode Submission

Steps:

Student opens Exam Mode task.

Writes response.

Attempts paste.

Submits writing.

Expected Result:

Paste is blocked, event is logged and submission is saved.

UAT-006: AI Marking

Steps:

Student submits writing.

System triggers AI marking.

Teacher opens marking page.

Expected Result:

AI score and feedback are displayed.

UAT-007: Teacher Override

Steps:

Teacher opens marking result.

Changes content score.

Adds teacher comment.

Saves final result.

Expected Result:

Final score is updated and override is logged.

UAT-008: Feedback Release

Steps:

Teacher reviews marking.

Teacher clicks release feedback.

Student opens result page.

Expected Result:

Student can view released feedback.

UAT-009: Class Report

Steps:

Teacher opens report page.

Selects class and task.

Generates report.

Expected Result:

Report displays completion, average scores, strengths and weaknesses.

UAT-010: Export

Steps:

Teacher opens report.

Clicks CSV export.

Clicks PDF export.

Expected Result:

CSV and PDF files are generated.

## 16. Deliverables

### 16.1 Project Management Deliverables

Project Implementation Plan.

Project Schedule.

Risk Register.

Issue Log.

Change Request Log.

UAT Plan.

UAT Result Record.

Acceptance Sign-off Form.

### 16.2 System Documentation Deliverables

Product Requirements Document.

System Design Specification.

Database Schema Document.

API Specification.

Security Design Note.

Data Protection Note.

Deployment Guide.

Backup and Restore Guide.

Operation Manual.

Teacher User Guide.

Student User Guide.

Administrator User Guide.

### 16.3 Software Deliverables

Frontend source code.

Backend source code.

OpenAuth configuration source code.

Database migration scripts.

Production deployment configuration.

Environment variable template.

Test cases.

UAT test data template.

### 16.4 Training Deliverables

Teacher training session.

Administrator training session.

Quick start guide for students.

Support workflow guide.

## 17. Implementation Milestones

### Milestone 1: Project Initiation and Requirements Confirmation

Deliverables:

Confirmed PRD.

Confirmed user roles.

Confirmed task list.

Confirmed rubric format.

Confirmed account import template.

Exit Criteria:

School confirms account data format.

School confirms writing topic list.

School confirms rubric requirements.

Project scope is frozen for Version 1.0.

### Milestone 2: Core Platform and OpenAuth Integration

Deliverables:

OpenAuth service.

Login flow.

Session management.

Role mapping.

User import.

Class management.

Exit Criteria:

Teacher login passes UAT.

Student login passes UAT.

Imported users can access correct dashboard.

Access control test passes.

### Milestone 3: Writing Task and Rubric Workflow

Deliverables:

Task builder.

Rubric builder.

Task assignment.

Student task dashboard.

Exit Criteria:

Teacher can publish task.

Student can see assigned task.

Unassigned student cannot see task.

### Milestone 4: Practice Mode and Exam Mode

Deliverables:

Practice Mode editor.

Suggestion panel.

Exam Mode editor.

Autosave.

Submission locking.

Exam event log.

Exit Criteria:

Practice Mode submission passes UAT.

Exam Mode submission passes UAT.

Paste blocking works in Exam Mode.

Autosave works.

### Milestone 5: AI Marking and Feedback

Deliverables:

AI marking service.

Rubric scoring.

Feedback generation.

Teacher review.

Feedback release.

Exit Criteria:

AI marking output matches required schema.

Teacher can override score.

Student can view released feedback.

### Milestone 6: Exercises, Reports and Export

Deliverables:

Post-writing exercise generation.

Class report.

CSV export.

PDF export.

Exit Criteria:

Exercise generation passes UAT.

Class report passes UAT.

CSV export passes UAT.

PDF export passes UAT.

### Milestone 7: UAT, Bug Fixing and Production Deployment

Deliverables:

UAT environment.

UAT result record.

Bug fix log.

Production deployment.

User guides.

Acceptance sign-off.

Exit Criteria:

All critical UAT cases pass.

No unresolved critical defect.

Production environment is accessible.

School receives user guides.

Acceptance sign-off is completed.

## 18. Risk Register

### RISK-001: OpenAuth Version Status

Risk Description:

OpenAuth is selected as the authentication provider. The project shall lock the OpenAuth package version before UAT and production deployment.

Impact:

Authentication behaviour can change if package version changes during implementation.

Control Measures:

Lock package version.

Record version in deployment document.

Test login, logout, password reset and session refresh before release.

Avoid unreviewed dependency upgrade during production period.

### RISK-002: AI Marking Accuracy

Risk Description:

AI-generated marking can differ from teacher judgement.

Impact:

Student score dispute and teacher trust issue.

Control Measures:

Teacher review workflow.

Teacher override function.

AI output label as assistant result.

Rubric-based structured output.

Prompt version tracking.

### RISK-003: Student Data Privacy

Risk Description:

Student writing contains personal data or sensitive content.

Impact:

Privacy risk and school governance concern.

Control Measures:

Do not send student name to AI provider.

Use submission ID in AI request.

Restrict teacher access by class.

Maintain audit logs.

Require no-training configuration or contractual term with AI provider.

### RISK-004: Real-time Suggestion Complexity

Risk Description:

Grammarly-style inline suggestion requires editor annotation, position mapping and text replacement logic.

Impact:

Development delay and UI defects.

Control Measures:

Use established rich-text editor framework.

Implement suggestion card workflow in phases.

Separate grammar suggestion from AI explanation.

Complete editor UAT before full rollout.

### RISK-005: Student Support Load

Risk Description:

470 students can generate repeated login and submission issues.

Impact:

Developer support overload.

Control Measures:

Student support routed through teacher first.

Bulk password reset function.

Account import validation.

Student quick start guide.

Support ticket categorisation.

## 19. Change Control

Any change after PRD sign-off shall be recorded as a Change Request.

Change Request shall include:

Change request ID.

Request date.

Requestor.

Description.

Business reason.

Affected modules.

Estimated effort impact.

Schedule impact.

Approval status.

Changes requiring schedule or cost review:

New user role.

LMS integration.

Parent portal.

New marking dimension.

New report type.

New AI model provider.

Real-time collaboration.

OS-level exam lockdown.

Mobile application.

Additional school tenant.

## 20. Production Readiness Checklist

The system shall not be released to production until the following items are completed:

OpenAuth login tested.

Role-based access control tested.

Student import tested.

Teacher import tested.

Class assignment tested.

Task creation tested.

Practice Mode tested.

Exam Mode tested.

AI marking tested.

Teacher override tested.

Feedback release tested.

Report export tested.

Audit logging tested.

Backup configured.

Environment variables configured.

Production secrets removed from source code.

User guide delivered.

UAT sign-off completed.

Production URL delivered to school.

Support contact confirmed.

## 21. Version 1.0 Completion Definition

Version 1.0 is complete when the following conditions are all satisfied:

School tenant is created.

Teacher accounts are imported.

Student accounts are imported.

P4, P5 and P6 classes are created.

At least one writing task can be created and assigned.

Practice Mode works.

Exam Mode works.

AI marking works.

Teacher review works.

Feedback release works.

Post-writing exercise works.

Class report works.

CSV export works.

PDF export works.

OpenAuth login works.

Support ticket workflow works.

UAT pass record is completed.

Production deployment is completed.

User documentation is delivered.

Acceptance sign-off is obtained.

## 22. Recommended Delivery Boundary for Quotation

For the school quotation, the supplier shall commit to the following deliverable boundary:

One school tenant.

Approximately 470 student accounts.

Teacher accounts for relevant English teachers.

P4 to P6 class management.

11 annual writing topics.

Practice Mode.

Exam Mode.

AI auto-marking.

School-based rubrics.

Individual student feedback.

Post-writing exercises.

Class reports.

Teacher technical support.

Student support through teacher escalation.

User guides.

UAT and production deployment.

The supplier shall not commit to unlimited topic creation, unlimited AI usage, unlimited support requests, LMS integration, parent portal, mobile app, plagiarism detection, handwriting OCR or OS-level secure exam browser under Version 1.0.

## 23. Final Product Statement

The English AI Writing Platform 2026–2027 shall be a school-based web platform for Primary 4 to Primary 6 English writing practice and assessment. The platform shall use OpenAuth for authentication, provide separate teacher and student portals, support Practice Mode and Exam Mode, generate rubric-based AI marking, provide individualised writing feedback, create post-writing exercises and produce class-level analysis reports.

The platform shall preserve teacher authority over final assessment, protect student personal data, maintain access control by role and class, and provide operational support suitable for school pilot deployment.
