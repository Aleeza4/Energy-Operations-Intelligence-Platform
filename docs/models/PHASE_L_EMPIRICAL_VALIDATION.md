# Phase L empirical validation

Phase L evidence is representative synthetic engineering evidence. It is not
production performance evidence and does not establish performance at a
real-world deployment scale.

## Reproduce

From the repository root, using the project virtual environment:

```powershell
.\.venv\Scripts\python.exe scripts\generate_phase_l_evidence.py
```

For byte-stable evaluation timestamps in an audited run:

```powershell
.\.venv\Scripts\python.exe scripts\generate_phase_l_evidence.py `
  --evaluated-at 2026-08-27T00:00:00+00:00
```

Artifacts are written to `artifacts/evaluation/phase_l/`. The workflow uses
seed `20260827`, two plants, 15-minute observations from 2025-01-01 through
2025-03-02 (exclusive), and chronological train/validation/test boundaries.
Synthetic events are scheduled independently of detector output. Maintenance
labels include only failures strictly after an observation and within the
documented 24-hour horizon.

Database artifacts remain `NOT VERIFIED` unless a safe PostgreSQL/TimescaleDB
environment is available. The workflow never interprets an absent database,
an empty table, or a completed query without timeout instrumentation as a
passing database criterion.

## Test safely on Windows

Prefect needs a writable local state directory in restricted environments:

```powershell
$env:PREFECT_HOME = Join-Path (Get-Location) '.prefect_phase_l_full'
.\.venv\Scripts\python.exe -m pytest -q `
  --basetemp .pytest_tmp_phase_l_full
```

The evidence classifications follow the Phase K status semantics: measured
criteria are `PASS` or `FAIL`; incomplete capability is `PARTIAL`; absent or
insufficient evidence remains `NOT VERIFIED`.
