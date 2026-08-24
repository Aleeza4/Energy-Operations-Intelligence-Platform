"""Add TimescaleDB continuous aggregates for EOIP time-series analytics.

Revision ID: c21b87a1d3cf
Revises: 8e608c963990
Create Date: 2026-08-15
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "c21b87a1d3cf"
down_revision: str | Sequence[str] | None = "8e608c963990"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCADA_HOURLY_VIEW = "scada_hourly"
WEATHER_HOURLY_VIEW = "weather_hourly"


def upgrade() -> None:
    """Create hourly SCADA and weather continuous aggregates."""

    op.execute(sa.text("""
            CREATE MATERIALIZED VIEW scada_hourly
            WITH (timescaledb.continuous) AS
            SELECT
                time_bucket(
                    INTERVAL '1 hour',
                    "timestamp"
                ) AS bucket,
                plant_id,
                equipment_id,
                COUNT(*) AS sample_count,
                AVG(active_power_kw) AS avg_active_power_kw,
                MAX(active_power_kw) AS max_active_power_kw,
                MIN(active_power_kw) AS min_active_power_kw,
                SUM(interval_energy_kwh) AS total_energy_kwh,
                AVG(dc_voltage_v) AS avg_dc_voltage_v,
                AVG(dc_current_a) AS avg_dc_current_a,
                AVG(ac_voltage_v) AS avg_ac_voltage_v,
                AVG(ac_current_a) AS avg_ac_current_a,
                AVG(frequency_hz) AS avg_frequency_hz,
                AVG(power_factor) AS avg_power_factor,
                COUNT(*) FILTER (
                    WHERE equipment_available IS TRUE
                ) AS equipment_available_samples,
                COUNT(*) FILTER (
                    WHERE grid_available IS TRUE
                ) AS grid_available_samples
            FROM scada_observations
            GROUP BY
                bucket,
                plant_id,
                equipment_id
            WITH NO DATA;
            """))

    op.execute(sa.text("""
            CREATE MATERIALIZED VIEW weather_hourly
            WITH (timescaledb.continuous) AS
            SELECT
                time_bucket(
                    INTERVAL '1 hour',
                    "timestamp"
                ) AS bucket,
                plant_id,
                weather_station_id,
                COUNT(*) AS sample_count,
                AVG(ghi_wm2) AS avg_ghi_wm2,
                MAX(ghi_wm2) AS max_ghi_wm2,
                AVG(dni_wm2) AS avg_dni_wm2,
                MAX(dni_wm2) AS max_dni_wm2,
                AVG(dhi_wm2) AS avg_dhi_wm2,
                AVG(
                    ambient_temperature_c
                ) AS avg_ambient_temperature_c,
                MIN(
                    ambient_temperature_c
                ) AS min_ambient_temperature_c,
                MAX(
                    ambient_temperature_c
                ) AS max_ambient_temperature_c,
                AVG(
                    module_temperature_c
                ) AS avg_module_temperature_c,
                MAX(
                    module_temperature_c
                ) AS max_module_temperature_c,
                AVG(wind_speed_ms) AS avg_wind_speed_ms,
                MAX(wind_speed_ms) AS max_wind_speed_ms,
                AVG(
                    relative_humidity_pct
                ) AS avg_relative_humidity_pct
            FROM weather_observations
            GROUP BY
                bucket,
                plant_id,
                weather_station_id
            WITH NO DATA;
            """))

    op.execute(sa.text("""
            SELECT add_continuous_aggregate_policy(
                'scada_hourly',
                start_offset => INTERVAL '30 days',
                end_offset => INTERVAL '1 hour',
                schedule_interval => INTERVAL '30 minutes'
            );
            """))

    op.execute(sa.text("""
            SELECT add_continuous_aggregate_policy(
                'weather_hourly',
                start_offset => INTERVAL '30 days',
                end_offset => INTERVAL '1 hour',
                schedule_interval => INTERVAL '30 minutes'
            );
            """))


def downgrade() -> None:
    """Remove EOIP hourly continuous aggregates and their policies."""

    op.execute(sa.text("""
            SELECT remove_continuous_aggregate_policy(
                'scada_hourly',
                if_exists => TRUE
            );
            """))

    op.execute(sa.text("""
            SELECT remove_continuous_aggregate_policy(
                'weather_hourly',
                if_exists => TRUE
            );
            """))

    op.execute(sa.text("""
            DROP MATERIALIZED VIEW IF EXISTS weather_hourly;
            """))

    op.execute(sa.text("""
            DROP MATERIALIZED VIEW IF EXISTS scada_hourly;
            """))
