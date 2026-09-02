# EOIP Anomaly Detection Models

> **Design/implementation reference.** Use the
> [anomaly model card](ANOMALY_MODEL_CARD.md) for empirical status. Phase L
> anomaly effectiveness metrics are mostly `NOT VERIFIED`.

## Overview

The Energy Operations Intelligence Platform anomaly detection layer identifies
unexpected operational behavior in solar plant and energy time-series data.

The subsystem currently supports:

- Validated anomaly detection datasets
- Statistical Z-score detection
- Isolation Forest detection
- Residual-based anomaly analysis
- Centralized threshold management
- Ground-truth evaluation
- Precision, recall, specificity, and F1 evaluation
- Alert generation
- PostgreSQL-backed anomaly storage

---

# Anomaly Detection Dataset

EOIP represents anomaly detection input using:

`AnomalyDataset`

The dataset validates:

- Non-empty observations
- Timestamp column presence
- Target column presence
- Datetime timestamps
- Chronological ordering
- Unique timestamps
- Numeric target values
- Missing-value constraints

Supported anomaly targets currently include:

- `active_power_kw`
- `interval_energy_kwh`
- `performance_ratio`
- `residual`

Datasets are constructed using:

`build_anomaly_dataset`

The builder:

1. Copies the source frame.
2. Normalizes timestamps to UTC.
3. Converts target values to numeric form.
4. Rejects invalid or missing values.
5. Rejects duplicate timestamps.
6. Sorts data chronologically.
7. Returns a validated `AnomalyDataset`.

---

# Statistical Baseline

## Z-Score Detector

Class:

`ZScoreAnomalyDetector`

The statistical detector calculates:

`z = (x - mean) / standard_deviation`

An observation is classified as anomalous when:

`abs(z_score) > threshold`

Default threshold:

`3.0`

The detector returns:

- Z-score
- Absolute Z-score
- Boolean anomaly flag
- Dataset mean
- Dataset standard deviation

### Strengths

- Highly interpretable
- Very fast
- Useful benchmark
- Easy to explain operationally

### Limitations

- Sensitive to distribution shape
- Global mean and standard deviation can be distorted by large outliers
- Does not naturally model multivariate relationships
- Does not capture time-dependent operating regimes

---

# Isolation Forest

Class:

`IsolationForestAnomalyDetector`

Library:

`scikit-learn`

Isolation Forest identifies unusual observations by randomly partitioning
feature space.

Anomalous observations generally require fewer random splits to isolate than
normal observations.

The EOIP implementation supports:

- Single-feature detection
- Multivariate feature detection
- Configurable contamination
- Deterministic random state
- Configurable estimator count
- Decision-function anomaly scores

Default configuration:

- `contamination = "auto"`
- `random_state = 42`
- `n_estimators = 100`

### Typical Features

Potential solar-operation features include:

- Active power
- Irradiance
- Temperature
- Performance ratio
- Voltage
- Current
- Forecast residual
- Rolling statistics

### Strengths

- Multivariate
- No normal-distribution assumption
- Suitable for unsupervised anomaly detection
- Handles nonlinear feature relationships
- Effective for unusual operating combinations

### Limitations

- Score interpretation is less intuitive than Z-score
- Sensitive to contamination assumptions
- Requires appropriate feature engineering
- Does not inherently understand temporal order

---

# Residual Analysis

Function:

`analyze_residuals`

Residual analysis compares observed and expected values.

Residual:

`actual - expected`

Absolute residual:

`abs(actual - expected)`

An observation is anomalous when:

`absolute_residual > threshold`

Expected values can come from:

- Forecasting models
- Physics-informed expected power
- Historical baseline models
- Clear-sky production estimates

Residual anomaly detection is especially useful in solar operations because
poor plant performance can be identified relative to expected production
rather than only relative to historical measurements.

### Example

If expected power is:

`800 kW`

and actual power is:

`500 kW`

then:

`residual = -300 kW`

The negative residual indicates underperformance.

---

# Threshold Management

Threshold configuration is managed through:

`AnomalyThreshold`

and:

`ThresholdRegistry`

Supported threshold types:

- Z-score
- Residual
- Anomaly score

The threshold registry supports:

- Register
- Replace
- Retrieve
- Remove
- Enable/disable
- List
- Clear

Centralized threshold management prevents anomaly rules from being scattered
through individual model implementations.

---

# Ground-Truth Evaluation

Ground-truth evaluation is provided through:

`evaluate_ground_truth`

The evaluation compares predicted anomaly flags with known anomaly labels.

The result contains the confusion matrix:

- True positives
- True negatives
- False positives
- False negatives

This is particularly important for EOIP synthetic data because the synthetic
event engine can provide known anomaly and fault labels.

---

# Precision and Recall Evaluation

EOIP calculates the following classification metrics.

## Accuracy

Accuracy measures the proportion of all classifications that are correct.

## Precision

Precision answers:

> Of all observations flagged as anomalies, how many were actually anomalies?

Formula:

`TP / (TP + FP)`

High precision means fewer false alarms.

This is important operationally because excessive false alarms create alarm
fatigue.

## Recall

Recall answers:

> Of all real anomalies, how many did the detector successfully identify?

Formula:

`TP / (TP + FN)`

High recall means fewer missed anomalies.

## Specificity

Specificity measures how well normal observations are correctly identified.

Formula:

`TN / (TN + FP)`

## F1 Score

F1 combines precision and recall.

Formula:

`2 × TP / (2 × TP + FP + FN)`

F1 is useful when both missed anomalies and false alarms matter.

---

# Alert Generation

Alert generation is implemented through:

`generate_anomaly_alerts`

Each generated anomaly alert contains:

- Alert ID
- Timestamp
- Source detector
- Metric
- Observed value
- Anomaly score
- Severity
- Message

Supported severities:

- Low
- Medium
- High
- Critical

Severity is currently derived from absolute anomaly score.

Default mapping:

| Absolute Score | Severity |
|---|---|
| `< 3.0` | Low |
| `3.0 – < 4.0` | Medium |
| `4.0 – < 5.0` | High |
| `>= 5.0` | Critical |

Future EOIP versions may combine severity with:

- Energy impact
- Financial impact
- Equipment criticality
- Duration
- Recurrence
- Plant operating state

---

# Anomaly Storage

Storage contracts are defined through:

`AnomalyStore`

Stored run metadata is represented by:

`StoredAnomalyRun`

The PostgreSQL implementation is:

`DatabaseAnomalyStore`

Anomaly persistence uses two tables.

## anomaly_runs

Stores run-level metadata:

- Anomaly run ID
- Detector name
- Target column
- Generated timestamp
- Row count
- Anomaly count

## anomaly_values

Stores observation-level results:

- Anomaly run ID
- Timestamp
- Boolean anomaly flag
- Detection score

The database schema includes:

- Primary keys
- Foreign-key integrity
- Cascade deletion
- Timestamp indexes
- Anomaly-flag index
- Positive row-count constraint
- Non-negative anomaly-count constraint
- Anomaly-count versus row-count constraint

Schema changes are managed through Alembic.

Migration:

`78e612611b54_add_anomaly_storage_tables`

---

# Recommended EOIP Detection Workflow

A typical anomaly detection workflow is:

1. Retrieve SCADA observations.
2. Retrieve weather observations.
3. Retrieve expected or forecast production.
4. Build the anomaly detection dataset.
5. Run the statistical baseline.
6. Run Isolation Forest.
7. Calculate residual anomalies.
8. Apply operational thresholds.
9. Compare predictions to synthetic ground truth.
10. Calculate precision and recall metrics.
11. Generate alerts.
12. Persist anomaly results in PostgreSQL.
13. Surface anomalies in the Streamlit application.
14. Expose anomaly results through the API layer.

---

# Current Models

| Model | Type | Status |
|---|---|---|
| Z-Score Detector | Statistical baseline | Implemented |
| Isolation Forest | Unsupervised ML | Implemented |
| Residual Analysis | Expected-vs-actual | Implemented |

---

# Current Evaluation Metrics

| Metric | Status |
|---|---|
| Accuracy | Implemented |
| Precision | Implemented |
| Recall | Implemented |
| Specificity | Implemented |
| F1 Score | Implemented |

---

# Current Persistence

| Component | Status |
|---|---|
| Anomaly storage contract | Implemented |
| SQLite unit verification | Implemented |
| PostgreSQL schema | Implemented |
| Alembic migration | Implemented |
| Database-backed store | Implemented |

---

# Future Extensions

Future improvements may include:

- Rolling robust Z-scores
- Median absolute deviation
- Dynamic thresholds
- Seasonal anomaly baselines
- Per-inverter anomaly models
- Autoencoder anomaly detection
- Local Outlier Factor
- One-Class SVM
- Forecast-residual Isolation Forest
- Context-aware anomaly scoring
- Multi-detector ensembles
- Anomaly duration tracking
- Event clustering
- Root-cause assistance
- Automated threshold optimization
- Model drift monitoring

These extensions can be added without changing the current Phase 7 interfaces.
