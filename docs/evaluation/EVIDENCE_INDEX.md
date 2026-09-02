# EOIP evidence index

| Evidence | Artifact/source | Purpose | Classification | Status |
|---|---|---|---|---|
| Representative dataset | `artifacts/evaluation/phase_l/phase_l_dataset_v1.json` | Configuration, volume, seed, run identity | `REPRESENTATIVE_SYNTHETIC` | `PASS` as reproducible evidence input |
| Forecast evaluation | `phase_l_forecast_v1.json` | Prophet vs Seasonal Naive across fixed folds | `REPRESENTATIVE_SYNTHETIC` | MAE/WAPE/coverage `FAIL`; RMSE/bias `PASS` |
| Anomaly evaluation | `phase_l_anomaly_v1.json` | Truth alignment, confusion matrix, alert rate, delay | `REPRESENTATIVE_SYNTHETIC` | Alert rate `PASS`; effectiveness `NOT VERIFIED` |
| Maintenance evaluation | `phase_l_maintenance_v1.json` | Random Forest discrimination, ranking, calibration | `REPRESENTATIVE_SYNTHETIC` | PR-AUC/ROC-AUC/precision/top-5% recall `FAIL`; calibration evaluated `PASS` |
| Equipment health | `phase_l_health_v1.json` | Coverage and component decomposition | `REPRESENTATIVE_SYNTHETIC` | Coverage/decomposition `PASS`; confidence `FAIL` |
| Data quality | `phase_l_data_quality_v1.json` | Completeness, validity, duplicates, missing records | `REPRESENTATIVE_SYNTHETIC` | Four measured criteria `PASS`; freshness/communications `NOT VERIFIED` |
| ETL | `phase_l_etl_v1.json` | Capability and representative runtime status | Repository capability + representative context | Audit/lineage/incremental `PARTIAL`; success/recovery `NOT VERIFIED` |
| Database benchmark | `phase_l_database_v1.json` | Clean migration/load/query criteria | Environment record | `NOT VERIFIED` |
| Phase K capability | `artifacts/evaluation/*_phase_k.json` and `docs/models/PHASE_K_ANALYTICAL_EVALUATION.md` | Evaluation architecture and evidence contracts | Capability evidence | Mixed, subordinate to Phase L empirical evidence |
| Governance | `src/eoip/governance/`, `tests/unit/governance/`, Phase M guide | Stable ID, lifecycle, evidence, audit, authorization | Domain/test evidence | Contract `PASS`; durability `PARTIAL` |
| Financial traceability | Phase M guide and governance tests | Assumptions, formulas, unavailability | Domain/test evidence | Architecture `PASS`; Revenue at Risk/ROI/realized benefit `NOT VERIFIED` |

No overall completion percentage is calculated because `PASS`, `FAIL`,
`PARTIAL`, and `NOT VERIFIED` represent different evidence states.

See [reproducibility](REPRODUCIBILITY.md) and the
[Phase L narrative](../models/PHASE_L_EMPIRICAL_VALIDATION.md).
