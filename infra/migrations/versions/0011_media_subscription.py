"""school subscription and generated task media

Revision ID: 0011_media_subscription
Revises: 0010_demo_showcase
Create Date: 2026-07-10
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "0011_media_subscription"
down_revision: str | None = "0010_demo_showcase"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHOOL_ID = "11111111-1111-4111-8111-111111111111"


def upgrade() -> None:
    op.add_column(
        "schools",
        sa.Column("plan_code", sa.String(length=32), nullable=False, server_default="FREE"),
    )
    op.add_column(
        "schools",
        sa.Column("subscription_status", sa.String(length=32), nullable=False, server_default="ACTIVE"),
    )
    op.add_column(
        "schools",
        sa.Column("subscription_renews_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_schools_plan_code", "schools", ["plan_code"], unique=False)
    op.create_index(
        "ix_schools_subscription_status", "schools", ["subscription_status"], unique=False
    )
    op.add_column("writing_tasks", sa.Column("image_path", sa.String(length=500), nullable=True))
    op.add_column(
        "writing_tasks", sa.Column("image_mime_type", sa.String(length=64), nullable=True)
    )
    op.execute(
        sa.text(
            "update schools set plan_code = 'SCHOOL_PRO', subscription_status = 'ACTIVE' where id = :id"
        ).bindparams(id=SCHOOL_ID)
    )


def downgrade() -> None:
    op.drop_column("writing_tasks", "image_mime_type")
    op.drop_column("writing_tasks", "image_path")
    op.drop_index("ix_schools_subscription_status", table_name="schools")
    op.drop_index("ix_schools_plan_code", table_name="schools")
    op.drop_column("schools", "subscription_renews_at")
    op.drop_column("schools", "subscription_status")
    op.drop_column("schools", "plan_code")
