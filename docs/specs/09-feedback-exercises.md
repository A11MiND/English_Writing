# 09 Feedback Exercises

Status: Phase 7 foundation implemented.

## Authoritative Sources

- `docs/source_extracted/Product Requirements Document(1).md`
- `docs/source_extracted/Technical Proposal.md`

## Implemented Scope

- Teacher can release feedback for an `AI_MARKED` marking result.
- If no teacher review exists at release time, release creates one from the AI scores.
- Student feedback is hidden until `teacher_reviews.status = RELEASED` and `feedback_released_at` is set.
- AI recommended exercises are converted into `post_writing_exercises` after successful marking.
- Student can view released feedback and assigned exercises.
- Student can submit exercise responses and mark exercises as completed.

## Access Rules

- Teacher release APIs require `TEACHER` and assigned-class access.
- Student feedback APIs require `STUDENT` and filter by authenticated `student_id`.
- Unreleased feedback returns `NOT_FOUND` to students.
- Exercise completion requires released feedback for the related submission.

## Remaining Work

- Improve release controls and completion status UI.
- Add exercise generation customization by rubric dimension.
- Add class-level exercise completion summary in reports.
