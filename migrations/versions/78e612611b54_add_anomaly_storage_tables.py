"""Add anomaly storage tables.

Revision ID: 78e612611b54
Revises: 1b5c1857e89b
Create Date: 2026-08-18 17:27:03.162822
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "78e612611b54"
down_revision: str | None = "1b5c1857e89b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create anomaly storage tables."""
    op.create_table(
        "anomaly_runs",
        sa.Column(
            "anomaly_run_id",
            sa.String(length=36),
            nullable=False,
        ),
        sa.Column(
            "detector_name",
            sa.String(length=255),
            nullable=False,
        ),
        sa.Column(
            "target_column",
            sa.String(length=255),
            nullable=False,
        ),
        sa.Column(
            "generated_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "row_count",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "anomaly_count",
            sa.Integer(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint(
            "anomaly_run_id",
            name="pk_anomaly_runs",
        ),
        sa.CheckConstraint(
            "row_count > 0",
            name="ck_anomaly_runs_row_count_positive",
        ),
        sa.CheckConstraint(
            "anomaly_count >= 0",
            name="ck_anomaly_runs_anomaly_count_non_negative",
        ),
        sa.CheckConstraint(
            "anomaly_count <= row_count",
            name="ck_anomaly_runs_anomaly_count_not_exceed_row_count",
        ),
    )

    op.create_table(
        "anomaly_values",
        sa.Column(
            "anomaly_run_id",
            sa.String(length=36),
            nullable=False,
        ),
        sa.Column(
            "timestamp",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "is_anomaly",
            sa.Boolean(),
            nullable=False,
        ),
        sa.Column(
            "score",
            sa.Float(),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(
            ["anomaly_run_id"],
            ["anomaly_runs.anomaly_run_id"],
            name=(
                "fk_anomaly_values_anomaly_run_id_"
                "anomaly_runs"
            ),
            onupdate="CASCADE",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "anomaly_run_id",
            "timestamp",
            name="pk_anomaly_values",
        ),
    )

    op.create_index(
        "ix_anomaly_runs_generated_at",
        "anomaly_runs",
        ["generated_at"],
        unique=False,
    )

    op.create_index(
        "ix_anomaly_values_anomaly_run_id",
        "anomaly_values",
        ["anomaly_run_id"],
        unique=False,
    )

    op.create_index(
        "ix_anomaly_values_timestamp",
        "anomaly_values",
        ["timestamp"],
        unique=False,
    )

    op.create_index(
        "ix_anomaly_values_is_anomaly",
        "anomaly_values",
        ["is_anomaly"],
        unique=False,
    )


def downgrade() -> None:
    """Drop anomaly storage tables."""
    op.drop_index(
        "ix_anomaly_values_is_anomaly",
        table_name="anomaly_values",
    )

    op.drop_index(
        "ix_anomaly_values_timestamp",
        table_name="anomaly_values",
    )

    op.drop_index(
        "ix_anomaly_values_anomaly_run_id",
        table_name="anomaly_values",
    )

    op.drop_index(
        "ix_anomaly_runs_generated_at",
        table_name="anomaly_runs",
    )

    op.drop_table("anomaly_values")
    op.drop_table("anomaly_runs")