"""curated demo showcase seed

Revision ID: 0010_demo_showcase
Revises: 0009_demo_ai_settings
Create Date: 2026-07-10
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "0010_demo_showcase"
down_revision: str | None = "0009_demo_ai_settings"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHOOL_ID = "11111111-1111-4111-8111-111111111111"
TEACHER_ID = "44444444-4444-4444-8444-444444444444"
STUDENT_ID = "55555555-5555-4555-8555-555555555555"
PRACTICE_TASK_ID = "dddddddd-dddd-4ddd-8ddd-dddddddddd01"
SUBMISSION_ID = "12121212-1212-4212-8212-121212121212"
MARKING_RESULT_ID = "13131313-1313-4313-8313-131313131313"
TEACHER_REVIEW_ID = "14141414-1414-4414-8414-141414141414"
EXERCISE_ID = "15151515-1515-4515-8515-151515151515"

STORY_TEXT = (
    "Today was the day of our P5 Science Fair. I felt nervous at first because I had to "
    "present in front of many people. My hands were shaking. When it was my turn, I took a "
    "deep breath and smiled. I explained how our volcano model worked. My classmates asked "
    "interesting questions, and I was proud of how our group worked together. In the end, we "
    "received a special mention. I felt happy and thankful for my friends and teacher. It was "
    "a day I will always remember."
)


def upgrade() -> None:
    op.execute(
        sa.text(
            """
            insert into submissions
                (
                    id, school_id, task_id, student_id, draft_id, mode, content_html,
                    content_text, word_count, status, submitted_at, created_at
                )
            values
                (
                    :id, :school_id, :task_id, :student_id, null, 'PRACTICE', :content_html,
                    :content_text, 82, 'SUBMITTED', now() - interval '1 day', now() - interval '1 day'
                )
            on conflict (task_id, student_id) do nothing
            """
        ).bindparams(
            id=SUBMISSION_ID,
            school_id=SCHOOL_ID,
            task_id=PRACTICE_TASK_ID,
            student_id=STUDENT_ID,
            content_html=f"<p>{STORY_TEXT}</p>",
            content_text=STORY_TEXT,
        )
    )
    op.execute(
        sa.text(
            """
            insert into marking_results
                (
                    id, school_id, submission_id, task_id, student_id, status,
                    content_score, language_score, organisation_score, total_score,
                    confidence_level, content_feedback, language_feedback,
                    organisation_feedback, strengths, weaknesses, sentence_level_comments,
                    recommended_exercises, warning_flags, model_metadata, attempts,
                    last_error, queued_at, marked_at, created_at, updated_at
                )
            values
                (
                    :id, :school_id, :submission_id, :task_id, :student_id, 'AI_MARKED',
                    4, 3, 4, 11, 'HIGH',
                    'Clear events and feelings are shown with relevant details.',
                    'Some word choices and past-tense forms need refining.',
                    'Events are ordered with a clear beginning, middle and ending.',
                    '["Clear event sequence", "Relevant personal reflection", "Strong ending"]'::jsonb,
                    '["Past tense consistency", "Stronger feeling words", "Spelling accuracy"]'::jsonb,
                    '[
                      {"sentence":"I felt nervous at first because I had to present in front of many people.","comment":"Good detail. Try a stronger feeling word to show how nervous you felt.","category":"LANGUAGE"},
                      {"sentence":"My hands were shaking.","comment":"Keep the whole event in the past tense.","category":"LANGUAGE"},
                      {"sentence":"In the end, we received a special mention.","comment":"Check the spelling of received.","category":"MECHANICS"}
                    ]'::jsonb,
                    '[
                      {"title":"Strengthen one feeling","exercise_type":"revision","focus_area":"Language","prompt":"Rewrite one sentence using a stronger feeling word and one supporting detail."}
                    ]'::jsonb,
                    '[]'::jsonb,
                    '{"provider":"demo","model":"curated-showcase","source":"seed"}'::jsonb,
                    1, null, now() - interval '1 day', now() - interval '1 day',
                    now() - interval '1 day', now() - interval '1 day'
                )
            on conflict (submission_id) do nothing
            """
        ).bindparams(
            id=MARKING_RESULT_ID,
            school_id=SCHOOL_ID,
            submission_id=SUBMISSION_ID,
            task_id=PRACTICE_TASK_ID,
            student_id=STUDENT_ID,
        )
    )
    op.execute(
        sa.text(
            """
            insert into teacher_reviews
                (
                    id, school_id, marking_result_id, submission_id, teacher_id,
                    content_score, language_score, organisation_score, total_score,
                    review_notes, status, created_at, updated_at,
                    feedback_released_at, feedback_released_by
                )
            values
                (
                    :id, :school_id, :marking_result_id, :submission_id, :teacher_id,
                    4, 3, 4, 11,
                    'You shared your day clearly and showed how you felt. Try stronger feeling words and check past tense. Well done!',
                    'RELEASED', now() - interval '20 hours', now() - interval '20 hours',
                    now() - interval '20 hours', :teacher_id
                )
            on conflict (marking_result_id) do nothing
            """
        ).bindparams(
            id=TEACHER_REVIEW_ID,
            school_id=SCHOOL_ID,
            marking_result_id=MARKING_RESULT_ID,
            submission_id=SUBMISSION_ID,
            teacher_id=TEACHER_ID,
        )
    )
    op.execute(
        sa.text(
            """
            insert into post_writing_exercises
                (
                    id, school_id, marking_result_id, submission_id, student_id,
                    title, exercise_type, focus_area, prompt, response_text, status,
                    assigned_at, completed_at, created_at, updated_at
                )
            values
                (
                    :id, :school_id, :marking_result_id, :submission_id, :student_id,
                    'Strengthen one feeling', 'revision', 'Language',
                    'Rewrite one sentence using a stronger feeling word and one supporting detail.',
                    null, 'ASSIGNED', now() - interval '20 hours', null,
                    now() - interval '20 hours', now() - interval '20 hours'
                )
            on conflict (id) do nothing
            """
        ).bindparams(
            id=EXERCISE_ID,
            school_id=SCHOOL_ID,
            marking_result_id=MARKING_RESULT_ID,
            submission_id=SUBMISSION_ID,
            student_id=STUDENT_ID,
        )
    )


def downgrade() -> None:
    op.execute(sa.text("delete from post_writing_exercises where id = :id").bindparams(id=EXERCISE_ID))
    op.execute(sa.text("delete from teacher_reviews where id = :id").bindparams(id=TEACHER_REVIEW_ID))
    op.execute(sa.text("delete from marking_results where id = :id").bindparams(id=MARKING_RESULT_ID))
    op.execute(sa.text("delete from submissions where id = :id").bindparams(id=SUBMISSION_ID))
