# Forecast model card

## Purpose and operational use

EOIP forecasts plant energy to support planning and comparison with expected
generation. Forecasts provide decision context; they are not automatic revenue
or recommendation triggers.

## Models, inputs, and outputs

- Candidate: repository `ProphetForecastModel`.
- Baseline: `SeasonalNaiveForecastModel`.
- Phase L scope: `PLANT-001`, representative plant telemetry.
- Output: point forecast and Prophet interval bounds for a 24-hour horizon
  (96 observations at 15-minute resolution).

## Evaluation method

Phase L uses three expanding-window folds with strictly earlier training data
and one-day test folds. It evaluates 288 predictions. The baseline and candidate
use identical folds. The persisted split boundaries are in
`artifacts/evaluation/phase_l/phase_l_forecast_v1.json`.

## Empirical results

| Metric | Prophet | Seasonal Naive | Criterion/result |
|---|---:|---:|---|
| MAE | 3.166386 | 1.904342 | -66.2719% improvement — `FAIL` |
| RMSE | 4.083339 | 4.739307 | 13.8410% improvement — `PASS` |
| WAPE | 39.657357% | 23.850911% | -66.2719% improvement — `FAIL` |
| Bias | -1.834427% | 0.580902% | absolute bias <=5% — `PASS` |
| Interval coverage | 69.097222% | unavailable | >=90% — `FAIL` |

Prophet is not empirically superior overall: it improves RMSE while worsening
MAE and WAPE and under-covering its interval.

## Limitations and status

- One representative synthetic plant, not production performance.
- Only three folds and a 24-hour horizon in this evidence run.
- Interval coverage is inadequate for a high-confidence uncertainty claim.
- Forecast MAE/WAPE failures prohibit an unqualified “accurate forecast” claim.
- No forecast output is converted to Revenue at Risk.

Current status: **mixed `PASS`/`FAIL`, representative synthetic evidence**.
Phase P may examine features, tuning, alternative models, more horizons, and
calibration without weakening evaluation criteria.
