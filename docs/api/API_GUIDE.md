# EOIP API guide

## Start and discovery

```powershell
python -m uvicorn eoip.api.app:app --reload --host 127.0.0.1 --port 8000
```

Configured discovery URLs are `/docs`, `/redoc`, and `/openapi.json`. The API
prefix defaults to `/api/v1` through `EOIP_API_PREFIX`.

## Authentication and authorization

`POST /api/v1/auth/token` accepts OAuth2 password-form credentials and returns
an expiring signed bearer token. Send it as `Authorization: Bearer <token>`.
`GET /api/v1/auth/me` returns the validated principal.

The code defines viewer, operator, and admin bootstrap roles. Viewer/operator/
admin can use read endpoints; `/api/v1/admin/status` requires admin. Production
identity, credential provisioning, rotation, and secret management are not
certified by Phase N. Configure a stable `EOIP_API_TOKEN_SECRET`; the development
fallback is process-generated.

## Configured route inventory

The following inventory comes from router definitions, not a hand-invented API:

| Method and path | Behavior | Access |
|---|---|---|
| `GET /api/v1/health` | Process liveness | Public |
| `GET /api/v1/health/ready` | Database-aware readiness/degraded state | Public |
| `POST /api/v1/auth/token` | Create access token | Credentials |
| `GET /api/v1/auth/me` | Current principal | Authenticated |
| `GET /api/v1/plants` / `{plant_id}` | List/get plants | Reader |
| `GET /api/v1/equipment` / `{equipment_id}` | List/get equipment | Reader |
| `GET /api/v1/scada` / `latest` | Bounded telemetry pages | Reader |
| `GET /api/v1/alarms` / `{alarm_id}` | List/get alarms | Reader |
| `GET /api/v1/incidents` / `{incident_id}` | List/get incidents | Reader |
| `GET /api/v1/analytics/summary` | Stored operational analytics | Reader |
| `GET /api/v1/analytics/plants/{plant_id}` | Plant analytics | Reader |
| `GET /api/v1/forecasts` / `{forecast_id}` | List/get persisted forecasts | Reader |
| `GET /api/v1/anomalies` / `{anomaly_id}` | List/get persisted anomalies | Reader |
| `GET /api/v1/anomalies/evaluation` | Stored evaluation-volume summary | Reader |
| `GET /api/v1/recommendations` / `{recommendation_id}` | List/get optimization recommendations | Reader |
| `GET /api/v1/admin/status` | Safe configuration status | Admin |

List routes support typed pagination and relevant filters. Time-series routes
require bounded time ranges. Unknown identifiers use structured 404 errors;
authentication and role failures use 401/403 responses.

## Recommendation behavior

Recommendation endpoints are read-only. They do not assign owners, approve,
defer, reject, complete, or persist governance history. Phase M's in-memory
domain store is a tested architecture boundary, not durable API workflow.

## Phase N runtime verification

Fresh-process OpenAPI inspection of `eoip.api.app:app` confirmed all 24 paths
listed above, and an in-process request to `/api/v1/health` returned HTTP 200.
This verifies route registration and process liveness; it does not certify
database contents, clean migrations, readiness against TimescaleDB, production
identity integration, or deployment networking. Those remain Phase O scope.

See [deployment](../deployment/DEPLOYMENT_GUIDE.md) for infrastructure limits.
