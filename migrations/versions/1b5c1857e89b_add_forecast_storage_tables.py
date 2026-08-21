"""Add forecast storage tables.

Revision ID: 1b5c1857e89b
Revises: a70cc2551e1b
Create Date: 2026-08-18 13:48:02.954522
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "1b5c1857e89b"
down_revision: str | None = "a70cc2551e1b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create forecast storage tables."""
    op.create_table(
        "forecast_runs",
        sa.Column(
            "forecast_id",
            sa.String(length=36),
            nullable=False,
        ),
        sa.Column(
            "model_name",
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
        sa.PrimaryKeyConstraint(
            "forecast_id",
            name="pk_forecast_runs",
        ),
        sa.CheckConstraint(
            "row_count > 0",
            name="ck_forecast_runs_row_count_positive",
        ),
    )

    op.create_table(
        "forecast_values",
        sa.Column(
            "forecast_id",
            sa.String(length=36),
            nullable=False,
        ),
        sa.Column(
            "timestamp",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "prediction",
            sa.Float(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["forecast_id"],
            ["forecast_runs.forecast_id"],
            name="fk_forecast_values_forecast_id_forecast_runs",
            onupdate="CASCADE",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "forecast_id",
            "timestamp",
            name="pk_forecast_values",
        ),
    )

    op.create_index(
        "ix_forecast_runs_generated_at",
        "forecast_runs",
        ["generated_at"],
        unique=False,
    )

    op.create_index(
        "ix_forecast_values_forecast_id",
        "forecast_values",
        ["forecast_id"],
        unique=False,
    )

    op.create_index(
        "ix_forecast_values_timestamp",
        "forecast_values",
        ["timestamp"],
        unique=False,
    )


def downgrade() -> None:
    """Drop forecast storage tables."""
    op.drop_index(
        "ix_forecast_values_timestamp",
        table_name="forecast_values",
    )

    op.drop_index(
        "ix_forecast_values_forecast_id",
        table_name="forecast_values",
    )

    op.drop_index(
        "ix_forecast_runs_generated_at",
        table_name="forecast_runs",
    )

    op.drop_table("forecast_values")
    op.drop_table("forecast_runs")