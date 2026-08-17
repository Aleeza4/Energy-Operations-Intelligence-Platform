"""Add operational database views for EOIP.

Revision ID: a5210905c5be
Revises: c21b87a1d3cf
Create Date: 2026-08-15
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a5210905c5be"
down_revision: str | Sequence[str] | None = "c21b87a1d3cf"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create EOIP operational reporting views."""

    op.execute(sa.text("""
            CREATE OR REPLACE VIEW vw_plant_equipment_status AS
            SELECT
                p.plant_id,
                p.plant_name,
                p.region,
                p.status AS plant_status,
                p.dc_capacity_mw,
                p.ac_capacity_mw,
                p.timezone_name,
                e.equipment_id,
                e.equipment_name,
                e.equipment_type,
                e.manufacturer,
                e.model_number,
                e.serial_number,
                e.rated_power_kw,
                e.status AS equipment_status,
                e.commissioning_date AS equipment_commissioning_date
            FROM plants AS p
            LEFT JOIN equipment AS e
                ON e.plant_id = p.plant_id;
            """))

    op.execute(sa.text("""
            CREATE OR REPLACE VIEW vw_alarm_incident_status AS
            SELECT
                a.alarm_id,
                a.plant_id,
                a.equipment_id,
                a.alarm_code,
                a.alarm_name,
                a.category AS alarm_category,
                a.severity AS alarm_severity,
                a.raised_at,
                a.status AS alarm_status,
                a.acknowledged_at,
                a.cleared_at,
                a.message AS alarm_message,
                i.incident_id,
                i.incident_name,
                i.category AS incident_category,
                i.severity AS incident_severity,
                i.occurred_at,
                i.status AS incident_status,
                i.detected_at,
                i.resolved_at,
                i.root_cause,
                i.description AS incident_description
            FROM alarms AS a
            LEFT JOIN incidents AS i
                ON i.linked_alarm_id = a.alarm_id;
            """))

    op.execute(sa.text("""
            CREATE OR REPLACE VIEW vw_incident_work_order_status AS
            SELECT
                i.incident_id,
                i.plant_id,
                i.equipment_id,
                i.incident_name,
                i.category AS incident_category,
                i.severity AS incident_severity,
                i.occurred_at,
                i.status AS incident_status,
                i.detected_at,
                i.resolved_at,
                i.root_cause,
                w.work_order_id,
                w.work_order_name,
                w.work_order_type,
                w.priority,
                w.status AS work_order_status,
                w.assigned_team,
                w.scheduled_at,
                w.started_at,
                w.completed_at,
                w.cancelled_at,
                w.estimated_labor_hours,
                w.actual_labor_hours,
                w.estimated_cost,
                w.actual_cost,
                w.description AS work_order_description,
                w.completion_notes
            FROM incidents AS i
            LEFT JOIN work_orders AS w
                ON w.linked_incident_id = i.incident_id;
            """))

    op.execute(sa.text("""
            CREATE OR REPLACE VIEW vw_open_operational_events AS
            SELECT
                a.plant_id,
                a.equipment_id,
                'alarm'::text AS event_type,
                a.alarm_id AS event_id,
                a.alarm_name AS event_name,
                a.severity,
                a.status,
                a.raised_at AS event_started_at,
                a.cleared_at AS event_closed_at
            FROM alarms AS a
            WHERE a.status <> 'cleared'

            UNION ALL

            SELECT
                i.plant_id,
                i.equipment_id,
                'incident'::text AS event_type,
                i.incident_id AS event_id,
                i.incident_name AS event_name,
                i.severity,
                i.status,
                i.occurred_at AS event_started_at,
                i.resolved_at AS event_closed_at
            FROM incidents AS i
            WHERE i.status <> 'resolved'

            UNION ALL

            SELECT
                w.plant_id,
                w.equipment_id,
                'work_order'::text AS event_type,
                w.work_order_id AS event_id,
                w.work_order_name AS event_name,
                w.priority AS severity,
                w.status,
                w.created_at AS event_started_at,
                COALESCE(w.completed_at, w.cancelled_at) AS event_closed_at
            FROM work_orders AS w
            WHERE w.status NOT IN ('completed', 'cancelled');
            """))


def downgrade() -> None:
    """Drop EOIP operational reporting views."""

    op.execute(sa.text("""
            DROP VIEW IF EXISTS vw_open_operational_events;
            """))

    op.execute(sa.text("""
            DROP VIEW IF EXISTS vw_incident_work_order_status;
            """))

    op.execute(sa.text("""
            DROP VIEW IF EXISTS vw_alarm_incident_status;
            """))

    op.execute(sa.text("""
            DROP VIEW IF EXISTS vw_plant_equipment_status;
            """))
