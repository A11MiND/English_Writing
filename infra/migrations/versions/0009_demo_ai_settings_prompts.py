"""demo ai settings prompts

Revision ID: 0009_demo_ai_settings
Revises: 0008_phase_8_reports
Create Date: 2026-07-07
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0009_demo_ai_settings"
down_revision: str | None = "0008_phase_8_reports"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "ai_provider_settings",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("school_id", sa.String(length=36), nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("model", sa.String(length=128), nullable=True),
        sa.Column("base_url", sa.String(length=500), nullable=True),
        sa.Column("api_key_secret", sa.Text(), nullable=True),
        sa.Column("timeout_seconds", sa.Integer(), nullable=False),
        sa.Column("updated_by", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["school_id"], ["schools.id"]),
        sa.ForeignKeyConstraint(["updated_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("school_id", name="uq_ai_provider_settings_school"),
    )
    op.create_index(op.f("ix_ai_provider_settings_school_id"), "ai_provider_settings", ["school_id"])

    op.create_table(
        "prompt_drafts",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("school_id", sa.String(length=36), nullable=False),
        sa.Column("created_by", sa.String(length=36), nullable=False),
        sa.Column("level", sa.String(length=16), nullable=False),
        sa.Column("mode", sa.String(length=32), nullable=False),
        sa.Column("teaching_focus", sa.Text(), nullable=False),
        sa.Column("word_minimum", sa.Integer(), nullable=True),
        sa.Column("word_maximum", sa.Integer(), nullable=True),
        sa.Column("exam_duration_minutes", sa.Integer(), nullable=True),
        sa.Column("rubric_id", sa.String(length=36), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("instruction", sa.Text(), nullable=False),
        sa.Column("rubric_notes", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("model", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["rubric_id"], ["rubrics.id"]),
        sa.ForeignKeyConstraint(["school_id"], ["schools.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_prompt_drafts_created_at"), "prompt_drafts", ["created_at"])
    op.create_index(op.f("ix_prompt_drafts_created_by"), "prompt_drafts", ["created_by"])
    op.create_index(op.f("ix_prompt_drafts_level"), "prompt_drafts", ["level"])
    op.create_index(op.f("ix_prompt_drafts_mode"), "prompt_drafts", ["mode"])
    op.create_index(op.f("ix_prompt_drafts_rubric_id"), "prompt_drafts", ["rubric_id"])
    op.create_index(op.f("ix_prompt_drafts_school_id"), "prompt_drafts", ["school_id"])
    op.create_index(op.f("ix_prompt_drafts_status"), "prompt_drafts", ["status"])


def downgrade() -> None:
    op.drop_index(op.f("ix_prompt_drafts_status"), table_name="prompt_drafts")
    op.drop_index(op.f("ix_prompt_drafts_school_id"), table_name="prompt_drafts")
    op.drop_index(op.f("ix_prompt_drafts_rubric_id"), table_name="prompt_drafts")
    op.drop_index(op.f("ix_prompt_drafts_mode"), table_name="prompt_drafts")
    op.drop_index(op.f("ix_prompt_drafts_level"), table_name="prompt_drafts")
    op.drop_index(op.f("ix_prompt_drafts_created_by"), table_name="prompt_drafts")
    op.drop_index(op.f("ix_prompt_drafts_created_at"), table_name="prompt_drafts")
    op.drop_table("prompt_drafts")
    op.drop_index(op.f("ix_ai_provider_settings_school_id"), table_name="ai_provider_settings")
    op.drop_table("ai_provider_settings")
