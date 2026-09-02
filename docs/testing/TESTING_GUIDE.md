# Testing and quality guide

## Test layers

| Layer | Location | Purpose |
|---|---|---|
| Unit | `tests/unit/` | Domain, analytics, API, database, ETL, model, governance, and app behavior |
| Integration | `tests/integration/` | API/provider, ETL, and optional PostgreSQL interaction |
| Acceptance | `tests/acceptance/` | Phase-level behavior and reproducibility |
| End-to-end | `tests/e2e/` | Cross-layer platform flow |
| Performance | `tests/performance/` | Representative volume/runtime assertions |
| Security | `tests/security/` | Secret/configuration and API security behavior |
| UI | `tests/ui/` | Streamlit route rendering and regression constraints |

## Standard commands

```powershell
python -m ruff check .
python -m black --check --no-cache --workers 1 .
python -m pytest tests/unit/app -q --basetemp .pytest_tmp_app
python -m pytest tests/ui -q --basetemp .pytest_tmp_ui
python -m pip check
git diff --check
```

Run the full suite with:

```powershell
$env:PREFECT_HOME = Join-Path (Get-Location) '.prefect_phase_n'
New-Item -ItemType Directory -Force $env:PREFECT_HOME | Out-Null
python -m pytest -q --basetemp .pytest_tmp_phase_n
```

Use repository-local paths on Windows to avoid restricted user temp/state
directories. Do not change tests to conceal permission failures.

## Database integration

Database tests require a disposable PostgreSQL/TimescaleDB instance and
`EOIP_DATABASE_URL`. Without it, they skip explicitly; a skip is not a pass.
Phase L recorded 39 such skips and left migration/query benchmarks `NOT
VERIFIED`. Phase O owns clean migration and performance certification.

## Prefect on Windows

Prefect's temporary server writes SQLite state. A missing/unwritable home may
cause `attempt to write a readonly database`. Create a repository-local
`PREFECT_HOME` before the run and rerun the affected test scope to distinguish
environment failure from product failure.

## Result reporting

Always report collected, passed, failed, skipped, xfailed/xpassed, and warnings.
Test counts are snapshots, not permanent guarantees. Phase N verification is
dated 2026-08-28 in the completion report; the commands above are the enduring
source of truth.
