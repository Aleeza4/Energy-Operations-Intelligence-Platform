# Predictive maintenance model card

## Purpose and operational use

The maintenance pipeline ranks equipment attention using estimated future
failure risk. It supports review and prioritization; it is not a trusted
financial probability engine and does not authorize maintenance completion.

## Algorithm, inputs, and outputs

- Model: repository `RandomForestFailurePredictor` with 100 trees and Phase L
  random state `20260827`.
- Inputs: AC power, DC/AC voltage and current, frequency, power factor, and
  availability ratio.
- Output: binary prediction and failure probability.
- Target: inverter failure strictly after the observation and within 24 hours;
  failure types include feeder, inverter, and transformer trips.

## Splitting and leakage controls

Phase L uses chronological train/validation/test populations. Train ends
`2025-02-05T23:00:00Z`; validation ends `2025-02-17T23:00:00Z`. Labels are
future-only, and no post-failure or future incident features are used.

## Empirical results

The test population contains 6,912 observations: 48 positives and 6,864
negatives.

| Metric | Actual | Target | Status |
|---|---:|---:|---|
| PR-AUC | 0.007261 | >=0.80 | `FAIL` |
| ROC-AUC | 0.515258 | >=0.90 | `FAIL` |
| Precision | 0.011364 | >=0.80 | `FAIL` |
| Top-5% recall | 0.041667 | >=0.85 | `FAIL` |
| Recall | 0.020833 | reported | measured |
| Brier score | 0.018507 | descriptive | measured |
| Calibration persistence | Brier score and bins recorded | evaluated | `PASS` |

Only two positive observations were captured in the 346-row top-risk cohort.
Calibration being evaluated does not mean the probabilities are adequate for
cost or expected-loss decisions.

## Limitations and status

- Severe class imbalance and weak discrimination.
- Representative synthetic outcomes, not field failures.
- Probability calibration is not sufficient for financial use.
- The model must not be multiplied by replacement cost or revenue exposure.

Current status: **evaluation capability `PASS`; predictive criteria `FAIL`**.
Phase P should investigate event prevalence, labels, features, model families,
ranking objectives, temporal validation, and calibration without changing truth
or acceptance thresholds.
