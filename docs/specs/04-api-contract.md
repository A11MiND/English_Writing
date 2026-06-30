# 04 API Contract

Status: Phase 8 implemented baseline plus AI marking, feedback and report endpoints.

## Authoritative Sources

- `docs/source_extracted/Product Requirements Document(1).md`
- `docs/source_extracted/Technical Proposal.md`

## Standard Response

Success:

```json
{
  "success": true,
  "data": {},
  "request_id": "string"
}
```

Error:

```json
{
  "success": false,
  "error_code": "string",
  "message": "string",
  "request_id": "string"
}
```

## Phase 0 Endpoints

- `GET /health`
- `GET /api/health`
- `GET /api/health/db`

## Phase 1 Endpoints

- `POST /api/auth/login`
- `POST /api/auth/logout`
- `GET /api/auth/me`
- `GET /api/protected/admin`
- `GET /api/protected/teacher`
- `GET /api/protected/student`

## Phase 2 Endpoints

- `GET /api/admin/users`
- `POST /api/admin/import/users`
- `GET /api/admin/classes`
- `POST /api/admin/classes`
- `GET /api/teacher/classes`
- `GET /api/student/profile`

All Phase 2 endpoints return the standard envelope and enforce session, role and school/class ownership filters.

## Phase 3 Endpoints

Teacher endpoints:

- `GET /api/teacher/rubrics`
- `POST /api/teacher/rubrics`
- `GET /api/teacher/tasks`
- `POST /api/teacher/tasks`
- `POST /api/teacher/tasks/{task_id}/assignments`

Student endpoints:

- `GET /api/student/tasks`

All Phase 3 endpoints return the standard envelope. Teacher endpoints require `TEACHER`, filter by `school_id`, and class assignment actions require assigned-class membership. Student task list filters by authenticated student profile and current class, and returns only `PUBLISHED` tasks.

## Phase 4 Endpoints

Student writing endpoints:

- `GET /api/student/tasks/{task_id}/writing`
- `PUT /api/student/tasks/{task_id}/draft`
- `POST /api/student/tasks/{task_id}/submit`
- `POST /api/student/tasks/{task_id}/exam-events`

All Phase 4 endpoints require `STUDENT`, filter by authenticated `student_id`, validate the task is assigned to the student's current class, and return the standard envelope. Draft save and submit reject `CLOSED` or `ARCHIVED` tasks with `TASK_CLOSED`. Draft save and duplicate submit reject already submitted tasks with `SUBMISSION_LOCKED`.

Submitting writing creates a queued `marking_results` record and attempts to enqueue the marking result ID to Redis for worker processing. Redis enqueue failure does not reject the submission because the submitted essay is already persisted and locked.

## Phase 5 Grammar Suggestion Endpoint

Student suggestion endpoint:

- `POST /api/suggestions/check`

Request:

```json
{
  "task_id": "uuid",
  "text": "string",
  "language": "en-US",
  "check_mode": "CHANGED"
}
```

Response data:

```json
{
  "suggestions": [
    {
      "id": "string",
      "rule_id": "string",
      "category": "string",
      "message": "string",
      "short_message": "string",
      "offset": 0,
      "length": 3,
      "replacements": ["string"],
      "severity": "WARNING"
    }
  ],
  "cached": false,
  "service_status": "ok",
  "check_mode": "CHANGED"
}
```

The endpoint requires `STUDENT`, filters by authenticated `student_id`, validates the task is assigned to the student's current class, and only allows `PRACTICE` tasks. Exam Mode requests are rejected with `ACCESS_DENIED`. Grammar service failures return an empty suggestion list with `service_status = unavailable` so writing is not blocked.

## Phase 6 AI Marking Foundation Endpoints

Teacher marking endpoints:

- `GET /api/teacher/marking/submissions`
- `POST /api/teacher/marking-results/{marking_result_id}/run`
- `POST /api/teacher/marking-results/{marking_result_id}/retry`
- `POST /api/teacher/marking-results/{marking_result_id}/review`
- `POST /api/teacher/marking-results/{marking_result_id}/release`

All marking endpoints require `TEACHER`, filter by `school_id`, and enforce assigned-class access using the submitted student's current class. `run` processes queued marking with the configured LLM adapter as a UAT/manual fallback. Normal submit flow is Redis queue plus worker. `retry` is limited to `AI_MARKING_FAILED`. `review` stores teacher override scores and writes an audit log. `release` makes feedback visible to the student.

## Phase 7 Feedback And Exercise Endpoints

Student feedback endpoints:

- `GET /api/student/submissions/{submission_id}/feedback`
- `POST /api/student/exercises/{exercise_id}/complete`

Student feedback endpoints require `STUDENT` and filter by authenticated `student_id`. Unreleased feedback is not visible and returns `NOT_FOUND`.

## Phase 8 Reports And Export Endpoints

Teacher report endpoints:

- `GET /api/teacher/reports/classes/{class_id}`
- `POST /api/teacher/reports/classes/{class_id}/generate`
- `GET /api/teacher/reports/classes/{class_id}/export.csv`
- `GET /api/teacher/reports/classes/{class_id}/export.pdf`

All report endpoints require `TEACHER`, filter by `school_id`, and enforce assigned-class access through `class_memberships`. JSON report endpoints return the standard envelope. CSV and PDF endpoints return downloadable files and write `CLASS_REPORT_EXPORTED` audit logs.

Report payload includes:

- `class_report`
- `summary`
- `rubric_breakdown`
- `score_distribution`
- `common_weaknesses`
- `completion_rows`

## Required Error Codes

- `AUTH_REQUIRED`
- `ACCESS_DENIED`
- `VALIDATION_ERROR`
- `NOT_FOUND`
- `DUPLICATE_RECORD`
- `TASK_CLOSED`
- `SUBMISSION_LOCKED`
- `AI_MARKING_FAILED`
- `EXPORT_FAILED`
- `SUPPORT_TICKET_NOT_FOUND`
- `HEALTH_CHECK_FAILED`
