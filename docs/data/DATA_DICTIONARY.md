# EOIP data dictionary

This dictionary summarizes major entities from actual dataclasses, ORM models,
API schemas, and application frames. It is not a replacement for those typed
sources.

| Entity | Purpose and identifier | Important fields | Time semantics | Source/classification |
|---|---|---|---|---|
| Plant | Renewable generation site; `plant_id` | name, region, coordinates, AC/DC capacity, status, timezone | commissioning date; audit timestamps | Synthetic representative; ORM configured |
| Equipment | Plant asset; `equipment_id` | type, manufacturer/model, serial, rating, parent, status | commissioning date; audit timestamps | Synthetic representative; ORM configured |
| SCADA | Equipment observation; composite plant/equipment/time identity | power, interval energy, electrical channels, availability, state, quality | timezone-aware observation timestamp | Synthetic/Phase L representative; ORM time-series configured |
| Plant SCADA | Plant-level generation observation | actual/expected energy and environmental/operating context | UTC interval timestamp | Synthetic representative; no identical application/ORM schema |
| Weather | Station observation attributed to plant | irradiance, temperatures, wind, humidity, quality | timezone-aware observation timestamp | Synthetic representative; ORM time-series configured |
| Alarm | Operational alert; `alarm_id` | plant/equipment, code, severity, status, message, ground-truth flag | raised, acknowledged, cleared | Synthetic representative; ORM configured |
| Incident | Operational event; `incident_id` | category, severity, status, optional alarm link, root cause | occurred, detected, resolved | Synthetic representative; ORM configured |
| Work order | Maintenance action record; `work_order_id` | type, priority, status, team, labor/cost, optional incident link | created, scheduled, started, completed/cancelled | Synthetic representative; ORM configured |
| Forecast | Stored forecast output; `forecast_id` | model, target timestamp, prediction, lower/upper bounds | issued/target timestamps | Model output; provider/storage contract |
| Anomaly | Stored detector output; `anomaly_id` | method, score, threshold/context | observation/detection timestamps | Model output; provider/storage contract |
| Maintenance priority | Ranked analytical attention record | equipment, failure probability, health, risk, priority | evaluation scope dependent | Model output or representative application data |
| Recommendation | Governed decision-support item; stable `REC-` ID | source identity, plant/equipment, type, action, rationale, rank, status, owner | no fabricated creation history | Representative application source; governed classifications |
| Evidence reference | Link from recommendation to source record | evidence type/source/ID, relationship, plant/equipment, description | optional UTC observed time | Same classification as referenced evidence |
| Governance audit event | Append-oriented workflow fact | event type, prior/new value, actor, note | timezone-aware UTC `occurred_at` | `USER_ENTERED` or explicit configured actor |
| Financial assumption | Versioned conversion input | currency, energy price, horizon, version | horizon is explicit; no silent date defaults | `CONFIGURED`, test-only representative, or unavailable |

## Application frame differences

The Streamlit data boundary uses display-oriented columns (`Plant`, `Equipment
ID`, `Actual Energy (MWh)`, and similar). Recommendation exports additionally
include source classifications, evidence semantics, financial availability,
and assumption fields. These frames are fresh deterministic snapshots and are
not durable workflow tables.

## Timestamp rules

- Internal time-series and audit timestamps use timezone-aware UTC.
- Effective and commissioning dates are date-valued business fields.
- Phase L split boundaries and evaluated timestamps are persisted in artifacts.
- Existing demo recommendations have no fabricated historical timestamps.

## Units and money

Power and energy fields retain explicit kW/kWh/MW/MWh units. Recoverable energy
is not financial impact. Monetary calculation requires currency, price/cost,
horizon, formula, classifications, and assumption version. Current Revenue at
Risk, ROI, and realized benefit are `NOT VERIFIED`.
