"""phase 4 writing editor

Revision ID: 0005_phase_4_editor
Revises: 0004_phase_3_tasks
Create Date: 2026-06-27
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0005_phase_4_editor"
down_revision: str | None = "0004_phase_3_tasks"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

EXAM_TASK_ID = "dddddddd-dddd-4ddd-8ddd-dddddddddd02"


def upgrade() -> None:
    op.add_column("writing_tasks", sa.Column("exam_duration_minutes", sa.Integer(), nullable=True))
    op.execute(
        sa.text(
            """
            update writing_tasks
            set exam_duration_minutes = 30
            where id = :task_id and mode = 'EXAM'
            """
        ).bindparams(task_id=EXAM_TASK_ID)
    )

    op.create_table(
        "drafts",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("school_id", sa.String(length=36), nullable=False),
        sa.Column("task_id", sa.String(length=36), nullable=False),
        sa.Column("student_id", sa.String(length=36), nullable=False),
        sa.Column("content_html", sa.Text(), nullable=False),
        sa.Column("content_text", sa.Text(), nullable=False),
        sa.Column("word_count", sa.Integer(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("saved_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["school_id"], ["schools.id"]),
        sa.ForeignKeyConstraint(["student_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["task_id"], ["writing_tasks.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("task_id", "student_id", name="uq_drafts_task_student"),
    )
    op.create_index(op.f("ix_drafts_saved_at"), "drafts", ["saved_at"])
    op.create_index(op.f("ix_drafts_school_id"), "drafts", ["school_id"])
    op.create_index(op.f("ix_drafts_status"), "drafts", ["status"])
    op.create_index(op.f("ix_drafts_student_id"), "drafts", ["student_id"])
    op.create_index(op.f("ix_drafts_task_id"), "drafts", ["task_id"])

    op.create_table(
        "submissions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("school_id", sa.String(length=36), nullable=False),
        sa.Column("task_id", sa.String(length=36), nullable=False),
        sa.Column("student_id", sa.String(length=36), nullable=False),
        sa.Column("draft_id", sa.String(length=36), nullable=True),
        sa.Column("mode", sa.String(length=32), nullable=False),
        sa.Column("content_html", sa.Text(), nullable=False),
        sa.Column("content_text", sa.Text(), nullable=False),
        sa.Column("word_count", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["draft_id"], ["drafts.id"]),
        sa.ForeignKeyConstraint(["school_id"], ["schools.id"]),
        sa.ForeignKeyConstraint(["student_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["task_id"], ["writing_tasks.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("task_id", "student_id", name="uq_submissions_task_student"),
    )
    op.create_index(op.f("ix_submissions_mode"), "submissions", ["mode"])
    op.create_index(op.f("ix_submissions_school_id"), "submissions", ["school_id"])
    op.create_index(op.f("ix_submissions_status"), "submissions", ["status"])
    op.create_index(op.f("ix_submissions_student_id"), "submissions", ["student_id"])
    op.create_index(op.f("ix_submissions_submitted_at"), "submissions", ["submitted_at"])
    op.create_index(op.f("ix_submissions_task_id"), "submissions", ["task_id"])

    op.create_table(
        "exam_events",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("school_id", sa.String(length=36), nullable=False),
        sa.Column("task_id", sa.String(length=36), nullable=False),
        sa.Column("student_id", sa.String(length=36), nullable=False),
        sa.Column("event_type", sa.String(length=32), nullable=False),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["school_id"], ["schools.id"]),
        sa.ForeignKeyConstraint(["student_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["task_id"], ["writing_tasks.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_exam_events_event_type"), "exam_events", ["event_type"])
    op.create_index(op.f("ix_exam_events_occurred_at"), "exam_events", ["occurred_at"])
    op.create_index(op.f("ix_exam_events_school_id"), "exam_events", ["school_id"])
    op.create_index(op.f("ix_exam_events_student_id"), "exam_events", ["student_id"])
    op.create_index(op.f("ix_exam_events_task_id"), "exam_events", ["task_id"])


def downgrade() -> None:
    op.drop_index(op.f("ix_exam_events_task_id"), table_name="exam_events")
    op.drop_index(op.f("ix_exam_events_student_id"), table_name="exam_events")
    op.drop_index(op.f("ix_exam_events_school_id"), table_name="exam_events")
    op.drop_index(op.f("ix_exam_events_occurred_at"), table_name="exam_events")
    op.drop_index(op.f("ix_exam_events_event_type"), table_name="exam_events")
    op.drop_table("exam_events")
    op.drop_index(op.f("ix_submissions_task_id"), table_name="submissions")
    op.drop_index(op.f("ix_submissions_submitted_at"), table_name="submissions")
    op.drop_index(op.f("ix_submissions_student_id"), table_name="submissions")
    op.drop_index(op.f("ix_submissions_status"), table_name="submissions")
    op.drop_index(op.f("ix_submissions_school_id"), table_name="submissions")
    op.drop_index(op.f("ix_submissions_mode"), table_name="submissions")
    op.drop_table("submissions")
    op.drop_index(op.f("ix_drafts_task_id"), table_name="drafts")
    op.drop_index(op.f("ix_drafts_student_id"), table_name="drafts")
    op.drop_index(op.f("ix_drafts_status"), table_name="drafts")
    op.drop_index(op.f("ix_drafts_school_id"), table_name="drafts")
    op.drop_index(op.f("ix_drafts_saved_at"), table_name="drafts")
    op.drop_table("drafts")
    op.drop_column("writing_tasks", "exam_duration_minutes")
