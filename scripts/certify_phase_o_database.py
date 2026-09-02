"""Run reproducible Phase O database checks against an isolated migrated database."""

from __future__ import annotations

import argparse
import json
import os
import time
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from eoip.database.bulk.scada import REQUIRED_SCADA_COLUMNS, SCADABulkLoader
from eoip.database.bulk.weather import REQUIRED_WEATHER_COLUMNS, WeatherBulkLoader
from eoip.database.models import EquipmentORM, PlantORM
from eoip.synthetic.config import (
    GenerationConfig,
    GenerationProfile,
    PortfolioConfig,
    TimeRangeConfig,
)
from eoip.synthetic.generator import SyntheticDatasetGenerator


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("artifacts/evaluation/phase_o/database_runtime_evidence.json"),
    )
    return parser.parse_args()


def _timed_scalar(session: Session, statement: str) -> tuple[object, float]:
    started = time.perf_counter()
    value = session.execute(text(statement)).scalar()
    return value, (time.perf_counter() - started) * 1_000


def _bulk_record(item: object, required_columns: set[str]) -> dict[str, object]:
    record = item.to_record()  # type: ignore[attr-defined]
    record["timestamp"] = item.timestamp  # type: ignore[attr-defined]
    return {column: record[column] for column in required_columns}


def main() -> int:
    args = _arguments()
    database_url = os.getenv("EOIP_DATABASE_URL")
    if not database_url:
        raise RuntimeError("EOIP_DATABASE_URL is required")

    engine = create_engine(database_url, pool_pre_ping=True, future=True)
    configuration = GenerationConfig(
        profile_name=GenerationProfile.UNIT,
        seed=20_260_828,
        time=TimeRangeConfig(
            datetime(2025, 1, 1, tzinfo=UTC),
            datetime(2025, 1, 1, 6, tzinfo=UTC),
        ),
        portfolio=PortfolioConfig(
            plant_count=1,
            aggregate_ac_capacity_min_mw=20,
            aggregate_ac_capacity_max_mw=100,
            inverter_count_min=2,
            inverter_count_max=2,
        ),
    )
    generator = SyntheticDatasetGenerator(configuration)
    generation_started = time.perf_counter()
    dataset = generator.generate()
    generation_seconds = time.perf_counter() - generation_started

    source_counts = {
        "plants": len(dataset.plants),
        "equipment": len(dataset.equipment),
        "scada_observations": len(dataset.inverter_scada),
        "weather_observations": len(dataset.weather),
    }

    load_started = time.perf_counter()
    with Session(engine) as session:
        session.add_all(PlantORM.from_domain(item) for item in dataset.plants)
        session.flush()
        session.add_all(EquipmentORM.from_domain(item) for item in dataset.equipment)
        session.flush()
        scada_written = SCADABulkLoader(session).load(
            _bulk_record(item, REQUIRED_SCADA_COLUMNS)
            for item in dataset.inverter_scada
        )
        weather_written = WeatherBulkLoader(session).load(
            _bulk_record(item, REQUIRED_WEATHER_COLUMNS) for item in dataset.weather
        )
        session.commit()
    load_seconds = time.perf_counter() - load_started

    duplicate_rejected = False
    with Session(engine) as session:
        try:
            session.add(PlantORM.from_domain(dataset.plants[0]))
            session.commit()
        except IntegrityError:
            session.rollback()
            duplicate_rejected = True

    inspector = inspect(engine)
    tables = sorted(inspector.get_table_names(schema="public"))
    with Session(engine) as session:
        database_counts = {
            table: session.execute(text(f'SELECT COUNT(*) FROM "{table}"')).scalar_one()
            for table in source_counts
        }
        postgresql_version = session.execute(text("SHOW server_version")).scalar_one()
        timescale_version = session.execute(
            text("SELECT extversion FROM pg_extension " "WHERE extname = 'timescaledb'")
        ).scalar_one_or_none()
        alembic_revision = session.execute(
            text("SELECT version_num FROM alembic_version")
        ).scalar_one()
        hypertables = [
            dict(row._mapping)
            for row in session.execute(
                text(
                    "SELECT hypertable_name, num_dimensions, num_chunks "
                    "FROM timescaledb_information.hypertables "
                    "ORDER BY hypertable_name"
                )
            )
        ]
        continuous_aggregates = [
            dict(row._mapping)
            for row in session.execute(
                text(
                    "SELECT view_name, materialized_only "
                    "FROM timescaledb_information.continuous_aggregates "
                    "ORDER BY view_name"
                )
            )
        ]
        index_count = session.execute(
            text("SELECT COUNT(*) FROM pg_indexes " "WHERE schemaname = 'public'")
        ).scalar_one()
        latest_timestamp, latest_ms = _timed_scalar(
            session, "SELECT MAX(timestamp) FROM scada_observations"
        )
        plant_summary_count, summary_ms = _timed_scalar(
            session,
            "SELECT COUNT(*) FROM scada_observations " "WHERE plant_id = 'PLANT-001'",
        )
        explain = [
            row[0]
            for row in session.execute(
                text(
                    "EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT) "
                    "SELECT * FROM scada_observations "
                    "WHERE equipment_id = 'INV-0001' "
                    "ORDER BY timestamp DESC LIMIT 96"
                )
            )
        ]

    total_rows = sum(database_counts.values())
    evidence = {
        "phase": "O",
        "classification": "REPRESENTATIVE_RUNTIME_VALIDATION",
        "configuration_fingerprint": configuration.fingerprint(),
        "seed": configuration.seed,
        "database_identity_redacted": True,
        "postgresql_version": postgresql_version,
        "timescaledb_version": timescale_version,
        "alembic_revision": alembic_revision,
        "tables": tables,
        "source_counts": source_counts,
        "database_counts": database_counts,
        "counts_match": source_counts == database_counts,
        "load": {
            "generation_seconds": generation_seconds,
            "load_seconds": load_seconds,
            "rows_written": total_rows,
            "rows_per_second": total_rows / load_seconds,
            "scada_written": scada_written,
            "weather_written": weather_written,
            "duplicate_primary_key_rejected": duplicate_rejected,
        },
        "schema": {
            "public_index_count": index_count,
            "hypertables": hypertables,
            "continuous_aggregates": continuous_aggregates,
        },
        "queries": {
            "latest_scada_timestamp": str(latest_timestamp),
            "latest_timestamp_ms": latest_ms,
            "plant_scada_rows": plant_summary_count,
            "plant_summary_ms": summary_ms,
            "equipment_recent_explain_analyze": explain,
            "production_sla_defined": False,
        },
        "status": "PASS" if source_counts == database_counts else "FAIL",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(evidence, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(evidence, indent=2))
    engine.dispose()
    return 0 if evidence["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
