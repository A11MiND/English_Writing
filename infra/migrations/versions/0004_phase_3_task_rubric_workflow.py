"""phase 3 task rubric workflow

Revision ID: 0004_phase_3_tasks
Revises: 0003_phase_2_core_school_data
Create Date: 2026-06-27
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "0004_phase_3_tasks"
down_revision: str | None = "0003_phase_2_core_school_data"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHOOL_ID = "11111111-1111-4111-8111-111111111111"
TEACHER_ID = "44444444-4444-4444-8444-444444444444"
P5A_ID = "88888888-8888-4888-8888-888888888885"
RUBRIC_ID = "cccccccc-cccc-4ccc-8ccc-ccccccccccc1"
PRACTICE_TASK_ID = "dddddddd-dddd-4ddd-8ddd-dddddddddd01"
EXAM_TASK_ID = "dddddddd-dddd-4ddd-8ddd-dddddddddd02"
PRACTICE_ASSIGNMENT_ID = "eeeeeeee-eeee-4eee-8eee-eeeeeeeeee01"
EXAM_ASSIGNMENT_ID = "eeeeeeee-eeee-4eee-8eee-eeeeeeeeee02"


def upgrade() -> None:
    op.create_table(
        "rubrics",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("school_id", sa.String(length=36), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("level", sa.String(length=16), nullable=False),
        sa.Column("total_score", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_by", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["school_id"], ["schools.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_rubrics_created_by"), "rubrics", ["created_by"])
    op.create_index(op.f("ix_rubrics_level"), "rubrics", ["level"])
    op.create_index(op.f("ix_rubrics_school_id"), "rubrics", ["school_id"])
    op.create_index(op.f("ix_rubrics_status"), "rubrics", ["status"])

    op.create_table(
        "rubric_dimensions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("school_id", sa.String(length=36), nullable=False),
        sa.Column("rubric_id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=64), nullable=False),
        sa.Column("min_score", sa.Integer(), nullable=False),
        sa.Column("max_score", sa.Integer(), nullable=False),
        sa.Column("descriptor", sa.Text(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["rubric_id"], ["rubrics.id"]),
        sa.ForeignKeyConstraint(["school_id"], ["schools.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("rubric_id", "name", name="uq_rubric_dimensions_rubric_name"),
    )
    op.create_index(op.f("ix_rubric_dimensions_rubric_id"), "rubric_dimensions", ["rubric_id"])
    op.create_index(op.f("ix_rubric_dimensions_school_id"), "rubric_dimensions", ["school_id"])

    op.create_table(
        "writing_tasks",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("school_id", sa.String(length=36), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("level", sa.String(length=16), nullable=False),
        sa.Column("instruction", sa.Text(), nullable=False),
        sa.Column("genre", sa.String(length=64), nullable=True),
        sa.Column("mode", sa.String(length=32), nullable=False),
        sa.Column("word_minimum", sa.Integer(), nullable=True),
        sa.Column("word_maximum", sa.Integer(), nullable=True),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rubric_id", sa.String(length=36), nullable=False),
        sa.Column("created_by", sa.String(length=36), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("allow_late_submission", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["rubric_id"], ["rubrics.id"]),
        sa.ForeignKeyConstraint(["school_id"], ["schools.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_writing_tasks_created_by"), "writing_tasks", ["created_by"])
    op.create_index(op.f("ix_writing_tasks_level"), "writing_tasks", ["level"])
    op.create_index(op.f("ix_writing_tasks_mode"), "writing_tasks", ["mode"])
    op.create_index(op.f("ix_writing_tasks_rubric_id"), "writing_tasks", ["rubric_id"])
    op.create_index(op.f("ix_writing_tasks_school_id"), "writing_tasks", ["school_id"])
    op.create_index(op.f("ix_writing_tasks_status"), "writing_tasks", ["status"])

    op.create_table(
        "assignments",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("school_id", sa.String(length=36), nullable=False),
        sa.Column("task_id", sa.String(length=36), nullable=False),
        sa.Column("class_id", sa.String(length=36), nullable=False),
        sa.Column("assigned_by", sa.String(length=36), nullable=False),
        sa.Column("assigned_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["assigned_by"], ["users.id"]),
        sa.ForeignKeyConstraint(["class_id"], ["classes.id"]),
        sa.ForeignKeyConstraint(["school_id"], ["schools.id"]),
        sa.ForeignKeyConstraint(["task_id"], ["writing_tasks.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("task_id", "class_id", name="uq_assignments_task_class"),
    )
    op.create_index(op.f("ix_assignments_assigned_by"), "assignments", ["assigned_by"])
    op.create_index(op.f("ix_assignments_class_id"), "assignments", ["class_id"])
    op.create_index(op.f("ix_assignments_school_id"), "assignments", ["school_id"])
    op.create_index(op.f("ix_assignments_task_id"), "assignments", ["task_id"])

    op.execute(
        sa.text(
            """
            insert into rubrics
                (id, school_id, title, level, total_score, status, created_by, created_at, updated_at)
            values
                (:id, :school_id, 'WFJLP P5 Narrative Writing Rubric', 'P5', 15, 'ACTIVE', :teacher_id, now(), now())
            """
        ).bindparams(id=RUBRIC_ID, school_id=SCHOOL_ID, teacher_id=TEACHER_ID)
    )
    for dimension_id, name, descriptor, sort_order in [
        (
            "ffffffff-ffff-4fff-8fff-fffffffffff1",
            "Content",
            "Ideas are relevant, developed and appropriate for the writing task.",
            1,
        ),
        (
            "ffffffff-ffff-4fff-8fff-fffffffffff2",
            "Language",
            "Vocabulary, grammar and sentence structures support clear expression.",
            2,
        ),
        (
            "ffffffff-ffff-4fff-8fff-fffffffffff3",
            "Organisation",
            "Writing is logically sequenced with clear paragraphing and cohesion.",
            3,
        ),
    ]:
        op.execute(
            sa.text(
                """
                insert into rubric_dimensions
                    (id, school_id, rubric_id, name, min_score, max_score, descriptor, sort_order, created_at)
                values
                    (:id, :school_id, :rubric_id, :name, 0, 5, :descriptor, :sort_order, now())
                """
            ).bindparams(
                id=dimension_id,
                school_id=SCHOOL_ID,
                rubric_id=RUBRIC_ID,
                name=name,
                descriptor=descriptor,
                sort_order=sort_order,
            )
        )

    for task_id, title, mode in [
        (PRACTICE_TASK_ID, "A Memorable School Day", "PRACTICE"),
        (EXAM_TASK_ID, "A Helpful Classmate", "EXAM"),
    ]:
        op.execute(
            sa.text(
                """
                insert into writing_tasks
                    (
                        id, school_id, title, level, instruction, genre, mode, word_minimum,
                        word_maximum, due_at, rubric_id, created_by, status, allow_late_submission,
                        created_at, updated_at
                    )
                values
                    (
                        :id, :school_id, :title, 'P5',
                        'Write a complete story with a clear beginning, middle and ending. Use details to show what happened and how people felt.',
                        'Narrative', :mode, 120, 180, now() + interval '30 days', :rubric_id,
                        :teacher_id, 'PUBLISHED', false, now(), now()
                    )
                """
            ).bindparams(
                id=task_id,
                school_id=SCHOOL_ID,
                title=title,
                mode=mode,
                rubric_id=RUBRIC_ID,
                teacher_id=TEACHER_ID,
            )
        )

    for assignment_id, task_id in [
        (PRACTICE_ASSIGNMENT_ID, PRACTICE_TASK_ID),
        (EXAM_ASSIGNMENT_ID, EXAM_TASK_ID),
    ]:
        op.execute(
            sa.text(
                """
                insert into assignments
                    (id, school_id, task_id, class_id, assigned_by, assigned_at)
                values
                    (:id, :school_id, :task_id, :class_id, :teacher_id, now())
                """
            ).bindparams(
                id=assignment_id,
                school_id=SCHOOL_ID,
                task_id=task_id,
                class_id=P5A_ID,
                teacher_id=TEACHER_ID,
            )
        )


def downgrade() -> None:
    op.drop_index(op.f("ix_assignments_task_id"), table_name="assignments")
    op.drop_index(op.f("ix_assignments_school_id"), table_name="assignments")
    op.drop_index(op.f("ix_assignments_class_id"), table_name="assignments")
    op.drop_index(op.f("ix_assignments_assigned_by"), table_name="assignments")
    op.drop_table("assignments")
    op.drop_index(op.f("ix_writing_tasks_status"), table_name="writing_tasks")
    op.drop_index(op.f("ix_writing_tasks_school_id"), table_name="writing_tasks")
    op.drop_index(op.f("ix_writing_tasks_rubric_id"), table_name="writing_tasks")
    op.drop_index(op.f("ix_writing_tasks_mode"), table_name="writing_tasks")
    op.drop_index(op.f("ix_writing_tasks_level"), table_name="writing_tasks")
    op.drop_index(op.f("ix_writing_tasks_created_by"), table_name="writing_tasks")
    op.drop_table("writing_tasks")
    op.drop_index(op.f("ix_rubric_dimensions_school_id"), table_name="rubric_dimensions")
    op.drop_index(op.f("ix_rubric_dimensions_rubric_id"), table_name="rubric_dimensions")
    op.drop_table("rubric_dimensions")
    op.drop_index(op.f("ix_rubrics_status"), table_name="rubrics")
    op.drop_index(op.f("ix_rubrics_school_id"), table_name="rubrics")
    op.drop_index(op.f("ix_rubrics_level"), table_name="rubrics")
    op.drop_index(op.f("ix_rubrics_created_by"), table_name="rubrics")
    op.drop_table("rubrics")
