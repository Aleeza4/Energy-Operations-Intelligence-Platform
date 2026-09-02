# EOIP interview guide

## 30-second summary

EOIP is an end-to-end renewable-energy operations intelligence platform. I built
typed synthetic data and ETL, PostgreSQL/TimescaleDB architecture, forecasting,
anomaly and maintenance analytics, a secured API definition, an 11-page
Streamlit UI, and recommendation governance. Its strongest feature is evidence
discipline: Phase L preserves failed model results and Phase M prevents
unsupported causal or financial claims.

## Two-minute summary

The platform starts with deterministic solar plants, equipment, telemetry,
weather, and operational events. Validation/ETL modules provide cleaning,
incremental state, retries, audit, and lineage. SQLAlchemy and Alembic define the
persistence layer. Analytics modules compute operational KPIs and evaluate
Prophet against Seasonal Naive, anomaly detectors against independent truth,
and a Random Forest using future-only failure labels. A Streamlit interface
organizes operational and intelligence workflows, while FastAPI router/provider
contracts define authenticated reads. Recommendations use stable identity,
explicit evidence relationships, lifecycle rules, ownership, audit, and
financial assumptions. Results are mixed by design: data-quality evidence is
strong, while forecasting and maintenance expose important failures.

## Five-minute architecture walkthrough

1. Show `src/eoip/synthetic` and the fixed Phase L configuration.
2. Explain ETL validation/audit/lineage and database repositories/migrations.
3. Show temporal model evaluation and Phase L JSON artifacts.
4. Contrast the configured persistence/API path with Streamlit's current
   deterministic `data_access.py` path.
5. End with recommendation governance and why unavailable money stays absent.

## Ten-minute technical walkthrough

Add the expanding-window forecast folds, future-only failure labeling, anomaly
truth alignment, component health decomposition, provider-based API design,
role authorization, PageDataContract filters, stable recommendation IDs,
append-oriented events, assumption versioning, and Windows-safe test execution.
Then show the evidence index and “What failed” section.

## Common questions

### Why TimescaleDB?

The domain contains high-volume timestamped telemetry plus relational assets and
operations records. TimescaleDB keeps PostgreSQL semantics while adding
hypertables and continuous aggregates. EOIP configures those structures, but
runtime performance remains `NOT VERIFIED` until Phase O.

### Why Prophet and a Seasonal Naive baseline?

Prophet provides trend/seasonality and intervals; Seasonal Naive is a strong,
transparent operational baseline. The comparison prevents model complexity from
being mistaken for improvement. Prophet only won RMSE in Phase L.

### How did you prevent leakage?

Forecast folds are chronological. Maintenance labels include only failures
strictly after an observation within 24 hours, with no future/post-failure
features. Anomaly truth is scheduled before detector execution.

### Why is PR-AUC important?

Failures are rare. PR-AUC focuses on positive-class ranking quality and is more
informative than accuracy in an imbalanced population. EOIP's 0.0073 result
shows the model is not operationally trustworthy.

### Why did maintenance perform poorly?

The representative data has rare outcomes and the chosen signals/model do not
separate positives adequately. I would revisit event design, label horizon,
features, class/ranking objectives, model families, and temporal calibration—
without changing truth to make metrics look better.

### Why not hide failed results?

Failures establish an honest improvement baseline, expose risk, and demonstrate
that evaluation criteria govern claims rather than presentation needs.

### How are anomalies linked to recommendations?

Only through explicit evidence references. Current matching demo records are
`RELATED_TO`; the recommendation generator does not establish that the anomaly
caused or triggered the recommendation.

### How is governance implemented?

Immutable dataclasses/enums define identity, status transitions, owner,
evidence, actors, audit events, assumptions, and calculations. Operator/admin
writes are validated in the in-memory domain boundary, but durable workflow is
not exposed.

### Why isn't Revenue at Risk available?

There is no defensible future energy-at-risk quantity, approved energy price,
currency, horizon, or assumption version. Recoverable energy and model failure
probability cannot simply be renamed as revenue exposure.

### How would production data replace synthetic data?

Implement source connectors at the ingestion/provider boundaries, retain the
typed validation and provenance contracts, load a disposable then managed
PostgreSQL/TimescaleDB environment, and re-evaluate models on independent field
outcomes. The Streamlit data boundary would be replaced by an authenticated
API/data provider rather than dashboard-local queries.

### How would you scale telemetry ingestion?

Partition by time/asset, batch validated writes, use hypertables and retention/
aggregation policies, enforce bounded queries, monitor late/duplicate data, and
measure throughput/latency under representative load before selecting further
streaming infrastructure.

### What would you do in Phase P?

Preserve Phase L artifacts and acceptance criteria; improve data coverage,
baselines, feature design, algorithms, ranking/calibration, and uncertainty;
then produce a new versioned evaluation rather than rewriting old evidence.
