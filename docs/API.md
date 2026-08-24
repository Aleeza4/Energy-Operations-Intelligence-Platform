# EOIP API

The Phase 11 FastAPI boundary exposes EOIP database services and persisted
intelligence outputs without making the Streamlit application depend on a
running API.

## Start

```powershell
python -m uvicorn eoip.api.app:app --host 127.0.0.1 --port 8000
```

Base path: `/api/v1`  
Swagger UI: `/docs`  
ReDoc: `/redoc`  
OpenAPI: `/openapi.json`

## Authentication

Obtain a bearer token with an OAuth2 form request:

```text
POST /api/v1/auth/token
Content-Type: application/x-www-form-urlencoded

username=<user>&password=<password>
```

Send the resulting token as `Authorization: Bearer <token>`. Bootstrap users
exist only for development demonstrations; production deployments must provide
a strong `EOIP_API_TOKEN_SECRET` and replace bootstrap identities with the
future identity store.

Roles are `viewer`, `operator`, and `admin`. Read routes accept all three roles;
`GET /api/v1/admin/status` requires `admin`.

## Configuration

- `EOIP_API_ENVIRONMENT`
- `EOIP_API_PREFIX`
- `EOIP_API_VERSION`
- `EOIP_API_TOKEN_SECRET` (minimum 32 characters; required for stable tokens)
- `EOIP_API_TOKEN_EXPIRY_MINUTES`
- Existing `EOIP_DATABASE_*` settings configure PostgreSQL.

## Route groups

Health, plants, equipment, SCADA, alarms, incidents, analytics, forecasts,
anomalies, recommendations, authentication, and administration are documented
in OpenAPI. Collection routes use bounded `limit`/`offset` pagination.

## Tests

```powershell
python -m pytest tests\unit\api tests\integration\api -v -p no:cacheprovider
```
