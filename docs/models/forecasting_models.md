# EOIP Forecasting Models

## Overview

The Energy Operations Intelligence Platform forecasting layer provides reusable
time-series forecasting capabilities for energy operations and solar plant
analytics.

The forecasting subsystem supports:

- Forecasting dataset construction
- Baseline forecasting models
- Prophet forecasting
- Feature engineering
- Training orchestration
- Expanding-window backtesting
- Forecast evaluation
- Model comparison
- Forecast persistence
- Forecast service orchestration

---

## Forecasting Targets

The current forecasting dataset contract supports the following targets:

- `active_power_kw`
- `interval_energy_kwh`
- `ghi_wm2`

Additional targets can be added through the `ForecastTarget` enumeration.

---

## Forecasting Dataset

Forecasting datasets are represented by:

`eoip.forecasting.dataset.ForecastDataset`

Each dataset includes:

- Timestamp column
- Target column
- Forecast frequency
- Ordered observations
- Validated numeric target values
- Unique timestamps

The dataset layer validates:

- Non-empty datasets
- Required columns
- Datetime timestamps
- Numeric targets
- Missing values
- Duplicate timestamps
- Chronological ordering

---

## Dataset Builder

The dataset builder is exposed through:

`build_forecast_dataset`

It converts source EOIP data into a validated forecasting dataset.

The builder supports:

- Timestamp normalization
- UTC conversion
- Target selection
- Feature selection
- Sorting
- Duplicate detection

---

## Feature Engineering

EOIP provides reusable feature preparation utilities.

### Time Features

`add_time_features`

Creates:

- Hour
- Minute
- Day of week
- Day of month
- Month
- Day of year
- Weekend indicator

### Lag Features

`add_lag_features`

Creates historical target features such as:

- Previous interval
- Previous hour
- Previous day
- Custom lag windows

### Rolling Features

`add_rolling_features`

Creates:

- Rolling mean
- Rolling standard deviation

Rolling statistics use shifted target values to reduce target leakage.

### Feature Selection

`select_forecast_features`

Produces the final model-ready feature frame and optionally removes rows
containing missing feature values.

---

## Forecast Model Contract

All EOIP forecasting models follow the `ForecastModel` protocol.

Models provide:

- `name`
- `fit`
- `predict`

Forecast output is standardized through `ForecastResult`.

Each result contains:

- Model name
- Target column
- Forecast timestamps
- Predicted values

---

# Baseline Models

## Naive Forecast

Class:

`NaiveForecastModel`

### Method

The naive forecast repeats the most recent observed target value across the
forecast horizon.

### Purpose

This model provides the simplest possible forecasting benchmark.

Any advanced forecasting model should normally outperform the naive forecast
before being considered useful.

### Strengths

- Extremely fast
- Easy to interpret
- No hyperparameters
- Useful benchmark

### Limitations

- Does not model seasonality
- Does not use weather
- Does not model trends
- Weak for longer horizons

---

## Seasonal Naive Forecast

Class:

`SeasonalNaiveForecastModel`

### Method

The seasonal naive model repeats the most recent seasonal cycle.

For example, with 15-minute data and daily seasonality:

96 observations represent one day.

The forecast can therefore repeat the previous day's production pattern.

### Purpose

Seasonal naive forecasting is a stronger baseline for solar generation because
solar power has strong daily seasonality.

### Strengths

- Simple
- Fast
- Strong solar baseline
- Preserves daily production pattern

### Limitations

- Cannot react to changing weather
- Assumes future seasonal patterns resemble the previous cycle
- Does not learn long-term trends

---

# Prophet Forecasting

Class:

`ProphetForecastModel`

Library:

`prophet`

### Method

Prophet models time series as a combination of:

- Trend
- Seasonality
- Calendar effects

The current EOIP implementation supports configurable:

- Daily seasonality
- Weekly seasonality
- Yearly seasonality

### EOIP Timestamp Handling

EOIP operates with timezone-aware UTC timestamps.

Prophet internally expects timezone-naive timestamps.

The model therefore:

1. Converts training timestamps to UTC.
2. Removes timezone information before passing data to Prophet.
3. Generates forecasts.
4. Returns forecast timestamps as timezone-aware UTC values.

### Strengths

- Handles trend
- Handles seasonality
- Interpretable
- Appropriate for operational time series
- Robust baseline advanced model

### Limitations

- Forecast quality depends on historical patterns
- Weather regressors are not automatically included
- Computationally heavier than baseline models
- Solar production may require weather-aware models for best accuracy

---

# Training Pipeline

Training orchestration is provided by:

`train_forecast_model`

The training pipeline:

1. Validates training data.
2. Verifies timestamp and target columns.
3. Calls the selected model's `fit` method.
4. Returns standardized training metadata.

Training metadata includes:

- Model name
- Target column
- Timestamp column
- Number of training observations

---

# Backtesting

EOIP uses expanding-window backtesting through:

`expanding_window_backtest`

### Method

For each backtest fold:

1. Train using all observations available up to that point.
2. Forecast the next configured horizon.
3. Compare predictions with actual observations.
4. Expand the training window.
5. Repeat.

This method approximates how forecasting models behave in production.

### Configurable Parameters

- Initial training size
- Forecast horizon
- Step size
- Frequency

---

# Forecast Evaluation

EOIP evaluates forecasts using:

- MAE
- RMSE
- MAPE
- sMAPE

## Mean Absolute Error

MAE measures the average absolute forecast error.

Lower values are better.

## Root Mean Squared Error

RMSE penalizes larger forecast errors more heavily than MAE.

Lower values are better.

## Mean Absolute Percentage Error

MAPE expresses average forecast error as a percentage.

Zero actual values are excluded.

If every actual value is zero, MAPE is undefined.

## Symmetric Mean Absolute Percentage Error

sMAPE provides a symmetric percentage-based error metric.

This is useful for energy time series containing values near zero.

---

# Model Comparison

EOIP provides:

`aggregate_backtest_metrics`

and:

`rank_model_summaries`

Backtest predictions are aggregated across folds and evaluated using the same
metric definitions.

Models can be ranked using:

- MAE
- RMSE
- MAPE
- sMAPE

Lower error values represent better forecast performance.

---

# Forecast Storage

Forecast persistence is implemented through the `ForecastStore` contract.

The PostgreSQL implementation is:

`DatabaseForecastStore`

Forecast storage uses two tables.

## forecast_runs

Stores forecast metadata:

- Forecast ID
- Model name
- Target column
- Generation timestamp
- Forecast row count

## forecast_values

Stores individual forecast values:

- Forecast ID
- Forecast timestamp
- Prediction

Forecast values are linked to forecast runs through a foreign key.

Deleting a forecast run also removes its associated prediction values.

---

# Database Migration

Forecast storage tables are managed through Alembic.

Migration:

`1b5c1857e89b_add_forecast_storage_tables`

The migration creates:

- `forecast_runs`
- `forecast_values`
- Forecast indexes
- Referential integrity constraints
- Positive row-count validation

Production database schemas should be updated using Alembic rather than direct
table creation.

---

# Forecast Service

Forecast application orchestration is provided through:

`ForecastService`

The service supports:

- Model training
- Forecast generation
- Forecast persistence
- Stored forecast retrieval

The service intentionally does not expose HTTP routes directly.

FastAPI endpoints will be added later during the dedicated API phase.

---

# Recommended Solar Forecasting Workflow

A typical EOIP forecasting workflow is:

1. Retrieve SCADA history.
2. Retrieve weather observations.
3. Build the forecasting dataset.
4. Add time features.
5. Add lag features.
6. Add rolling statistics.
7. Select model-ready features.
8. Train baseline models.
9. Train Prophet.
10. Run expanding-window backtesting.
11. Calculate forecast metrics.
12. Rank model performance.
13. Select the preferred model.
14. Generate production forecasts.
15. Store forecasts in PostgreSQL.
16. Expose stored forecasts through the application service.

---

# Current Models

| Model | Type | Status |
|---|---|---|
| Naive Forecast | Baseline | Implemented |
| Seasonal Naive | Baseline | Implemented |
| Prophet | Statistical Forecasting | Implemented |

---

# Current Evaluation Metrics

| Metric | Status |
|---|---|
| MAE | Implemented |
| RMSE | Implemented |
| MAPE | Implemented |
| sMAPE | Implemented |

---

# Future Extensions

Possible later improvements include:

- Weather regressors in Prophet
- Clear-sky index features
- Cloud-cover features
- Numerical weather prediction integration
- Gradient boosting forecasting
- LightGBM or XGBoost
- Quantile forecasts
- Prediction intervals
- Ensemble forecasting
- Probabilistic forecasting
- Per-plant models
- Per-inverter models
- Automated model selection
- Forecast drift monitoring

These extensions are outside the current Phase 6 completion scope and can be
added later without changing the existing forecasting interfaces.