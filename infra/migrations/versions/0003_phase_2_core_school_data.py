"""phase 2 core school data

Revision ID: 0003_phase_2_core_school_data
Revises: 0002_phase_1_auth_rbac
Create Date: 2026-06-27
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "0003_phase_2_core_school_data"
down_revision: str | None = "0002_phase_1_auth_rbac"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHOOL_ID = "11111111-1111-4111-8111-111111111111"
TEACHER_ID = "44444444-4444-4444-8444-444444444444"
STUDENT_ID = "55555555-5555-4555-8555-555555555555"
P4A_ID = "88888888-8888-4888-8888-888888888884"
P5A_ID = "88888888-8888-4888-8888-888888888885"
P6A_ID = "88888888-8888-4888-8888-888888888886"
P4A_TEACHER_MEMBERSHIP_ID = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaa4"
P5A_TEACHER_MEMBERSHIP_ID = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaa5"
P6A_TEACHER_MEMBERSHIP_ID = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaa6"
P5A_STUDENT_MEMBERSHIP_ID = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbb5"


def upgrade() -> None:
    op.create_table(
        "classes",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("school_id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.Column("level", sa.String(length=16), nullable=False),
        sa.Column("academic_year", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["school_id"], ["schools.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("school_id", "name", "academic_year", name="uq_classes_school_name_year"),
    )
    op.create_index(op.f("ix_classes_level"), "classes", ["level"], unique=False)
    op.create_index(op.f("ix_classes_school_id"), "classes", ["school_id"], unique=False)

    op.create_table(
        "teacher_profiles",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("school_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("staff_code", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["school_id"], ["schools.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_teacher_profiles_school_id"), "teacher_profiles", ["school_id"])
    op.create_index(op.f("ix_teacher_profiles_user_id"), "teacher_profiles", ["user_id"], unique=True)

    op.create_table(
        "student_profiles",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("school_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("student_number", sa.String(length=64), nullable=False),
        sa.Column("level", sa.String(length=16), nullable=False),
        sa.Column("current_class_id", sa.String(length=36), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["current_class_id"], ["classes.id"]),
        sa.ForeignKeyConstraint(["school_id"], ["schools.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("school_id", "student_number", name="uq_student_profiles_school_number"),
    )
    op.create_index(op.f("ix_student_profiles_level"), "student_profiles", ["level"])
    op.create_index(op.f("ix_student_profiles_school_id"), "student_profiles", ["school_id"])
    op.create_index(op.f("ix_student_profiles_student_number"), "student_profiles", ["student_number"])
    op.create_index(op.f("ix_student_profiles_user_id"), "student_profiles", ["user_id"], unique=True)

    op.create_table(
        "class_memberships",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("school_id", sa.String(length=36), nullable=False),
        sa.Column("class_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("membership_role", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["class_id"], ["classes.id"]),
        sa.ForeignKeyConstraint(["school_id"], ["schools.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("class_id", "user_id", "membership_role", name="uq_class_membership_role"),
    )
    op.create_index(op.f("ix_class_memberships_class_id"), "class_memberships", ["class_id"])
    op.create_index(
        op.f("ix_class_memberships_membership_role"), "class_memberships", ["membership_role"]
    )
    op.create_index(op.f("ix_class_memberships_school_id"), "class_memberships", ["school_id"])
    op.create_index(op.f("ix_class_memberships_user_id"), "class_memberships", ["user_id"])

    for class_id, name, level in [(P4A_ID, "P4A", "P4"), (P5A_ID, "P5A", "P5"), (P6A_ID, "P6A", "P6")]:
        op.execute(
            sa.text(
                """
                insert into classes (id, school_id, name, level, academic_year, status, created_at)
                values (:id, :school_id, :name, :level, '2026-2027', 'ACTIVE', now())
                on conflict (school_id, name, academic_year) do nothing
                """
            ).bindparams(id=class_id, school_id=SCHOOL_ID, name=name, level=level)
        )

    op.execute(
        sa.text(
            """
            insert into teacher_profiles (id, school_id, user_id, staff_code, created_at)
            values ('99999999-9999-4999-8999-999999999991', :school_id, :user_id, 'T001', now())
            on conflict (user_id) do nothing
            """
        ).bindparams(school_id=SCHOOL_ID, user_id=TEACHER_ID)
    )
    op.execute(
        sa.text(
            """
            insert into student_profiles
                (id, school_id, user_id, student_number, level, current_class_id, created_at)
            values
                ('99999999-9999-4999-8999-999999999992', :school_id, :user_id, 'S0001', 'P5', :class_id, now())
            on conflict (user_id) do nothing
            """
        ).bindparams(school_id=SCHOOL_ID, user_id=STUDENT_ID, class_id=P5A_ID)
    )
    for membership_id, class_id in [
        (P4A_TEACHER_MEMBERSHIP_ID, P4A_ID),
        (P5A_TEACHER_MEMBERSHIP_ID, P5A_ID),
        (P6A_TEACHER_MEMBERSHIP_ID, P6A_ID),
    ]:
        op.execute(
            sa.text(
                """
                insert into class_memberships
                    (id, school_id, class_id, user_id, membership_role, created_at)
                values
                    (:id, :school_id, :class_id, :user_id, 'TEACHER', now())
                on conflict (class_id, user_id, membership_role) do nothing
                """
            ).bindparams(
                id=membership_id, school_id=SCHOOL_ID, class_id=class_id, user_id=TEACHER_ID
            )
        )
    op.execute(
        sa.text(
            """
            insert into class_memberships
                (id, school_id, class_id, user_id, membership_role, created_at)
            values
                (:id, :school_id, :class_id, :user_id, 'STUDENT', now())
            on conflict (class_id, user_id, membership_role) do nothing
            """
        ).bindparams(
            id=P5A_STUDENT_MEMBERSHIP_ID,
            school_id=SCHOOL_ID,
            class_id=P5A_ID,
            user_id=STUDENT_ID,
        )
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_class_memberships_user_id"), table_name="class_memberships")
    op.drop_index(op.f("ix_class_memberships_school_id"), table_name="class_memberships")
    op.drop_index(op.f("ix_class_memberships_membership_role"), table_name="class_memberships")
    op.drop_index(op.f("ix_class_memberships_class_id"), table_name="class_memberships")
    op.drop_table("class_memberships")
    op.drop_index(op.f("ix_student_profiles_user_id"), table_name="student_profiles")
    op.drop_index(op.f("ix_student_profiles_student_number"), table_name="student_profiles")
    op.drop_index(op.f("ix_student_profiles_school_id"), table_name="student_profiles")
    op.drop_index(op.f("ix_student_profiles_level"), table_name="student_profiles")
    op.drop_table("student_profiles")
    op.drop_index(op.f("ix_teacher_profiles_user_id"), table_name="teacher_profiles")
    op.drop_index(op.f("ix_teacher_profiles_school_id"), table_name="teacher_profiles")
    op.drop_table("teacher_profiles")
    op.drop_index(op.f("ix_classes_school_id"), table_name="classes")
    op.drop_index(op.f("ix_classes_level"), table_name="classes")
    op.drop_table("classes")
