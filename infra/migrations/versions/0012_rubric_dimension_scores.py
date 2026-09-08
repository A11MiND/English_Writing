"""Score every rubric dimension instead of a fixed Content/Language/Organisation trio.

Rubrics let a school name its own dimensions, but marking could only ever produce
three scores, so a fourth dimension was accepted at creation and then silently
never marked. Scores and per-dimension feedback move into one JSONB list.
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0012_rubric_dimension_scores"
down_revision: str | None = "0011_media_subscription"
branch_labels = None
depends_on = None


def upgrade() -> None:
    for table in ("marking_results", "teacher_reviews"):
        op.add_column(
            table,
            sa.Column(
                "dimension_scores",
                postgresql.JSONB(astext_type=sa.Text()),
                nullable=False,
                server_default=sa.text("'[]'::jsonb"),
            ),
        )

    # Carry the existing trio over so released feedback keeps its scores.
    op.execute(
        """
        UPDATE marking_results SET dimension_scores = (
          SELECT COALESCE(jsonb_agg(entry ORDER BY ord), '[]'::jsonb)
          FROM (
            VALUES
              (1, 'Content', content_score, content_feedback),
              (2, 'Language', language_score, language_feedback),
              (3, 'Organisation', organisation_score, organisation_feedback)
          ) AS source(ord, name, score, feedback),
          LATERAL (
            SELECT jsonb_build_object(
              'name', source.name,
              'score', source.score,
              'max_score', NULL::int,
              'feedback', source.feedback
            ) AS entry
          ) AS built
          WHERE source.score IS NOT NULL
        )
        """
    )
    op.execute(
        """
        UPDATE teacher_reviews SET dimension_scores = (
          SELECT COALESCE(jsonb_agg(entry ORDER BY ord), '[]'::jsonb)
          FROM (
            VALUES
              (1, 'Content', content_score),
              (2, 'Language', language_score),
              (3, 'Organisation', organisation_score)
          ) AS source(ord, name, score),
          LATERAL (
            SELECT jsonb_build_object(
              'name', source.name,
              'score', source.score,
              'max_score', NULL::int
            ) AS entry
          ) AS built
          WHERE source.score IS NOT NULL
        )
        """
    )

    for column in ("content_score", "language_score", "organisation_score",
                   "content_feedback", "language_feedback", "organisation_feedback"):
        op.drop_column("marking_results", column)
    for column in ("content_score", "language_score", "organisation_score"):
        op.drop_column("teacher_reviews", column)


def downgrade() -> None:
    for column in ("content_score", "language_score", "organisation_score"):
        op.add_column("teacher_reviews", sa.Column(column, sa.Integer(), nullable=True))
    for column in ("content_score", "language_score", "organisation_score"):
        op.add_column("marking_results", sa.Column(column, sa.Integer(), nullable=True))
    for column in ("content_feedback", "language_feedback", "organisation_feedback"):
        op.add_column("marking_results", sa.Column(column, sa.Text(), nullable=True))

    for table in ("marking_results", "teacher_reviews"):
        for column, name in (
            ("content_score", "Content"),
            ("language_score", "Language"),
            ("organisation_score", "Organisation"),
        ):
            op.execute(
                f"""
                UPDATE {table} SET {column} = (
                  SELECT (entry ->> 'score')::int FROM jsonb_array_elements(dimension_scores) AS entry
                  WHERE entry ->> 'name' = '{name}' LIMIT 1
                )
                """
            )
    for column, name in (
        ("content_feedback", "Content"),
        ("language_feedback", "Language"),
        ("organisation_feedback", "Organisation"),
    ):
        op.execute(
            f"""
            UPDATE marking_results SET {column} = (
              SELECT entry ->> 'feedback' FROM jsonb_array_elements(dimension_scores) AS entry
              WHERE entry ->> 'name' = '{name}' LIMIT 1
            )
            """
        )

    for table in ("marking_results", "teacher_reviews"):
        op.drop_column(table, "dimension_scores")
