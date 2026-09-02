# EOIP portfolio case study

## Problem and objective

Renewable-energy operations data is commonly split across telemetry, weather,
alarms, incidents, maintenance, forecasts, and business systems. EOIP explores
how to build a coherent, testable platform that turns those sources into
operational context and governed decisions without overstating analytical or
commercial evidence.

The objective was an end-to-end engineering reference: typed data generation,
ETL controls, time-series persistence architecture, analytics/ML, APIs,
Streamlit workflows, empirical evaluation, and recommendation governance.

## My engineering approach

I separated concerns into packages, used immutable or validated domain
contracts, centralized configuration, preserved units and UTC time semantics,
introduced deterministic seeds and chronological evaluation, and treated
unavailable evidence as a first-class result. Tests cover individual modules
and cross-layer flows.

## Architecture and data engineering

EOIP includes representative solar plants, equipment, SCADA, weather, alarms,
incidents, work orders, tariffs, budgets, and independent ground truth. ETL
modules cover ingestion, cleaning, validation, incremental loading, retry,
audit, lineage, and Prefect orchestration. SQLAlchemy/Alembic define PostgreSQL
and TimescaleDB persistence, including analytical views and time-series
structures, while Phase O still needs to certify them in a clean runtime.

## Analytics and ML

- Operational KPI modules preserve units and invalid/unavailable states.
- Prophet is benchmarked against Seasonal Naive with expanding-window folds.
- Isolation Forest/residual/statistical anomaly paths separate predictions from
  independent truth.
- Random Forest maintenance labels are future-only with chronological splits.
- Equipment health exposes named component contributions without inventing
  confidence.

## Operations and application engineering

FastAPI defines typed, authenticated provider-backed read endpoints. Streamlit
provides 11 filtered dashboards with consistent navigation, drill-down state,
charts/tables, and filtered exports. The current UI uses deterministic
application frames; it is not presented as a live database client.

## Governance

Recommendations have stable source-derived IDs, explicit provenance, controlled
lifecycle transitions, optional ownership, typed evidence relationships,
append-oriented audit events, authorization rules, and versioned financial
assumption boundaries. Governance persistence is intentionally described as
non-durable. Revenue at Risk, ROI, and realized benefit remain unavailable.

## Testing and empirical results

The repository contains unit, integration, acceptance, end-to-end, performance,
security, and Streamlit UI tests. Phase L creates reproducible representative
artifacts with a fixed seed and timestamp. Data-quality criteria passed on the
representative dataset, and model-evaluation infrastructure produced honest
mixed outcomes.

## What failed

- Prophet MAE and WAPE were 66.27% worse than Seasonal Naive; interval coverage
  was 69.10% against a 90% criterion.
- Maintenance PR-AUC was 0.0073, ROC-AUC 0.5153, precision 0.0114, and top-5%
  recall 0.0417—all failed.
- Anomaly precision, recall, F1, critical recall, and delay were not verifiable
  because the test scope contained no eligible truth events.
- Equipment-health confidence is unsupported.
- Database migration/query benchmarks and production ETL success rate were not
  verified.
- Revenue at Risk, ROI, and realized benefit lack approved inputs/evidence.

Preserving these results is deliberate engineering discipline. A platform that
hides unfavorable metrics cannot support operational decisions or trustworthy
model improvement.

## Challenges and improvements

The main challenges were aligning time-series labels without leakage, keeping
synthetic truth independent, separating application/demo schemas from database
schemas, handling Windows test-state permissions, and preventing contextual
links from becoming false causal claims.

Phase O should certify database, containers, migrations, deployed API behavior,
and performance. Phase P should improve data/event design, features, baselines,
model families, ranking objectives, and calibration using unchanged acceptance
discipline. Phase Q should then re-audit every claim.

## Skills demonstrated

Python packaging, dataclasses/Pydantic/SQLAlchemy, PostgreSQL/TimescaleDB design,
Alembic, ETL orchestration, temporal ML evaluation, scikit-learn, Prophet,
FastAPI security, Streamlit application architecture, testing, reproducibility,
evidence governance, and technical communication.
