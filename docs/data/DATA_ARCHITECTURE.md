# EOIP data architecture

## Data layers

EOIP has three related but non-identical data representations:

| Layer | Source of truth | Purpose | Evidence classification |
|---|---|---|---|
| Synthetic domain | `src/eoip/synthetic/models/` and generators | Rich deterministic plants, telemetry, weather, operations, tariff, budget, and truth data | `REPRESENTATIVE_SYNTHETIC` |
| Database | `src/eoip/database/models/` and Alembic | Normalized relational/time-series persistence architecture | `CONFIGURED`; runtime `NOT VERIFIED` |
| Application | `src/eoip/app/data_access.py` | Small deterministic frames for the Streamlit experience | `REPRESENTATIVE_SYNTHETIC` |

These schemas intentionally differ. The application frames are not ORM rows,
and synthetic models are not proof that corresponding database tables are
populated in a deployed environment.

## Generation and provenance

`SyntheticDatasetGenerator` uses a versioned configuration and deterministic
random streams. Phase L uses two plants, 15-minute observations, seed
`20260827`, and UTC range `[2025-01-01, 2025-03-02)`. Ground-truth events are
scheduled independently before detector execution. Metadata includes a run ID,
schema/generator versions, configuration fingerprint, and counts.

## ETL contracts

The ETL package separates ingestion, cleaning, transformation, validation,
incremental state, retry, audit, and lineage. Implementations and tests exist,
but Phase L did not execute a representative database ETL run. Production
success rate, failed-batch recovery, and completion time therefore remain
`NOT VERIFIED` or `PARTIAL`.

## Persistence

The database layer uses SQLAlchemy repositories/services and PostgreSQL-oriented
models. Alembic adds TimescaleDB hypertables and continuous aggregates. All
operational timestamps are intended to be timezone-aware UTC. Database tests
require `EOIP_DATABASE_URL`; absent configuration causes explicit skips.

## Analytical datasets

- Forecasting builds time-series datasets and uses expanding-window backtests.
- Anomaly evaluation aligns predictions with independently generated truth.
- Maintenance labels include failures strictly after each observation within a
  24-hour horizon.
- Equipment health combines named degradation contributions; it is a score,
  not a calibrated probability or confidence interval.
- Application data-quality checks evaluate deterministic frames, whereas Phase
  L quality metrics evaluate the representative inverter telemetry population.

## Relationships and discrepancies

| Relationship | Supported meaning |
|---|---|
| Plant to equipment | Explicit ownership/foreign key in domain and ORM models |
| Plant/equipment to telemetry | Attribution by identifiers and timestamps |
| Alarm to incident | Optional explicit linked alarm ID |
| Incident to work order | Optional explicit linked incident ID |
| Recommendation to evidence | Typed reference with explicit relationship strength |
| Same plant/equipment IDs | May justify `RELATED_TO`; never automatic causality |

Application records use display names such as `Solar Plant D`, while synthetic
and database contracts commonly use stable IDs such as `PLANT-001`. Forecast,
anomaly, maintenance, and recommendation persistence schemas are also exposed
through analytical/provider contracts rather than being identical to the
application frames. Consumers must use the relevant layer's schema.

See the [data dictionary](DATA_DICTIONARY.md) and
[system architecture](../architecture/SYSTEM_ARCHITECTURE.md).
