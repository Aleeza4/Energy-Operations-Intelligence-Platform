# Deployment guide

This guide documents configured deployment assets. It does not certify Phase O.

## Local services

Create `.env` from `.env.example` and configure database credentials, a stable
API token secret, and optional API settings. Never commit `.env`.

```powershell
python -m uvicorn eoip.api.app:app --host 127.0.0.1 --port 8000
python -m streamlit run src/eoip/app/main.py
```

Configured health paths are `/api/v1/health` for liveness and
`/api/v1/health/ready` for database-aware readiness. The Streamlit container
uses `/_stcore/health`.

## Database and migrations

The database settings include host, port, name, user, and password. Migrations
consume the application database configuration through `migrations/env.py`.
With a disposable configured database:

```powershell
python -m alembic upgrade head
python -m alembic current
```

Do not run migrations against an unknown or production database during
verification. Clean migration, rollback/recovery, hypertable conversion,
continuous aggregates, representative loading, and query performance remain
`NOT VERIFIED` until Phase O.

## Containers and Compose

`Dockerfile.api` starts Uvicorn on port 8000 as a non-root user.
`Dockerfile.streamlit` starts the app on port 8501 as a non-root user.
`docker-compose.yml` defines TimescaleDB, a migration job, API, and Streamlit
services with health/dependency conditions.

The Compose file references prebuilt image tags `eoip-api:phase13` and
`eoip-streamlit:phase13`; it does not define `build:` sections. Example builds,
not certified in Phase N, are:

```powershell
docker build -f Dockerfile.api -t eoip-api:phase13 .
docker build -f Dockerfile.streamlit -t eoip-streamlit:phase13 .
docker compose up
```

## Configuration and secrets

Important variables include:

- `EOIP_DATABASE_HOST`, `PORT`, `NAME`, `USER`, `PASSWORD`
- `EOIP_DATABASE_URL` for integration/runtime paths that require a full URL
- `EOIP_API_ENVIRONMENT`, `PREFIX`, `VERSION`
- `EOIP_API_TOKEN_SECRET`, `EOIP_API_TOKEN_EXPIRY_MINUTES`
- `EOIP_LOG_LEVEL`

Compose currently includes demonstrative database credentials. Production
secret management, TLS, network policies, external identity, backups,
observability, scaling, and rotation are deployment responsibilities.

## Verification status

| Area | Status |
|---|---|
| Dockerfile definitions | `CONFIGURED` |
| Docker builds | `NOT VERIFIED` in Phase N |
| Compose networking/startup | `NOT VERIFIED` |
| Clean TimescaleDB migration | `NOT VERIFIED` |
| API route registration and liveness | `VERIFIED` in-process during Phase N; deployed networking `NOT VERIFIED` |
| Query performance/continuous aggregates | `NOT VERIFIED` |
| Production secret management | `NOT VERIFIED` |
| Streamlit deterministic local UI | Tested application behavior |

Phase O should certify these areas in a disposable environment without changing
model evidence.
