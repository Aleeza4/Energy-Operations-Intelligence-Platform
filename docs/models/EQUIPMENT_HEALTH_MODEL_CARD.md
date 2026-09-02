# Equipment health model card

## Purpose and operational use

EOIP equipment health combines named degradation contributions into a
human-readable score for asset review. It is deterministic analytical scoring,
not a trained survival model and not a calibrated confidence estimate.

## Inputs and outputs

Phase L constructs equipment-level inputs from failure probability, anomaly
rate, alarm burden, temperature stress, and performance loss. The health module
returns health/degradation scores and component contribution columns.

## Evaluation method and results

The monitored population is all 24 inverter IDs present before scoring in the
representative telemetry. Tests verify coverage and that component
contributions sum to degradation.

| Criterion | Actual | Status |
|---|---:|---|
| Population coverage | 100% (24/24) | `PASS` |
| Maximum component-sum error | 6.9389e-18 | `PASS` |
| Defensible confidence | Unsupported | `FAIL` |
| Historical trend validation | unavailable | `NOT VERIFIED` |
| Independent outcome validation | unavailable | `NOT VERIFIED` |

Representative health scores range from 92.1940 to 99.8437 with mean 96.8873.
These values demonstrate computation coverage, not real-world equipment health
accuracy.

## Confidence and limitations

No calibrated uncertainty, ensemble variance, or empirical error model exists.
Failure probability and health score are not relabeled as confidence. The score
also inherits limitations from maintenance and representative synthetic inputs.

Current status: **coverage and decomposition `PASS`; confidence `FAIL`; outcome
validity `NOT VERIFIED`**.
