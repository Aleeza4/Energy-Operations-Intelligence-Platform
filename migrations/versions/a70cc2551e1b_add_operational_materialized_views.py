"""Add operational materialized views for EOIP.

Revision ID: a70cc2551e1b
Revises: a5210905c5be
Create Date: 2026-08-15
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a70cc2551e1b"
down_revision: str | Sequence[str] | None = "a5210905c5be"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create EOIP operational materialized views and indexes."""

    op.execute(sa.text("""
            CREATE MATERIALIZED VIEW mv_plant_operational_summary AS
            SELECT
                p.plant_id,
                p.plant_name,
                p.region,
                p.status AS plant_status,
                p.dc_capacity_mw,
                p.ac_capacity_mw,
                COUNT(DISTINCT e.equipment_id) AS equipment_count,
                COUNT(DISTINCT e.equipment_id)
                    FILTER (
                        WHERE e.status = 'operational'
                    ) AS operational_equipment_count,
                COUNT(DISTINCT o.event_id)
                    FILTER (
                        WHERE o.event_type = 'alarm'
                    ) AS open_alarm_count,
                COUNT(DISTINCT o.event_id)
                    FILTER (
                        WHERE o.event_type = 'incident'
                    ) AS open_incident_count,
                COUNT(DISTINCT o.event_id)
                    FILTER (
                        WHERE o.event_type = 'work_order'
                    ) AS open_work_order_count,
                COUNT(DISTINCT o.event_id) AS total_open_event_count
            FROM plants AS p
            LEFT JOIN equipment AS e
                ON e.plant_id = p.plant_id
            LEFT JOIN vw_open_operational_events AS o
                ON o.plant_id = p.plant_id
            GROUP BY
                p.plant_id,
                p.plant_name,
                p.region,
                p.status,
                p.dc_capacity_mw,
                p.ac_capacity_mw;
            """))

    op.execute(sa.text("""
            CREATE UNIQUE INDEX
                ux_mv_plant_operational_summary_plant_id
            ON mv_plant_operational_summary (plant_id);
            """))

    op.execute(sa.text("""
            CREATE INDEX
                ix_mv_plant_operational_summary_status
            ON mv_plant_operational_summary (plant_status);
            """))

    op.execute(sa.text("""
            CREATE MATERIALIZED VIEW mv_equipment_operational_summary AS
            SELECT
                e.plant_id,
                e.equipment_id,
                e.equipment_name,
                e.equipment_type,
                e.status AS equipment_status,
                e.rated_power_kw,
                COUNT(DISTINCT o.event_id)
                    FILTER (
                        WHERE o.event_type = 'alarm'
                    ) AS open_alarm_count,
                COUNT(DISTINCT o.event_id)
                    FILTER (
                        WHERE o.event_type = 'incident'
                    ) AS open_incident_count,
                COUNT(DISTINCT o.event_id)
                    FILTER (
                        WHERE o.event_type = 'work_order'
                    ) AS open_work_order_count,
                COUNT(DISTINCT o.event_id) AS total_open_event_count
            FROM equipment AS e
            LEFT JOIN vw_open_operational_events AS o
                ON o.plant_id = e.plant_id
                AND o.equipment_id = e.equipment_id
            GROUP BY
                e.plant_id,
                e.equipment_id,
                e.equipment_name,
                e.equipment_type,
                e.status,
                e.rated_power_kw;
            """))

    op.execute(sa.text("""
            CREATE UNIQUE INDEX
                ux_mv_equipment_operational_summary_equipment_id
            ON mv_equipment_operational_summary (equipment_id);
            """))

    op.execute(sa.text("""
            CREATE INDEX
                ix_mv_equipment_operational_summary_plant_id
            ON mv_equipment_operational_summary (plant_id);
            """))

    op.execute(sa.text("""
            CREATE INDEX
                ix_mv_equipment_operational_summary_status
            ON mv_equipment_operational_summary (equipment_status);
            """))


def downgrade() -> None:
    """Drop EOIP operational materialized views."""

    op.execute(sa.text("""
            DROP MATERIALIZED VIEW
            IF EXISTS mv_equipment_operational_summary;
            """))

    op.execute(sa.text("""
            DROP MATERIALIZED VIEW
            IF EXISTS mv_plant_operational_summary;
            """))
