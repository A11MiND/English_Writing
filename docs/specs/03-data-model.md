# 03 Data Model

Status: Phase 8 foundation implemented.

## Authoritative Sources

- `docs/source_extracted/Product Requirements Document(1).md`
- `docs/source_extracted/Technical Proposal.md`

## Phase 0-1 Data Model

- Alembic is configured with baseline revision `0001_phase_0_baseline`.
- Phase 1 creates `schools`, `users`, `user_sessions` and `audit_logs`.

## Phase 2 Data Model

Phase 2 adds core school data tables:

- `teacher_profiles`: one row per teacher user.
- `student_profiles`: one row per student user, including student number, level and current class.
- `classes`: school-owned class records such as P4A, P5A and P6A.
- `class_memberships`: class-user membership rows for teacher assignments and student class membership.

Rules:

- Every school-owned row includes `school_id`.
- Duplicate email is rejected.
- Duplicate class name in the same school and academic year is rejected.
- A student may have only one active student class membership.
- Teacher class visibility is based on `class_memberships` rows with `membership_role = TEACHER`.

## Phase 3 Data Model

Phase 3 adds task and rubric workflow tables:

- `rubrics`: school-owned rubric definitions with title, level, total score, status and `created_by`.
- `rubric_dimensions`: ordered dimensions for each rubric, including score range and descriptor.
- `writing_tasks`: school-owned writing tasks with title, level, instruction, writing mode, word limits, due date, assigned rubric, status and `created_by`.
- `assignments`: class-level task assignments with assigned class, assigned-by teacher and assigned timestamp.

Rules:

- Every Phase 3 table includes `school_id`.
- Every task and rubric includes `created_by`.
- Writing task mode values are `PRACTICE` and `EXAM`.
- Writing task status values are `DRAFT`, `PUBLISHED`, `CLOSED` and `ARCHIVED`.
- Rubric status values are `DRAFT`, `ACTIVE` and `ARCHIVED`.
- Students can see only published tasks assigned to their current class.
- Teachers can assign tasks only to classes where they have `class_memberships.membership_role = TEACHER`.

## Phase 4 Data Model

Phase 4 adds writing editor tables:

- `drafts`: one active draft per student/task, storing autosaved HTML, plain text, word count, version and save timestamp.
- `submissions`: locked final writing copy for a student/task, preserving the final HTML/text and submit timestamp.
- `exam_events`: append-only browser event log for Exam Mode events.

Phase 4 also adds `exam_duration_minutes` to `writing_tasks` for configured exam timers.

Rules:

- Every table includes `school_id`.
- Draft and submission rows include `student_id`.
- Student draft and submission APIs filter by authenticated `student_id`.
- A submitted student/task pair is locked and cannot be edited through draft autosave.
- Failed AI marking must not delete or modify submitted essay content.
- Exam event types are `PASTE_ATTEMPT`, `WINDOW_BLUR`, `WINDOW_FOCUS`, `FULLSCREEN_EXIT` and `SUBMISSION`.

## Phase 6 AI Marking Foundation Data Model

Phase 6 foundation adds:

- `marking_results`: one marking job/result per submission. Stores status, rubric dimension scores, feedback, schema-validated JSON fields, attempt count and failure detail.
- `teacher_reviews`: one teacher review row per marking result. Stores teacher-overridden scores, notes and review status.
- `ai_usage_logs`: append-only usage/failure log for AI marking provider calls.

Rules:

- Every table includes `school_id`.
- `marking_results.submission_id` is unique so a submission has one current AI marking record.
- Teacher review is stored separately from AI output so override does not destroy the AI result.
- Teacher marking APIs join through `student_profiles.current_class_id`, `assignments` and teacher `class_memberships` to enforce assigned-class access.
- AI marking failure updates only the marking result status/error fields; it never modifies `submissions.content_html` or `submissions.content_text`.

## Phase 7 Feedback And Exercise Data Model

Phase 7 adds:

- `teacher_reviews.feedback_released_at`: release timestamp for student-visible feedback.
- `teacher_reviews.feedback_released_by`: teacher user who released feedback.
- `post_writing_exercises`: assigned post-writing exercises generated from validated AI marking recommendations.

Rules:

- Every exercise includes `school_id`, `marking_result_id`, `submission_id` and `student_id`.
- Student exercise queries filter by authenticated `student_id`.
- Feedback is student-visible only when the teacher review status is `RELEASED`.

## Phase 8 Reports And Export Data Model

Phase 8 adds:

- `class_reports`: generated report snapshots for a school/class and optional task scope.

Rules:

- Every report includes `school_id`, `class_id`, `generated_by`, `status`, `summary`, `generated_at` and `created_at`.
- Optional `task_id` scopes a report to one writing task.
- Teacher report generation and export must join through `class_memberships` and require `membership_role = TEACHER`.
- Report summaries may include student names and numbers for assigned teachers, but no report data is sent to an LLM provider.
- Export actions are represented in `audit_logs` using `CLASS_REPORT_EXPORTED`.
