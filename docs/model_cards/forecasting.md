# Forecasting Model Card

## 1. Model Summary

The forecasting component of the Energy Operations Intelligence Platform estimates near-term generation and energy output for solar assets using historical plant telemetry, weather condition data, and time-series patterns. The current implementation is designed to support operational planning, comparison against expected output, and dashboard-friendly forecast views rather than automated financial dispatch decisions.

The primary model is a time-series forecasting model trained on representative SCADA and meteorological inputs to predict future generation performance over a defined horizon. The model is intentionally conservative in scope and framed as an operational decision support tool.

---

## 2. Intended Use

This forecasting model is intended for:

- plant-level operational planning
- day-ahead and intra-day generation visibility
- comparison of actual vs expected output
- anomaly and performance context during operational reviews
- dashboard use in operational monitoring workflows

This model should not be used as a sole basis for:

- revenue guarantee commitments
- dispatch or trading decisions without additional validation
- automated maintenance or investment approval without human review

---

## 3. Model Type

The platform uses a statistical forecasting approach adapted to solar generation time-series behavior. The model incorporates:

- historical energy production patterns
- meteorological inputs such as irradiance, temperature, and wind conditions
- time-based seasonality and trend signals
- plant-specific training data context

The model is assessed as a predictive support model for operational monitoring and performance analysis rather than as a production-grade utility-scale forecasting product.

---

## 4. Data Inputs

### Primary data sources

- plant SCADA telemetry
- weather observations
- historical generation output
- operational timestamps aligned to plant timezone

### Key input features

- timestamp
- active power output
- interval energy production
- irradiance measurements
- ambient and module temperature
- wind speed and humidity
- plant identifier and equipment context

### Data scope

The forecasting work in the project is intentionally scoped to representative synthetic operational data. This supports reproducibility and evaluation while keeping the demonstration environment controlled and auditable.

---

## 5. Operational Context

The model supports the platform’s broader analytics architecture:

- telemetry passes through the plant and equipment layers
- environmental inputs contribute to generation context
- forecast outputs are persisted for downstream comparison and dashboard consumption
- forecasts are evaluated against historical performance signals to establish confidence bounds

This supports a practical workflow in which forecast output is examined alongside observed conditions, alarms, incidents, and equipment health indicators.

---

## 6. Evaluation Method

The project’s empirical evaluation follows a reproducible rolling-window methodology. Forecast performance is measured using consistent train/test partitions and evaluation metrics that highlight both fit quality and operational usefulness.

### Evaluation setup

- repeated expanding-window validation
- earlier data used for training
- fixed future periods used for testing
- comparison against a simple baseline model
- evaluation over representative forecast horizons

### Metrics used

- MAE (Mean Absolute Error)
- RMSE (Root Mean Squared Error)
- WAPE (Weighted Absolute Percentage Error)
- bias
- interval coverage

These metrics assess both point forecast quality and uncertainty calibration.

---

## 7. Empirical Results

The current evaluation for the project shows mixed results and therefore requires a careful interpretation.

| Metric | Forecasting Model | Baseline | Interpretation |
| --- | ---: | ---: | --- |
| MAE | 3.166386 | 1.904342 | Model underperformed for absolute error |
| RMSE | 4.083339 | 4.739307 | Model improved on RMSE |
| WAPE | 39.657357% | 23.850911% | Model underperformed materially |
| Bias | -1.834427% | 0.580902% | Bias acceptable within threshold |
| Interval coverage | 69.097222% | unavailable | Below acceptable calibration threshold |

### Interpretation

The forecasting model achieved a better RMSE but failed on MAE and WAPE against the baseline. The model also under-covered its uncertainty intervals, which means the confidence bounds are not sufficiently calibrated for a high-assurance production claim.

This is a critical outcome: the project cannot claim that the forecasting model is broadly superior or production-ready from this evaluation alone.

---

## 8. Model Status

### Current status

The forecasting model is currently in a mixed evidence state:

- some metrics pass
- other metrics fail against the baseline
- uncertainty coverage is insufficient for strong confidence claims
- scope is limited to representative synthetic data

### Status label

Status: Mixed Pass/Fail with synthetic evidence only

This means the model is appropriate as a demonstration, testing, and dashboard-capability asset, but not yet as a validated production forecasting instrument.

---

## 9. Limitations

The forecasting model has several important limitations:

- It is trained on representative synthetic data rather than a full live operating portfolio.
- It is evaluated over a limited forecast horizon and structured validation windows.
- It has not yet been benchmarked against broader production-scale conditions.
- Uncertainty calibration remains insufficient for high-confidence planning decisions.
- Forecast values are not treated as guaranteed generation outcomes.

These limitations should be explicitly stated in any stakeholder or leadership briefing.

---

## 10. Governance and Risk

This model should be treated as a decision-support capability with clear human review requirements.

Recommended governance actions:

- document model limitations clearly in operational dashboards
- avoid using the model as a sole decision trigger for financial commitments
- compare forecast outputs with real-world operational feedback
- continuously upgrade evaluation windows and data quality checks
- maintain a versioned record of model performance and training context

---

## 11. Summary

The EOIP forecasting model is useful for visibility, planning support, and comparative analytics, but it is not yet at a level that supports unqualified production claims. Its current evidence is strong enough to support operational exploration and dashboard integration, while still requiring transparent caveats around accuracy, calibration, and synthetic-data limitations.
