"""Convert EOIP time-series tables to TimescaleDB hypertables.

Revision ID: 8e608c963990
Revises: a1c9cbd16e30
Create Date: 2026-08-15
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from psycopg2.errors import FeatureNotSupported, UndefinedFile, UndefinedFunction

revision: str = "8e608c963990"
down_revision: str | Sequence[str] | None = "a1c9cbd16e30"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Convert SCADA and weather tables to TimescaleDB hypertables."""
    try:
        with op.get_bind().begin_nested():
            op.execute(sa.text("""
                CREATE EXTENSION IF NOT EXISTS timescaledb;
                """))
    except (FeatureNotSupported, UndefinedFile, sa.exc.DBAPIError) as error:
        if not isinstance(
            error, (FeatureNotSupported, UndefinedFile)
        ) and not isinstance(error.orig, (FeatureNotSupported, UndefinedFile)):
            raise
        print(
            "WARNING: TimescaleDB is not available in this environment; "
            "skipping hypertable conversion."
        )
        return

    try:
        with op.get_bind().begin_nested():
            op.execute(sa.text("""
                SELECT create_hypertable(
                    'scada_observations',
                    by_range('timestamp', INTERVAL '1 day'),
                    if_not_exists => TRUE,
                    migrate_data => TRUE
                );
                """))
    except (FeatureNotSupported, UndefinedFunction, sa.exc.DBAPIError) as error:
        if not isinstance(
            error, (FeatureNotSupported, UndefinedFunction)
        ) and not isinstance(error.orig, (FeatureNotSupported, UndefinedFunction)):
            raise
        print(
            "WARNING: TimescaleDB hypertables are not supported; "
            "skipping scada_observations conversion."
        )

    try:
        with op.get_bind().begin_nested():
            op.execute(sa.text("""
                SELECT create_hypertable(
                    'weather_observations',
                    by_range('timestamp', INTERVAL '1 day'),
                    if_not_exists => TRUE,
                    migrate_data => TRUE
                );
                """))
    except (FeatureNotSupported, UndefinedFunction, sa.exc.DBAPIError) as error:
        if not isinstance(
            error, (FeatureNotSupported, UndefinedFunction)
        ) and not isinstance(error.orig, (FeatureNotSupported, UndefinedFunction)):
            raise
        print(
            "WARNING: TimescaleDB hypertables are not supported; "
            "skipping weather_observations conversion."
        )


def downgrade() -> None:
    """Leave hypertables intact during downgrade.

    TimescaleDB does not provide a simple in-place operation that converts
    a hypertable back into an ordinary PostgreSQL table while preserving
    all schema and data semantics. Reversing this migration therefore
    requires an explicit data-migration procedure rather than an automatic
    destructive downgrade.
    """
    raise RuntimeError(
        "Downgrading EOIP hypertables requires an explicit "
        "hypertable-to-regular-table data migration."
    )
