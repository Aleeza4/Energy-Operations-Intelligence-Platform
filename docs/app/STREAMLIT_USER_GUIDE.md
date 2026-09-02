# Streamlit user guide

## Start and data scope

```powershell
python -m streamlit run src/eoip/app/main.py
```

The application uses a grouped custom sidebar and 11 renderer modules. It
currently loads fresh deterministic frames from `src/eoip/app/data_access.py`.
It is not a live telemetry console or durable governance client.

Global plant/equipment/date filters are rendered where supported and applied by
`PageDataContract`. Drill-down navigation carries plant/equipment context in
Streamlit session state. CSV downloads reflect the selected scope.

## Navigation and pages

| Group / page | Questions answered | Main content and filters | Drill-down / limitation |
|---|---|---|---|
| Overview — Executive | How is portfolio generation tracking plan? Which exceptions and priorities need attention? | Portfolio KPIs, actual/expected comparison, attention queue, plant comparison, governed priorities | Links to performance, operations, recommendations; monetary impact unavailable |
| Operations — Operations | What is the current representative operating state? | Status KPIs, plant status, trend/context tables, active attention items; plant scope | Links to asset, anomaly, maintenance/performance; not live data |
| Operations — Plant Performance | Which plant is below expected generation? | Actual/expected energy, variance, PR, capacity factor, availability; plant scope | Links to assets, operations, incidents, anomaly |
| Operations — Asset Dashboard | Which equipment needs review? | Health/risk distribution, asset table and detail; plant/equipment scope | Links to anomaly, maintenance, recommendations, plant performance |
| Operations — Alarms & Incidents | What events, response times, and downtime are represented? | Alarm/incident KPIs and tables; plant/equipment/date scope | Event records are deterministic representative data |
| Intelligence — Forecast | What generation path and uncertainty bounds are displayed? | Forecast series, interval, model context; date scope, portfolio forecast | Links to operations; Phase L model failures remain limitations |
| Intelligence — Anomaly | Which abnormal records require investigation? | Severity/method counts, anomaly scores and detail; plant/equipment scope | Related investigation links; no causal claim |
| Intelligence — Maintenance | How are equipment attention priorities ranked? | Failure risk, health, priority and detail; plant/equipment scope | Model discrimination is weak; links to assets/recommendations/operations |
| Intelligence — Recommendation Center | Why is an action proposed and what evidence/finance supports it? | Stable ID, priority, provenance, status, owner, evidence and financial availability | Links across workflow; no durable write buttons or money claims |
| Platform — Data Quality | Are application datasets structurally complete and valid? | Dataset coverage, validation, quality tables | Application-frame quality is not production SLA evidence |
| Platform — Administration | What safe configuration/platform information is available? | Environment, navigation, design and configuration summaries | No secrets or destructive administration |

## Recommendation interpretation

Demo recommendations initialize `PROPOSED` and `Unassigned`. This is not
historical approval or assignment. Evidence links use explicit semantics;
current anomaly references are `RELATED_TO`, not causal. Financial conversion,
Revenue at Risk, ROI, and realized benefit remain unavailable because approved
business assumptions and outcomes do not exist.

## Known application limits

- Deterministic representative application records, separate from Phase L's
  larger representative dataset.
- No direct database/API-backed UI runtime is verified.
- Session state preserves navigation/filter context, not enterprise workflow.
- Forecast, anomaly, maintenance, and health views inherit Phase L limitations.
- The UI was not modified during documentation-only Phase N.
