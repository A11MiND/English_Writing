"""phase 1 auth rbac

Revision ID: 0002_phase_1_auth_rbac
Revises: 0001_phase_0_baseline
Create Date: 2026-06-27
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0002_phase_1_auth_rbac"
down_revision: str | None = "0001_phase_0_baseline"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHOOL_ID = "11111111-1111-4111-8111-111111111111"
SYSTEM_ADMIN_ID = "22222222-2222-4222-8222-222222222222"
SCHOOL_ADMIN_ID = "33333333-3333-4333-8333-333333333333"
TEACHER_ID = "44444444-4444-4444-8444-444444444444"
STUDENT_ID = "55555555-5555-4555-8555-555555555555"
SUSPENDED_ID = "66666666-6666-4666-8666-666666666666"
ARCHIVED_ID = "77777777-7777-4777-8777-777777777777"


def upgrade() -> None:
    op.create_table(
        "schools",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_schools_code"), "schools", ["code"], unique=True)

    op.create_table(
        "users",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("school_id", sa.String(length=36), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("display_name", sa.String(length=255), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["school_id"], ["schools.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=True)
    op.create_index(op.f("ix_users_role"), "users", ["role"], unique=False)
    op.create_index(op.f("ix_users_school_id"), "users", ["school_id"], unique=False)
    op.create_index(op.f("ix_users_status"), "users", ["status"], unique=False)

    op.create_table(
        "user_sessions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("session_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("invalidated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_user_sessions_expires_at"), "user_sessions", ["expires_at"], unique=False)
    op.create_index(
        op.f("ix_user_sessions_session_hash"), "user_sessions", ["session_hash"], unique=True
    )
    op.create_index(op.f("ix_user_sessions_user_id"), "user_sessions", ["user_id"], unique=False)

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("school_id", sa.String(length=36), nullable=True),
        sa.Column("actor_user_id", sa.String(length=36), nullable=True),
        sa.Column("actor_role", sa.String(length=32), nullable=True),
        sa.Column("action", sa.String(length=96), nullable=False),
        sa.Column("ip_address", sa.String(length=64), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_audit_logs_action"), "audit_logs", ["action"], unique=False)
    op.create_index(
        op.f("ix_audit_logs_actor_user_id"), "audit_logs", ["actor_user_id"], unique=False
    )
    op.create_index(op.f("ix_audit_logs_created_at"), "audit_logs", ["created_at"], unique=False)
    op.create_index(op.f("ix_audit_logs_school_id"), "audit_logs", ["school_id"], unique=False)

    op.execute(
        sa.text(
            """
            insert into schools (id, name, code, created_at)
            values (:id, :name, :code, now())
            """
        ).bindparams(id=SCHOOL_ID, name="W F Joseph Lee Primary School", code="WFJLP")
    )
    users = [
        (SYSTEM_ADMIN_ID, None, "system@edcosys.local", "System Administrator", "SYSTEM_ADMIN", "ACTIVE"),
        (SCHOOL_ADMIN_ID, SCHOOL_ID, "admin@wfjosephlee.edu.hk", "School Administrator", "SCHOOL_ADMIN", "ACTIVE"),
        (TEACHER_ID, SCHOOL_ID, "teacher@wfjosephlee.edu.hk", "English Teacher", "TEACHER", "ACTIVE"),
        (STUDENT_ID, SCHOOL_ID, "student@wfjosephlee.edu.hk", "P5A Student", "STUDENT", "ACTIVE"),
        (SUSPENDED_ID, SCHOOL_ID, "suspended@wfjosephlee.edu.hk", "Suspended Student", "STUDENT", "SUSPENDED"),
        (ARCHIVED_ID, SCHOOL_ID, "archived@wfjosephlee.edu.hk", "Archived Teacher", "TEACHER", "ARCHIVED"),
    ]
    for user in users:
        op.execute(
            sa.text(
                """
                insert into users
                    (id, school_id, email, display_name, role, status, created_at, updated_at)
                values
                    (:id, :school_id, :email, :display_name, :role, :status, now(), now())
                """
            ).bindparams(
                id=user[0],
                school_id=user[1],
                email=user[2],
                display_name=user[3],
                role=user[4],
                status=user[5],
            )
        )


def downgrade() -> None:
    op.drop_index(op.f("ix_audit_logs_school_id"), table_name="audit_logs")
    op.drop_index(op.f("ix_audit_logs_created_at"), table_name="audit_logs")
    op.drop_index(op.f("ix_audit_logs_actor_user_id"), table_name="audit_logs")
    op.drop_index(op.f("ix_audit_logs_action"), table_name="audit_logs")
    op.drop_table("audit_logs")
    op.drop_index(op.f("ix_user_sessions_user_id"), table_name="user_sessions")
    op.drop_index(op.f("ix_user_sessions_session_hash"), table_name="user_sessions")
    op.drop_index(op.f("ix_user_sessions_expires_at"), table_name="user_sessions")
    op.drop_table("user_sessions")
    op.drop_index(op.f("ix_users_status"), table_name="users")
    op.drop_index(op.f("ix_users_school_id"), table_name="users")
    op.drop_index(op.f("ix_users_role"), table_name="users")
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_table("users")
    op.drop_index(op.f("ix_schools_code"), table_name="schools")
    op.drop_table("schools")
