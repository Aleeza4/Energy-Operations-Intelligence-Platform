# Predictive Maintenance Model Card

## 1. Model Summary

The predictive maintenance component of the Energy Operations Intelligence Platform is designed to estimate the probability that an asset will experience a near-term failure event. It combines equipment-level telemetry, operational features, failure-window labeling, and a supervised learning model to support maintenance prioritization and operational review.

This model sits at the intersection of equipment reliability and operational visibility. It is intended to support maintenance planning and inspection prioritization rather than to replace engineering judgement or maintenance teams.

---

## 2. Intended Use

This model is intended for:

- identifying equipment segments with elevated failure risk
- prioritizing maintenance interventions by estimated risk
- supporting field and operations review workflows
- combining machine-generated risk signals with alarms and incidents

This model should not be used for:

- automatic dispatch without human validation
- blind replacement decisions based only on score output
- guaranteed failure prediction claims
- final root-cause classification without field investigation

---

## 3. Model Type

The predictive maintenance workflow uses a supervised learning approach based on failure-window labeling and equipment-level feature engineering. The model type consists of a random forest classifier trained on engineered operational features such as lagged readings, rolling statistics, and delta indicators.

The model is designed to estimate whether a near-term failure is more likely than not within a defined horizon, based on recent equipment behavior.

---

## 4. Data and Feature Engineering

### Data sources

The model consumes operational and equipment data including:

- SCADA telemetry
- alarm records
- equipment operating state
- historical maintenance indicators
- performance-related variables
- weather and plant context when relevant

### Feature engineering

The workflow includes a structured set of engineered features, such as:

- lag features from previous observations
- rolling mean and rolling standard deviation over historical windows
- delta features representing change between consecutive observations
- equipment-specific operational patterns

These features help the model detect emerging reliability risk while avoiding leakage from the current observation into its own explanatory features.

---

## 5. Label Definition

The model defines a future failure label using a configurable horizon. A record is labeled as a failure case when a failure event occurs after the current observation time and within the defined prediction period.

This design ensures the model predicts future failures rather than classifying events that are already occurring at the same timestamp.

Common prediction windows include:

- 6 hours
- 12 hours
- 24 hours
- 48 hours
- 7 days

---

## 6. Model Training and Scoring

The predictive maintenance classifier uses a random forest model with reproducible settings and a balanced class objective.

### Model characteristics

- algorithm: RandomForestClassifier
- objective: failure risk classification
- class balancing: enabled
- reproducibility: fixed random state
- scoring: probability-based risk estimate

### Operational output

The model produces:

- probability of failure within the configured horizon
- risk categorization
- equipment-level prioritization output
- maintenance recommendation support based on risk and operational context

---

## 7. Evaluation Status

The empirical status for the corresponding maintenance model card indicates that the system did not meet the relevant performance thresholds in the evaluated benchmark.

The current project evidence indicates that the maintenance model failed the discrimination- and recall-related criteria under the defined validation conditions. This means the predictive maintenance workflow is still a capability demonstration rather than a confirmed production-qualifying model.

Key implication:

- model scores are useful for exploration and prioritization workflows
- model outputs should be interpreted cautiously
- operational validation remains required before governance approval

---

## 8. Model Limitations

The predictive maintenance model carries several important limitations:

- evaluation performance did not meet the project’s stated thresholds
- predictive output is bounded by the synthetic benchmark conditions
- failure labels are dependent on historical event definitions and selected horizons
- the model is not a standalone root-cause or failure-proofing system
- maintenance prioritization must be reviewed alongside alarms, work orders, and field observations

---

## 9. Risk and Governance

This model should be treated as a decision-support tool with human oversight. It should complement operational judgement, maintenance planning, and field investigation instead of substituting for them.

Recommended governance controls:

- review high-risk outputs with engineering or operations teams
- combine score-based recommendations with actual alarm and incident context
- clearly label the model as benchmarked, not fully production-validated
- maintain versioned performance evidence and retraining records
- avoid one-click maintenance closure based solely on model output

---

## 10. Summary

The EOIP predictive maintenance model is a meaningful operational analytics capability, but it is not yet a fully validated production-grade reliability model. It provides value for investigating equipment risk patterns and maintaining a structured maintenance prioritization workflow, while still requiring explicit caution due to the project’s current performance evidence and the fact that the model is based on synthetic benchmark conditions.
