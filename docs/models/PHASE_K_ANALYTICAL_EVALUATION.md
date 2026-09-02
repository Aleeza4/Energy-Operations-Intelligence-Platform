# Phase K analytical evaluation

Phase K adds reproducible metric calculations and evidence-safe JSON artifacts.
It does not treat the dashboard demonstration frames as model-validation data.

## Forecasting

- WAPE is `sum(abs(actual - predicted)) / sum(abs(actual)) * 100` and is
  undefined when the denominator is zero.
- Bias is `sum(predicted - actual) / sum(actual) * 100`. Positive values mean
  over-forecasting; negative values mean under-forecasting.
- Interval coverage is the percentage of observed targets inside inclusive
  `[lower, upper]` bounds. Both bounds must come from the evaluated model.
- Candidate and Seasonal Naive results must use identical folds and samples.
  Improvement is `(baseline error - candidate error) / baseline error * 100`.
  A zero baseline error produces an undefined improvement, not a pass.
- Existing expanding-window folds preserve temporal ordering. Training rows
  always precede test rows, preventing future-target leakage.

## Anomaly detection

Precision, recall, and F1 use standard confusion-matrix definitions. Critical
recall is restricted to ground-truth observations explicitly labelled
`critical`.

False alerts per asset-day require explicit asset exposure intervals. Asset-days
are the sum of `(exposure_end - exposure_start) / 24 hours` for each supplied
asset interval. Missing exposure returns `NOT VERIFIED` rather than estimating a
denominator.

Detection delay matches detections to ground-truth event IDs and uses the
earliest detection at or after each event start. Mean, median, and p95 are
reported. Because the success criterion does not define which statistic governs
the threshold, artifacts must disclose that ambiguity rather than select the
most favorable statistic.

## Predictive maintenance

- PR-AUC uses scikit-learn average precision.
- Top-5%-risk recall ranks probabilities descending, selects
  `ceil(sample_count * 0.05)` with a minimum of one, and retains stable input
  order at ties. It divides positives in the cohort by all positives.
- Calibration evidence includes Brier score and fixed-width bins containing
  mean predicted probability and observed event rate. No calibration-quality
  pass threshold is invented.

All metrics must be calculated on held-out or temporally valid evaluation data.
Training performance must not be presented as validation.

## Equipment health

The health score is mathematically decomposable into five real weighted inputs:
failure probability, anomaly rate, alarm burden, temperature stress, and
performance loss. Phase K exposes those weighted contributions; they sum to the
degradation score.

Confidence is intentionally not implemented. EOIP has no uncertainty,
calibration, sample-sufficiency, or ensemble-dispersion model for health.
Failure probability and health score are not relabelled as confidence.
Historical and ground-truth validation remain unverified until timestamped
input histories and accepted outcome labels are supplied.

## Artifacts and reproduction

Capability artifacts live under `artifacts/evaluation/`. Unsupported values are
JSON `null` with status `NOT VERIFIED`, or `FAIL` when the capability itself is
unsupported.

```powershell
python scripts/generate_phase_k_evidence.py `
  --output artifacts/evaluation `
  --evaluated-at 2026-08-26T00:00:00+00:00
```

For real model evidence, callers must provide versioned model outputs and
evaluation populations to the analytical functions before creating a PASS or
FAIL artifact. Artifacts contain no credentials or absolute machine paths.
