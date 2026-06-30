# 10 Reports Export

Status: Phase 8 foundation implemented.

## Authoritative Sources

- `docs/source_extracted/Product Requirements Document(1).md`
- `docs/source_extracted/Technical Proposal.md`

## Scope

Reports are class-level teacher analytics for assigned classes. They support the controlled pilot workflow:

- completion status
- rubric breakdown
- score distribution
- common weaknesses
- per student/task completion rows
- CSV export
- PDF export
- export audit log

## Access Rules

- Teacher endpoints require `TEACHER`.
- Every query filters by `school_id`.
- Teacher class access requires `class_memberships.membership_role = TEACHER`.
- Students do not access class reports.
- Report generation does not call the LLM provider.

## API

- `GET /api/teacher/reports/classes/{class_id}` returns a live preview.
- `POST /api/teacher/reports/classes/{class_id}/generate` stores a `class_reports` snapshot.
- `GET /api/teacher/reports/classes/{class_id}/export.csv` returns a CSV download.
- `GET /api/teacher/reports/classes/{class_id}/export.pdf` returns a PDF download.

Optional `task_id` query parameter scopes the report to one assigned writing task.

## Acceptance

- Teacher can view assigned class report.
- Teacher cannot view unassigned class report.
- Report includes completion status.
- Report includes rubric breakdown.
- Report includes common weaknesses.
- CSV export works.
- PDF export works.
- Export action is logged.
