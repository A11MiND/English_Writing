"""phase 6 ai marking foundation

Revision ID: 0006_phase_6_ai_marking
Revises: 0005_phase_4_editor
Create Date: 2026-06-27
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0006_phase_6_ai_marking"
down_revision: str | None = "0005_phase_4_editor"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "marking_results",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("school_id", sa.String(length=36), nullable=False),
        sa.Column("submission_id", sa.String(length=36), nullable=False),
        sa.Column("task_id", sa.String(length=36), nullable=False),
        sa.Column("student_id", sa.String(length=36), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("content_score", sa.Integer(), nullable=True),
        sa.Column("language_score", sa.Integer(), nullable=True),
        sa.Column("organisation_score", sa.Integer(), nullable=True),
        sa.Column("total_score", sa.Integer(), nullable=True),
        sa.Column("confidence_level", sa.String(length=32), nullable=True),
        sa.Column("content_feedback", sa.Text(), nullable=True),
        sa.Column("language_feedback", sa.Text(), nullable=True),
        sa.Column("organisation_feedback", sa.Text(), nullable=True),
        sa.Column("strengths", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("weaknesses", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("sentence_level_comments", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("recommended_exercises", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("warning_flags", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("model_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("queued_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("marked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["school_id"], ["schools.id"]),
        sa.ForeignKeyConstraint(["student_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["submission_id"], ["submissions.id"]),
        sa.ForeignKeyConstraint(["task_id"], ["writing_tasks.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("submission_id", name="uq_marking_results_submission"),
    )
    op.create_index(op.f("ix_marking_results_marked_at"), "marking_results", ["marked_at"])
    op.create_index(op.f("ix_marking_results_queued_at"), "marking_results", ["queued_at"])
    op.create_index(op.f("ix_marking_results_school_id"), "marking_results", ["school_id"])
    op.create_index(op.f("ix_marking_results_status"), "marking_results", ["status"])
    op.create_index(op.f("ix_marking_results_student_id"), "marking_results", ["student_id"])
    op.create_index(op.f("ix_marking_results_submission_id"), "marking_results", ["submission_id"])
    op.create_index(op.f("ix_marking_results_task_id"), "marking_results", ["task_id"])

    op.create_table(
        "teacher_reviews",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("school_id", sa.String(length=36), nullable=False),
        sa.Column("marking_result_id", sa.String(length=36), nullable=False),
        sa.Column("submission_id", sa.String(length=36), nullable=False),
        sa.Column("teacher_id", sa.String(length=36), nullable=False),
        sa.Column("content_score", sa.Integer(), nullable=True),
        sa.Column("language_score", sa.Integer(), nullable=True),
        sa.Column("organisation_score", sa.Integer(), nullable=True),
        sa.Column("total_score", sa.Integer(), nullable=True),
        sa.Column("review_notes", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["marking_result_id"], ["marking_results.id"]),
        sa.ForeignKeyConstraint(["school_id"], ["schools.id"]),
        sa.ForeignKeyConstraint(["submission_id"], ["submissions.id"]),
        sa.ForeignKeyConstraint(["teacher_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("marking_result_id", name="uq_teacher_reviews_marking_result"),
    )
    op.create_index(op.f("ix_teacher_reviews_marking_result_id"), "teacher_reviews", ["marking_result_id"])
    op.create_index(op.f("ix_teacher_reviews_school_id"), "teacher_reviews", ["school_id"])
    op.create_index(op.f("ix_teacher_reviews_status"), "teacher_reviews", ["status"])
    op.create_index(op.f("ix_teacher_reviews_submission_id"), "teacher_reviews", ["submission_id"])
    op.create_index(op.f("ix_teacher_reviews_teacher_id"), "teacher_reviews", ["teacher_id"])

    op.create_table(
        "ai_usage_logs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("school_id", sa.String(length=36), nullable=False),
        sa.Column("marking_result_id", sa.String(length=36), nullable=True),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("model", sa.String(length=128), nullable=False),
        sa.Column("operation", sa.String(length=64), nullable=False),
        sa.Column("prompt_tokens", sa.Integer(), nullable=True),
        sa.Column("completion_tokens", sa.Integer(), nullable=True),
        sa.Column("total_tokens", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["marking_result_id"], ["marking_results.id"]),
        sa.ForeignKeyConstraint(["school_id"], ["schools.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_ai_usage_logs_created_at"), "ai_usage_logs", ["created_at"])
    op.create_index(op.f("ix_ai_usage_logs_marking_result_id"), "ai_usage_logs", ["marking_result_id"])
    op.create_index(op.f("ix_ai_usage_logs_operation"), "ai_usage_logs", ["operation"])
    op.create_index(op.f("ix_ai_usage_logs_provider"), "ai_usage_logs", ["provider"])
    op.create_index(op.f("ix_ai_usage_logs_school_id"), "ai_usage_logs", ["school_id"])
    op.create_index(op.f("ix_ai_usage_logs_status"), "ai_usage_logs", ["status"])


def downgrade() -> None:
    op.drop_index(op.f("ix_ai_usage_logs_status"), table_name="ai_usage_logs")
    op.drop_index(op.f("ix_ai_usage_logs_school_id"), table_name="ai_usage_logs")
    op.drop_index(op.f("ix_ai_usage_logs_provider"), table_name="ai_usage_logs")
    op.drop_index(op.f("ix_ai_usage_logs_operation"), table_name="ai_usage_logs")
    op.drop_index(op.f("ix_ai_usage_logs_marking_result_id"), table_name="ai_usage_logs")
    op.drop_index(op.f("ix_ai_usage_logs_created_at"), table_name="ai_usage_logs")
    op.drop_table("ai_usage_logs")
    op.drop_index(op.f("ix_teacher_reviews_teacher_id"), table_name="teacher_reviews")
    op.drop_index(op.f("ix_teacher_reviews_submission_id"), table_name="teacher_reviews")
    op.drop_index(op.f("ix_teacher_reviews_status"), table_name="teacher_reviews")
    op.drop_index(op.f("ix_teacher_reviews_school_id"), table_name="teacher_reviews")
    op.drop_index(op.f("ix_teacher_reviews_marking_result_id"), table_name="teacher_reviews")
    op.drop_table("teacher_reviews")
    op.drop_index(op.f("ix_marking_results_task_id"), table_name="marking_results")
    op.drop_index(op.f("ix_marking_results_submission_id"), table_name="marking_results")
    op.drop_index(op.f("ix_marking_results_student_id"), table_name="marking_results")
    op.drop_index(op.f("ix_marking_results_status"), table_name="marking_results")
    op.drop_index(op.f("ix_marking_results_school_id"), table_name="marking_results")
    op.drop_index(op.f("ix_marking_results_queued_at"), table_name="marking_results")
    op.drop_index(op.f("ix_marking_results_marked_at"), table_name="marking_results")
    op.drop_table("marking_results")
