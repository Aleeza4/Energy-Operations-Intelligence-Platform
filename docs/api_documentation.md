# EOIP API Documentation

## 1. Overview

The Energy Operations Intelligence Platform exposes a versioned REST API that provides secure access to operational plant data, telemetry, asset status, event intelligence, forecast outputs, anomaly evaluations, and recommendation records. The API is implemented with FastAPI and is designed to support both dashboard consumers and operational service integrations.

The canonical runtime interface is configured through the EOIP application factory and mounted under the API prefix used by the deployment environment. The application exposes read-only operational data endpoints and a minimal authentication flow for secure access.

---

## 2. Base Configuration

### Base URL

The application is exposed under the configured API prefix. In the default local configuration, the service is typically available at:

- http://localhost:8000/api/v1

### Core endpoints

- Swagger UI: /docs
- ReDoc: /redoc
- OpenAPI schema: /openapi.json

### Service metadata

- Title: Energy Operations Intelligence Platform API
- Summary: EOIP API
- Version: defined by the runtime settings
- Authentication: OAuth2 bearer token flow

---

## 3. Authentication Model

The EOIP API uses bearer-token authentication with a role-based access model.

### Supported roles

- viewer
- operator
- admin

### Token flow

1. Call the token endpoint with form credentials.
2. Receive an access token and expiry value.
3. Include the token in the Authorization header for protected requests.

Example:

Authorization: Bearer <token>

### Authentication endpoint

| Method | Route | Description |
| --- | --- | --- |
| POST | /api/v1/auth/token | Authenticate a known user and issue a signed bearer token |
| GET | /api/v1/auth/me | Return the current authenticated principal and role |

### Bootstrap users

The system ships with bootstrap users for demonstration and internal testing. These identities are intended for development use and should be replaced or removed in production with a proper long-term identity provider.

---

## 4. Authorization Rules

The API enforces role-aware access at the route level.

| Access level | Typical allowed routes |
| --- | --- |
| viewer | plant, equipment, telemetry, alarm, incident, analytics, forecast, anomaly, recommendation reads |
| operator | same as viewer, with operational context focused access |
| admin | all reads plus privileged administrative health/status information |

The administrative status route is restricted to admins.

---

## 5. Common API Behaviors

### Pagination

Collection routes use a consistent paginated response envelope.

Response shape:

- items: list of records
- total: total matched records
- limit: page size
- offset: starting offset

### Time ranges

Operational query endpoints typically accept start_time and end_time parameters. The API rejects reversed time ranges.

### Filtering

Routes support selective filtering using common query parameters such as:

- plant_id
- equipment_id
- status
- severity
- model_name
- recommendation_type
- method

### Error handling

The API returns structured errors with a status code and an application-defined error code where applicable. Common patterns include:

- 401 unauthorized
- 404 not found
- 422 invalid input
- 500 internal server error

---

## 6. Route Inventory

## 6.1 Health and readiness

| Method | Route | Description |
| --- | --- | --- |
| GET | /api/v1/health | Returns the service liveness status |
| GET | /api/v1/health/ready | Returns service status plus dependency readiness |

Example response:

{
  "status": "healthy",
  "service": "eoip-api",
  "version": "<version>",
  "environment": "<environment>",
  "dependencies": {
    "database": "available"
  }
}

---

## 6.2 Plants

| Method | Route | Description |
| --- | --- | --- |
| GET | /api/v1/plants | List plants with optional status filter |
| GET | /api/v1/plants/{plant_id} | Get a single plant by identifier |

### Query parameters

- status: optional plant status
- limit: page size
- offset: page offset

### Typical payload

- plant_id
- plant_name
- region
- latitude
- longitude
- dc_capacity_mw
- ac_capacity_mw
- commissioning_date
- status
- timezone_name

---

## 6.3 Equipment

| Method | Route | Description |
| --- | --- | --- |
| GET | /api/v1/equipment | List equipment |
| GET | /api/v1/equipment/{equipment_id} | Get one equipment asset |

### Query parameters

- plant_id
- equipment_type
- status
- limit
- offset

### Typical payload

- equipment_id
- plant_id
- equipment_name
- equipment_type
- manufacturer
- model_number
- serial_number
- commissioning_date
- rated_power_kw
- parent_equipment_id
- status

---

## 6.4 SCADA telemetry

| Method | Route | Description |
| --- | --- | --- |
| GET | /api/v1/scada | Query telemetry time-series data |
| GET | /api/v1/scada/latest | Return the latest telemetry observations |

### Query parameters

- plant_id
- equipment_id
- start_time
- end_time
- limit
- offset

### Typical payload

- plant_id
- equipment_id
- timestamp
- active_power_kw
- interval_energy_kwh
- dc_voltage_v
- dc_current_a
- ac_voltage_v
- ac_current_a
- frequency_hz
- power_factor
- equipment_available
- grid_available
- operating_state
- quality

### Notes

This endpoint is optimized for bounded operational reads and is designed to support dashboards and near-real-time monitoring views.

---

## 6.5 Alarms

| Method | Route | Description |
| --- | --- | --- |
| GET | /api/v1/alarms | List alarm records |
| GET | /api/v1/alarms/{alarm_id} | Get one alarm |

### Query parameters

- plant_id
- equipment_id
- severity
- status
- start_time
- end_time
- limit
- offset

### Typical payload

- alarm_id
- plant_id
- equipment_id
- alarm_code
- alarm_name
- category
- severity
- raised_at
- status
- acknowledged_at
- cleared_at
- message

---

## 6.6 Incidents

| Method | Route | Description |
| --- | --- | --- |
| GET | /api/v1/incidents | List incidents |
| GET | /api/v1/incidents/{incident_id} | Get one incident |

### Query parameters

- plant_id
- equipment_id
- severity
- status
- start_time
- end_time
- limit
- offset

### Typical payload

- incident_id
- plant_id
- equipment_id
- incident_name
- category
- severity
- occurred_at
- status
- detected_at
- resolved_at
- description
- root_cause
- linked_alarm_id

---

## 6.7 Analytics summary

| Method | Route | Description |
| --- | --- | --- |
| GET | /api/v1/analytics/summary | Return a stored operational analytics summary |
| GET | /api/v1/analytics/plants/{plant_id} | Return analytics for one plant |

### Query parameters

- plant_id
- start_time
- end_time
- metrics (optional list of selected metric groups)

### Output characteristics

The summary response includes:

- plant_id
- start_time
- end_time
- units
- plant_operations
- scada_hourly
- open_alarms
- open_incidents

This endpoint is aligned to analytical dashboards and summary scorecards, typically derived from persisted operational intelligence stores.

---

## 6.8 Forecasts

| Method | Route | Description |
| --- | --- | --- |
| GET | /api/v1/forecasts | List persisted forecasts |
| GET | /api/v1/forecasts/{forecast_id} | Get one forecast record |

### Query parameters

- model_name
- horizon
- limit
- offset

### Typical payload

- forecast_id
- model_name
- target_column
- generated_at
- row_count
- units
- values: list of timestamp and prediction pairs

---

## 6.9 Anomalies

| Method | Route | Description |
| --- | --- | --- |
| GET | /api/v1/anomalies | List anomalies |
| GET | /api/v1/anomalies/evaluation | Get stored anomaly evaluation summary |
| GET | /api/v1/anomalies/{anomaly_id} | Get one anomaly |

### Query parameters

- method
- start_time
- end_time
- limit
- offset

### Typical payload

- anomaly_id
- anomaly_run_id
- timestamp
- score
- detector_name
- target_column
- generated_at
- severity
- status

---

## 6.10 Recommendations

| Method | Route | Description |
| --- | --- | --- |
| GET | /api/v1/recommendations | List persisted optimization recommendations |
| GET | /api/v1/recommendations/{recommendation_id} | Return one recommendation |

### Query parameters

- plant_id
- equipment_id
- recommendation_type
- minimum_priority
- economically_justified
- limit
- offset

### Typical payload

- recommendation_id
- plant_id
- equipment_id
- recommendation_type
- action
- rationale
- priority_rank
- priority_score
- risk_score
- recoverable_energy_kwh
- expected_benefit
- net_financial_impact
- roi_percent
- economically_justified

---

## 6.11 Administration

| Method | Route | Description |
| --- | --- | --- |
| GET | /api/v1/admin/status | Return admin-safe API status information |

This route is protected and accessible only to the admin role. It returns a concise operational status snapshot and indicates whether the database configuration is present.

---

## 7. Example Requests

## 7.1 Obtain a token

POST /api/v1/auth/token
Content-Type: application/x-www-form-urlencoded

username=operator&password=<password>

## 7.2 Get plants

GET /api/v1/plants?limit=20&offset=0
Authorization: Bearer <token>

## 7.3 Query telemetry

GET /api/v1/scada?plant_id=PLANT-001&start_time=2026-01-01T00:00:00Z&end_time=2026-01-02T00:00:00Z&limit=100
Authorization: Bearer <token>

## 7.4 Get active alarms

GET /api/v1/alarms?severity=critical&status=open&limit=25
Authorization: Bearer <token>

## 7.5 Get recommendations

GET /api/v1/recommendations?plant_id=PLANT-001&minimum_priority=0.5
Authorization: Bearer <token>

---

## 8. Data Contract Notes

The API response models are intentionally typed and aligned to the EOIP persistence layer. Collection endpoints wrap arrays in a Page object, and single-resource endpoints return object-shaped payloads using the same schema definitions used in the OpenAPI specification.

The functional emphasis of the interface is read access to operational intelligence and persisted model output, rather than direct write operations. This design keeps the platform aligned to monitoring, analytics, and decision support workflows.

---

## 9. Operational Guidance

- Use the health route to confirm the service is running.
- Use the ready route to confirm dependencies are available.
- Use role-based access to separate viewer, operational, and admin responsibilities.
- Prefer filtered, bounded queries for dashboard performance and operational reliability.
- Use the analytics, forecast, anomaly, and recommendation endpoints together for end-to-end operational intelligence workflows.

---

## 10. Summary

The EOIP API is built to provide a secure, structured, and dashboard-friendly interface to the platform’s operational and analytical data. It exposes a clear separation between plant metadata, asset telemetry, operational events, analytics summaries, forecast outputs, anomaly detection results, and optimization recommendations, while keeping access patterns simple and predictable for downstream clients.
