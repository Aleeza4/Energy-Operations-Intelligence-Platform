# Anomaly model card

## Purpose and operational use

EOIP provides Isolation Forest, residual-analysis, and statistical anomaly
implementations for abnormal-behavior investigation. An anomaly is an
investigation signal, not proof of failure or causality.

## Phase L method

The fixed Phase L benchmark evaluates repository Isolation Forest behavior for
`PLANT-001`. Contamination is `0.001`, selected from independent truth
prevalence for the benchmark. Ground-truth events are scheduled before detector
execution and are not derived from predictions. The evaluated test period is
`2025-02-18T00:00:00Z` to `2025-03-02T00:00:00Z` (exclusive), containing 1,152
observations and 12 asset-days.

## Empirical results

The test scope contained no eligible truth events. The detector produced two
false positives and 1,150 true negatives:

| Metric | Actual | Status |
|---|---:|---|
| False alerts per asset-day | 0.166667 | `PASS` (<0.20) |
| Precision | unavailable | `NOT VERIFIED` |
| Recall | unavailable | `NOT VERIFIED` |
| F1 | unavailable | `NOT VERIFIED` |
| Critical-event recall | unavailable | `NOT VERIFIED` |
| Conservative p95 detection delay | unavailable | `NOT VERIFIED` |

The false-alert result is measurable because false positives and exposure are
known. Effectiveness cannot be inferred when the evaluated population contains
no eligible positive events.

## Inputs, outputs, and thresholds

Detectors consume numeric operational time series and produce scores/labels
according to their implementations. Threshold semantics vary by detector; the
Phase L artifact records the exact Isolation Forest contamination setting.
Stored anomalies may be linked to recommendations only with an explicit
relationship. Matching plant/equipment identifiers justify at most
`RELATED_TO` unless stronger lineage exists.

## Limitations and status

- Representative synthetic scope and no eligible positive test events.
- Precision, recall, F1, critical recall, and delay are `NOT VERIFIED`.
- Detection does not establish root cause, equipment failure, or financial loss.
- Phase N does not alter thresholds or synthetic truth.

Current status: **false-alert criterion `PASS`; effectiveness `NOT VERIFIED`**.
