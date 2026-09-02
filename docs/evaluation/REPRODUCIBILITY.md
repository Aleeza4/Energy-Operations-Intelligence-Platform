# Phase L reproducibility

## Evidence contract

Phase L artifacts are `REPRESENTATIVE_SYNTHETIC`. They demonstrate deterministic
data/evaluation engineering and do not claim production performance. The
canonical artifacts are under `artifacts/evaluation/phase_l/` and use schema
version `1.0`.

## Fixed configuration

| Setting | Value |
|---|---|
| Seed | `20260827` |
| Evaluated timestamp | `2026-08-27T00:00:00+00:00` |
| Data period | `[2025-01-01T00:00:00Z, 2025-03-02T00:00:00Z)` |
| Resolution | 15 minutes |
| Plants | 2 |
| Dataset/run ID | `RUN-20250101T000000Z-20260827` |
| Configuration fingerprint | `6f3353ca3450d690caf15f9f016c1c457aab698914166d94a544ddbb824d6d74` |

## Reproduce

From an installed repository environment:

```powershell
.\.venv\Scripts\python.exe scripts\generate_phase_l_evidence.py `
  --evaluated-at 2026-08-27T00:00:00+00:00
```

The default output is `artifacts/evaluation/phase_l/`. For comparison without
overwriting audited artifacts, use an alternate output directory:

```powershell
.\.venv\Scripts\python.exe scripts\generate_phase_l_evidence.py `
  --evaluated-at 2026-08-27T00:00:00+00:00 `
  --output artifacts/evaluation/phase_l_reproduction
```

Generation duration and platform metadata may vary by machine; compare semantic
metrics/configuration deliberately. Do not overwrite evidence to improve it.

## Evaluation stages

1. Generate typed synthetic plants, equipment, telemetry, weather, events,
   alarms, incidents, work orders, tariffs, and budgets.
2. Reconstruct independently scheduled ground-truth events and apply effects.
3. Forecast plant generation using three expanding-window folds; compare
   Prophet to Seasonal Naive.
4. Evaluate Isolation Forest predictions against eligible independent truth and
   calculate false alerts per asset-day/detection delay when defined.
5. Create future-only 24-hour failure labels, chronological splits, train the
   Random Forest, and persist discrimination/ranking/calibration metrics.
6. Calculate equipment-health component decomposition and population coverage.
7. Evaluate telemetry completeness, validity, duplicates, and missing records.
8. Record ETL/database criteria honestly when representative runtime evidence
   is unavailable.

## Leakage controls

- Ground truth is scheduled before detector execution.
- Forecast folds train only on earlier timestamps.
- Maintenance labels use failures strictly after each observation.
- No post-failure or future incident features enter maintenance training.
- Missing history, confidence, database results, or business assumptions are not
  synthesized.

## Artifact hashes recorded before Phase N

| Artifact | SHA-256 |
|---|---|
| `phase_l_anomaly_v1.json` | `C4DA18E11E1AA7CDED0C2090F62BE4D5C123BF2FCDB49174E05EBF3F055A5AC6` |
| `phase_l_data_quality_v1.json` | `489B63BAE9369DDC1C336C3CA1567CB4B59A7D808150AF7AB4CF5C7347031AC6` |
| `phase_l_database_v1.json` | `C755052DC9C978938B41847FAFA59854097116FA21EB424222BFADAD17B9717E` |
| `phase_l_dataset_v1.json` | `A6545C2A59BD429E21D78535C24104C367F97B6EF8EC66C3EA7396D171A84741` |
| `phase_l_etl_v1.json` | `9260721D03DB18F164F8C7ACD56BA82B82CF656D37B48AEBD4F37A78A183B8D3` |
| `phase_l_forecast_v1.json` | `41226E0ADABE69CEF631A0AC892FD2F68C8A12A80E356FB4BCEE7DDBB8DCA5AC` |
| `phase_l_health_v1.json` | `45C4E498AF54225336A6C9F4A0D7A698AC0CE55CB439C86A05616EC8F2D01028` |
| `phase_l_maintenance_v1.json` | `26EAC021E5C5418C1E020F2297183233E7EC5661B33964D1E02CC40EAD6618EA` |

Verify after documentation changes:

```powershell
Get-ChildItem artifacts/evaluation/phase_l/*.json |
  Get-FileHash -Algorithm SHA256
```
