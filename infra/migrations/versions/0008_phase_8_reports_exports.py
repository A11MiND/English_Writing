"""phase 8 reports exports

Revision ID: 0008_phase_8_reports
Revises: 0007_phase_7_feedback
Create Date: 2026-06-28
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0008_phase_8_reports"
down_revision: str | None = "0007_phase_7_feedback"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "class_reports",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("school_id", sa.String(length=36), nullable=False),
        sa.Column("class_id", sa.String(length=36), nullable=False),
        sa.Column("task_id", sa.String(length=36), nullable=True),
        sa.Column("generated_by", sa.String(length=36), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("summary", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["class_id"], ["classes.id"]),
        sa.ForeignKeyConstraint(["generated_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["school_id"], ["schools.id"]),
        sa.ForeignKeyConstraint(["task_id"], ["writing_tasks.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_class_reports_class_id"), "class_reports", ["class_id"])
    op.create_index(op.f("ix_class_reports_generated_at"), "class_reports", ["generated_at"])
    op.create_index(op.f("ix_class_reports_generated_by"), "class_reports", ["generated_by"])
    op.create_index(op.f("ix_class_reports_school_id"), "class_reports", ["school_id"])
    op.create_index(op.f("ix_class_reports_status"), "class_reports", ["status"])
    op.create_index(op.f("ix_class_reports_task_id"), "class_reports", ["task_id"])


def downgrade() -> None:
    op.drop_index(op.f("ix_class_reports_task_id"), table_name="class_reports")
    op.drop_index(op.f("ix_class_reports_status"), table_name="class_reports")
    op.drop_index(op.f("ix_class_reports_school_id"), table_name="class_reports")
    op.drop_index(op.f("ix_class_reports_generated_by"), table_name="class_reports")
    op.drop_index(op.f("ix_class_reports_generated_at"), table_name="class_reports")
    op.drop_index(op.f("ix_class_reports_class_id"), table_name="class_reports")
    op.drop_table("class_reports")
