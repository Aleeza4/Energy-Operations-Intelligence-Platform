# EOIP Predictive Maintenance Models

## Overview

The Energy Operations Intelligence Platform predictive-maintenance layer
estimates equipment failure risk, explains contributing factors, calculates
equipment health, classifies risk, and prioritizes maintenance actions.

The current subsystem supports:

- Predictive-maintenance dataset construction
- Equipment-level feature engineering
- Failure-window labeling
- Random Forest failure prediction
- Equipment health scoring
- Maintenance risk classification
- SHAP explainability
- Maintenance prioritization
- Predictive-maintenance model evaluation

---

# Maintenance Dataset

Predictive-maintenance observations are represented by:

`MaintenanceDataset`

The dataset validates:

- Non-empty observations
- Timestamp column presence
- Equipment identifier presence
- Target presence
- Datetime timestamps
- Missing-value constraints
- Unique equipment/timestamp observations
- Candidate feature discovery

The dataset can contain operational signals such as:

- Active power
- Temperature
- Alarm counts
- Anomaly rates
- Performance loss
- SCADA measurements
- Equipment operating state
- Historical maintenance indicators

---

# Maintenance Dataset Builder

Datasets are constructed using:

`build_maintenance_dataset`

The builder:

1. Copies source data.
2. Normalizes timestamps to UTC.
3. Normalizes equipment identifiers.
4. Rejects invalid identifiers.
5. Rejects missing targets.
6. Rejects duplicate equipment/timestamp observations.
7. Sorts records by equipment and timestamp.
8. Returns a validated `MaintenanceDataset`.

---

# Feature Engineering

EOIP provides reusable equipment-level feature engineering.

## Lag Features

Function:

`add_lag_features`

Lag features represent earlier values from the same equipment asset.

Examples:

- Previous active power
- Previous inverter temperature
- Previous alarm count

Lag operations are grouped by equipment so values do not leak between assets.

---

## Rolling Features

Function:

`add_rolling_features`

Rolling features include:

- Rolling mean
- Rolling standard deviation

Rolling calculations are shifted before aggregation.

This prevents the current observation from leaking into its own historical
feature values.

Potential uses include:

- Temperature trend monitoring
- Power degradation monitoring
- Alarm-frequency tracking
- Operational instability detection

---

## Delta Features

Function:

`add_delta_features`

Delta features represent the first difference between consecutive observations
from the same asset.

Examples:

- Change in active power
- Change in temperature
- Change in current
- Change in voltage

Large changes may indicate developing equipment abnormalities.

---

# Failure Window Definition

Future-failure labels are generated using:

`label_failure_windows`

The target indicates whether a failure occurs after the observation timestamp
and before or at the end of a configured prediction horizon.

The rule is:

`observation_time < failure_time <= observation_time + prediction_window`

This intentionally excludes a failure occurring at the exact observation
timestamp because predictive maintenance should predict future failures rather
than label an already-occurring failure as a successful prediction.

The default prediction window is:

`24 hours`

Different horizons can be configured depending on operational needs.

Examples:

- 6 hours
- 12 hours
- 24 hours
- 48 hours
- 7 days

---

# Failure Prediction

## Random Forest Failure Predictor

Class:

`RandomForestFailurePredictor`

Library:

`scikit-learn`

The current EOIP supervised failure-prediction model uses:

`RandomForestClassifier`

The default configuration includes:

- `n_estimators = 100`
- `random_state = 42`
- `class_weight = "balanced"`
- `probability_threshold = 0.5`

The fixed random state makes model behavior reproducible.

---

## Training Requirements

The model requires:

- Numeric features
- Finite values
- No missing feature values
- Unique feature names
- Binary target labels
- Both target classes represented

The model records the exact feature schema used during training.

Prediction requires the same feature schema and order.

---

## Prediction Output

Predictions are represented by:

`FailurePredictionResult`

Each prediction contains:

- Failure probability
- Boolean predicted-failure flag

The failure probability lies between:

`0.0` and `1.0`

The Boolean classification is created using the configured probability
threshold.

---

# Equipment Health Score

Equipment health is calculated using:

`calculate_equipment_health_score`

Batch scoring is provided by:

`calculate_health_scores`

The health model combines normalized degradation signals.

Default weights:

| Signal | Weight |
|---|---:|
| Failure probability | 0.35 |
| Anomaly rate | 0.20 |
| Alarm burden | 0.15 |
| Temperature stress | 0.15 |
| Performance loss | 0.15 |

The weighted degradation score is normalized between:

`0.0` and `1.0`

Health is calculated as:

`100 × (1 - degradation_score)`

Therefore:

- `100` represents best modeled health.
- `0` represents maximum modeled degradation.

---

# Maintenance Risk Classification

Risk classification is provided through:

`classify_equipment_risk`

Batch classification is provided through:

`classify_equipment_risks`

Risk combines:

- Equipment health degradation
- Failure probability

Default weights:

| Component | Weight |
|---|---:|
| Failure probability | 0.60 |
| Health-derived risk | 0.40 |

Health-derived risk is:

`1 - health_score / 100`

The resulting risk score ranges from:

`0.0` to `1.0`

---

## Risk Levels

Risk scores are classified as:

| Risk Score | Level |
|---|---|
| `< 0.25` | Low |
| `0.25 – < 0.50` | Moderate |
| `0.50 – < 0.75` | High |
| `>= 0.75` | Critical |

These categories provide an operational interpretation of predictive risk.

---

# Explainability with SHAP

Failure predictions are explained through:

`explain_failure_predictions`

Library:

`shap`

The EOIP Random Forest model uses SHAP tree-based explanations.

SHAP provides feature-level contribution values showing how each feature
influenced the model output.

Examples of potentially important contributors include:

- High inverter temperature
- Repeated alarms
- Declining active power
- Elevated anomaly rate
- Performance degradation
- Historical operational instability

---

## SHAP Output

SHAP results are represented by:

`ShapExplanationResult`

The result includes:

- Per-observation SHAP values
- Model base value
- Feature names
- Mean absolute feature importance

Mean absolute SHAP importance can be used to identify which features most
strongly influence predictions across many assets.

---

# Maintenance Prioritization

Maintenance ranking is provided through:

`prioritize_maintenance`

The priority model combines:

- Maintenance risk score
- Failure probability
- Health degradation
- Asset criticality

Default weights:

| Component | Weight |
|---|---:|
| Risk score | 0.40 |
| Failure probability | 0.30 |
| Health degradation | 0.20 |
| Criticality | 0.10 |

The resulting priority score ranges from:

`0.0` to `1.0`

Higher values indicate greater maintenance urgency.

Assets are ranked in descending priority order.

Ties are resolved deterministically using equipment identifier ordering.

---

# Model Evaluation

Failure-prediction evaluation is provided through:

`evaluate_failure_predictions`

The evaluation result is represented by:

`MaintenanceEvaluationResult`

The current metrics include:

- Accuracy
- Precision
- Recall
- Specificity
- F1 Score
- ROC AUC
- True positives
- True negatives
- False positives
- False negatives

---

## Precision

Precision answers:

> Of the equipment observations predicted to fail, how many actually failed?

Formula:

`TP / (TP + FP)`

High precision reduces unnecessary maintenance actions.

---

## Recall

Recall answers:

> Of all actual future failures, how many were detected in advance?

Formula:

`TP / (TP + FN)`

Recall is especially important for critical equipment because missed failures
can create downtime and financial loss.

---

## Specificity

Specificity measures how well the model correctly identifies normal equipment.

Formula:

`TN / (TN + FP)`

---

## F1 Score

F1 balances precision and recall.

Formula:

`2 × precision × recall / (precision + recall)`

It is useful when failure events are less common than normal operating
observations.

---

## ROC AUC

ROC AUC evaluates the model's ability to rank failure observations above normal
observations across different classification thresholds.

Higher values indicate stronger discrimination.

---

# Recommended EOIP Predictive-Maintenance Workflow

A typical predictive-maintenance workflow is:

1. Retrieve equipment history.
2. Retrieve SCADA measurements.
3. Retrieve alarms and incidents.
4. Retrieve anomaly-detection results.
5. Retrieve known failure events.
6. Construct the maintenance dataset.
7. Generate failure-window labels.
8. Add lag features.
9. Add rolling features.
10. Add delta features.
11. Select model-ready numeric features.
12. Split data chronologically.
13. Train the Random Forest failure model.
14. Generate failure probabilities.
15. Evaluate model performance.
16. Generate SHAP explanations.
17. Calculate equipment health.
18. Calculate maintenance risk.
19. Add equipment criticality.
20. Rank maintenance priorities.
21. Surface results in the maintenance dashboard.
22. Expose predictive-maintenance results through the API layer.

---

# Current Predictive-Maintenance Components

| Component | Status |
|---|---|
| Maintenance Dataset | Implemented |
| Feature Engineering | Implemented |
| Failure Window Definition | Implemented |
| Random Forest Failure Prediction | Implemented |
| Equipment Health Score | Implemented |
| Risk Classification | Implemented |
| SHAP Explainability | Implemented |
| Maintenance Prioritization | Implemented |
| Model Evaluation | Implemented |

---

# Current Evaluation Metrics

| Metric | Status |
|---|---|
| Accuracy | Implemented |
| Precision | Implemented |
| Recall | Implemented |
| Specificity | Implemented |
| F1 Score | Implemented |
| ROC AUC | Implemented |

---

# Current Model

| Model | Type | Status |
|---|---|---|
| Random Forest | Supervised classification | Implemented |

---

# Future Extensions

Future predictive-maintenance improvements may include:

- Gradient boosting classifiers
- XGBoost
- LightGBM
- Time-to-failure prediction
- Remaining useful life estimation
- Survival analysis
- Equipment-specific models
- Inverter-specific models
- Transformer-based sequence models
- LSTM sequence models
- Dynamic failure windows
- Cost-sensitive classification
- Probability calibration
- Automated threshold optimization
- Model drift monitoring
- Maintenance feedback loops
- Work-order outcome integration

These extensions can be added without changing the current Phase 8 foundation.