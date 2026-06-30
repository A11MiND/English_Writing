"""phase 7 feedback exercises

Revision ID: 0007_phase_7_feedback
Revises: 0006_phase_6_ai_marking
Create Date: 2026-06-28
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "0007_phase_7_feedback"
down_revision: str | None = "0006_phase_6_ai_marking"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "teacher_reviews",
        sa.Column("feedback_released_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "teacher_reviews",
        sa.Column("feedback_released_by", sa.String(length=36), nullable=True),
    )
    op.create_foreign_key(
        "fk_teacher_reviews_feedback_released_by_users",
        "teacher_reviews",
        "users",
        ["feedback_released_by"],
        ["id"],
    )

    op.create_table(
        "post_writing_exercises",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("school_id", sa.String(length=36), nullable=False),
        sa.Column("marking_result_id", sa.String(length=36), nullable=False),
        sa.Column("submission_id", sa.String(length=36), nullable=False),
        sa.Column("student_id", sa.String(length=36), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("exercise_type", sa.String(length=64), nullable=False),
        sa.Column("focus_area", sa.String(length=128), nullable=False),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("response_text", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("assigned_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["marking_result_id"], ["marking_results.id"]),
        sa.ForeignKeyConstraint(["school_id"], ["schools.id"]),
        sa.ForeignKeyConstraint(["student_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["submission_id"], ["submissions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_post_writing_exercises_assigned_at"), "post_writing_exercises", ["assigned_at"])
    op.create_index(op.f("ix_post_writing_exercises_exercise_type"), "post_writing_exercises", ["exercise_type"])
    op.create_index(op.f("ix_post_writing_exercises_marking_result_id"), "post_writing_exercises", ["marking_result_id"])
    op.create_index(op.f("ix_post_writing_exercises_school_id"), "post_writing_exercises", ["school_id"])
    op.create_index(op.f("ix_post_writing_exercises_status"), "post_writing_exercises", ["status"])
    op.create_index(op.f("ix_post_writing_exercises_student_id"), "post_writing_exercises", ["student_id"])
    op.create_index(op.f("ix_post_writing_exercises_submission_id"), "post_writing_exercises", ["submission_id"])


def downgrade() -> None:
    op.drop_index(op.f("ix_post_writing_exercises_submission_id"), table_name="post_writing_exercises")
    op.drop_index(op.f("ix_post_writing_exercises_student_id"), table_name="post_writing_exercises")
    op.drop_index(op.f("ix_post_writing_exercises_status"), table_name="post_writing_exercises")
    op.drop_index(op.f("ix_post_writing_exercises_school_id"), table_name="post_writing_exercises")
    op.drop_index(op.f("ix_post_writing_exercises_marking_result_id"), table_name="post_writing_exercises")
    op.drop_index(op.f("ix_post_writing_exercises_exercise_type"), table_name="post_writing_exercises")
    op.drop_index(op.f("ix_post_writing_exercises_assigned_at"), table_name="post_writing_exercises")
    op.drop_table("post_writing_exercises")
    op.drop_constraint("fk_teacher_reviews_feedback_released_by_users", "teacher_reviews", type_="foreignkey")
    op.drop_column("teacher_reviews", "feedback_released_by")
    op.drop_column("teacher_reviews", "feedback_released_at")
