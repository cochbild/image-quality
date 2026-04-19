"""initial schema — scans, assessments, category scores, settings

Revision ID: 20260419_0001
Revises:
Create Date: 2026-04-19

Captures the schema that earlier releases stood up through
`Base.metadata.create_all`. Existing deployments should run
`alembic stamp 20260419_0001` once after upgrading to mark their
already-created tables as migrated; fresh deployments just run
`alembic upgrade head`.
"""
from alembic import op
import sqlalchemy as sa

revision = "20260419_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "iqa_scans",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("input_dir", sa.String(), nullable=False),
        sa.Column("output_dir", sa.String(), nullable=False),
        sa.Column("reject_dir", sa.String(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("total_images", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("passed_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("failed_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="running"),
    )
    op.create_index("ix_iqa_scans_id", "iqa_scans", ["id"])

    op.create_table(
        "iqa_assessments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "scan_id",
            sa.Integer(),
            sa.ForeignKey("iqa_scans.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("filename", sa.String(), nullable=False),
        sa.Column("file_path", sa.String(), nullable=False),
        sa.Column("destination_path", sa.String(), nullable=True),
        sa.Column("passed", sa.Boolean(), nullable=True),
        sa.Column("triage_score", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_iqa_assessments_id", "iqa_assessments", ["id"])

    op.create_table(
        "iqa_category_scores",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "assessment_id",
            sa.Integer(),
            sa.ForeignKey("iqa_assessments.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("category", sa.String(length=30), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("reasoning", sa.Text(), nullable=True),
        sa.Column("was_deep_dive", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.CheckConstraint("score >= 1 AND score <= 10", name="ck_score_range"),
    )
    op.create_index("ix_iqa_category_scores_id", "iqa_category_scores", ["id"])

    op.create_table(
        "iqa_settings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("key", sa.String(length=100), nullable=False, unique=True),
        sa.Column("value", sa.Text(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
        ),
    )
    op.create_index("ix_iqa_settings_id", "iqa_settings", ["id"])
    op.create_index("ix_iqa_settings_key", "iqa_settings", ["key"])


def downgrade() -> None:
    op.drop_index("ix_iqa_settings_key", table_name="iqa_settings")
    op.drop_index("ix_iqa_settings_id", table_name="iqa_settings")
    op.drop_table("iqa_settings")
    op.drop_index("ix_iqa_category_scores_id", table_name="iqa_category_scores")
    op.drop_table("iqa_category_scores")
    op.drop_index("ix_iqa_assessments_id", table_name="iqa_assessments")
    op.drop_table("iqa_assessments")
    op.drop_index("ix_iqa_scans_id", table_name="iqa_scans")
    op.drop_table("iqa_scans")
