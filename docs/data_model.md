# Energy Operations Intelligence Platform
## Data Model Design

**Document:** Data Model
**Version:** 1.0
**Status:** Draft
**Project:** Energy Operations Intelligence Platform

---

# 1. Purpose

This document defines the logical data model for the Energy Operations Intelligence Platform.

The model is designed to support:

- 15-minute SCADA telemetry
- solar plant and equipment hierarchy
- weather analytics
- RMS alarms and operator actions
- incidents and outages
- maintenance and component replacement
- tariffs, load, budgets and costs
- forecasting and anomaly detection
- recommendation tracking
- ETL auditability
- machine-learning ground-truth evaluation

The design follows a hybrid analytical model:

- dimension tables for stable descriptive entities
- fact tables for operational and time-series events
- explicit foreign-key relationships
- canonical units and measurement conventions
- auditable model outputs and operator feedback

---

# 2. Design Principles

1. Every operational fact must be traceable to a plant.
2. Equipment-level facts must reference `dim_equipment`.
3. All timestamps must be stored in UTC.
4. Canonical units must follow `configs/units.yaml`.
5. Raw telemetry and curated analytics must remain distinguishable.
6. Simulation scenarios must retain ground-truth labels.
7. Model alerts and recommendations must support human review.
8. Financial estimates must retain assumptions and source references.
9. High-volume time-series tables must support partitioning or hypertables.
10. Referential integrity must be enforced wherever practical.

---

# 3. Model Domains

The data model is divided into the following domains:

- Portfolio and Asset Master Data
- Sensor and Measurement Governance
- Calendar and Time Intelligence
- Fault and Alarm Management
- SCADA and Weather Telemetry
- Incident and Grid Operations
- Maintenance and Component Replacement
- Tariff, Load, Budget and Financial Data
- Forecasting and Machine Learning
- Recommendation and Action Tracking
- ETL Audit and Platform Governance

---

# 4. Dimension Tables

The dimension layer contains descriptive entities that change less frequently than operational facts.

## 4.1 `dim_plant`

Purpose: Stores plant-level technical, geographic, contractual and performance attributes.

Primary key:

```text
plant_id

## 4.2 `dim_equipment`

**Purpose:** Stores the complete physical asset hierarchy for inverters, transformers, feeders, meters, relays, and weather stations.

**Primary key:**

```text
equipment_id
```

**Foreign keys:**

```text
plant_id → dim_plant.plant_id
parent_equipment_id → dim_equipment.equipment_id
```

The self-referencing parent key supports the following hierarchy:

```text
Plant
└── Transformer
    └── Feeder
        └── Inverter
            └── Sensor
```

## 4.3 `dim_sensor`

**Purpose:** Defines sensor metadata, measurement type, unit, accuracy, and calibration requirements.

**Primary key:**

```text
sensor_id
```

**Foreign key:**

```text
equipment_id → dim_equipment.equipment_id
```

## 4.4 `dim_fault_code`

**Purpose:** Standardizes fault classifications, severity, probable cause, SLA expectations, and recommended response.

**Primary key:**

```text
fault_code
```

## 4.5 `dim_calendar`

**Purpose:** Supports time-based filtering, aggregation, tariff periods, and seasonality.

**Primary key:**

```text
timestamp_utc
```

The model uses 15-minute interval-end timestamps.

## 4.6 `dim_operator`

**Purpose:** Stores operator, team, shift, and role attributes used for alarm-response analytics.

**Primary key:**

```text
operator_id
```

## 4.7 `dim_simulation_scenario`

**Purpose:** Stores injected synthetic scenarios and their expected operational and financial effects.

**Primary key:**

```text
scenario_id
```

**Foreign keys:**

```text
plant_id → dim_plant.plant_id
equipment_id → dim_equipment.equipment_id
```

# 5. Fact Tables

## 5.1 `fact_scada_reading`

**Purpose:** Stores 15-minute equipment telemetry and operational state.

**Recommended grain:**

```text
One row per equipment item per 15-minute interval
```

**Composite natural key:**

```text
timestamp_utc + equipment_id
```

**Recommended physical design:**

- TimescaleDB hypertable on `timestamp_utc`
- Partitioning by time
- Index on `(equipment_id, timestamp_utc)`
- Index on `(plant_id, timestamp_utc)`
- Compression for historical intervals

## 5.2 `fact_weather`

**Purpose:** Stores plant-level weather and irradiance observations.

**Recommended grain:**

```text
One row per plant per 15-minute interval
```

**Natural key:**

```text
timestamp_utc + plant_id
```

## 5.3 `fact_alarm_event`

**Purpose:** Stores the lifecycle of every RMS or SCADA alarm.

**Recommended grain:**

```text
One row per alarm occurrence
```

**Primary key:**

```text
alarm_event_id
```

**Important relationships:**

```text
plant_id → dim_plant
equipment_id → dim_equipment
fault_code → dim_fault_code
acknowledged_by → dim_operator
parent_incident_id → fact_incident
```

## 5.4 `fact_alarm_action`

**Purpose:** Stores every operator action taken against an alarm.

**Recommended grain:**

```text
One row per action per alarm
```

**Foreign keys:**

```text
alarm_event_id → fact_alarm_event
operator_id → dim_operator
```

## 5.5 `fact_incident`

**Purpose:** Stores operational incidents, outage classification, lost energy, and financial impact.

**Recommended grain:**

```text
One row per incident
```

**Primary key:**

```text
incident_id
```

## 5.6 `fact_grid_event`

**Purpose:** Stores grid unavailability, voltage events, frequency events, curtailment, and export limits.

**Recommended grain:**

```text
One row per grid event
```

## 5.7 `fact_work_order`

**Purpose:** Stores maintenance work orders and their operational and financial outcomes.

**Recommended grain:**

```text
One row per work order
```

## 5.8 `fact_component_replacement`

**Purpose:** Stores component replacements linked to maintenance activity.

**Recommended grain:**

```text
One row per replaced component
```

## 5.9 `fact_tariff`

**Purpose:** Stores time-dependent import, export, and demand-charge rates.

**Recommended grain:**

```text
One row per region, tariff type, and effective interval
```

## 5.10 `fact_load`

**Purpose:** Stores regional or feeder-level demand measurements.

**Recommended grain:**

```text
One row per feeder per 15-minute interval
```

## 5.11 `fact_budget_target`

**Purpose:** Stores monthly plant-level generation, revenue, reliability, and cost targets.

**Recommended grain:**

```text
One row per plant per budget period
```

## 5.12 `fact_forecast`

**Purpose:** Stores model predictions, confidence intervals, and actual values.

**Recommended grain:**

```text
One row per forecast run, plant, target timestamp, and forecast type
```

## 5.13 `fact_model_alert`

**Purpose:** Stores anomaly, failure-risk, and health-related model alerts with operator feedback.

**Recommended grain:**

```text
One row per model alert
```

## 5.14 `fact_recommendation_action`

**Purpose:** Tracks recommendations from creation through implementation and realized benefit.

**Recommended grain:**

```text
One row per recommendation
```

## 5.15 `fact_etl_run`

**Purpose:** Stores pipeline audit information and data-quality outcomes.

**Recommended grain:**

```text
One row per ETL pipeline run
```

# 6. Relationship Summary

```text
dim_plant
├── dim_equipment
│   ├── dim_sensor
│   ├── fact_scada_reading
│   ├── fact_alarm_event
│   ├── fact_incident
│   ├── fact_work_order
│   ├── fact_component_replacement
│   ├── fact_model_alert
│   └── fact_recommendation_action
│
├── fact_weather
├── fact_grid_event
├── fact_budget_target
├── fact_forecast
└── dim_simulation_scenario

dim_fault_code
└── fact_alarm_event

dim_operator
├── fact_alarm_action
├── fact_alarm_event
└── fact_model_alert

fact_incident
├── fact_alarm_event
└── fact_work_order

fact_work_order
└── fact_component_replacement
```

# 7. Key Design Decisions

## 7.1 SCADA Grain

SCADA telemetry is stored at equipment level rather than plant level.

This supports:

- Inverter comparison
- Equipment anomaly detection
- Fault propagation analysis
- Plant aggregation
- Equipment health scoring

## 7.2 Plant-Level Weather

Weather is stored at plant level because one or more weather stations typically represent the site.

Sensor-level weather data may be introduced later through `dim_sensor`.

## 7.3 Alarm and Action Separation

Alarm events and operator actions are separated because a single alarm may have multiple actions, escalations, and notes.

## 7.4 Incident and Alarm Separation

Multiple alarms may belong to one operational incident.

This avoids overstating incident counts during alarm storms.

## 7.5 Forecast Persistence

Forecasts are stored rather than calculated only in memory.

This enables:

- Forecast-versus-actual reporting
- Model comparison
- Model-version tracking
- Backtesting
- Auditability

## 7.6 Human Feedback

Model alerts include operator feedback and review outcomes.

This supports:

- False-positive analysis
- Model retraining
- Operator trust
- Closed-loop learning

# 8. High-Volume Tables

The following tables are expected to contain the largest volumes:

| Table | Expected Scale | Recommended Storage |
|---|---:|---|
| `fact_scada_reading` | Millions of rows | TimescaleDB hypertable |
| `fact_weather` | Hundreds of thousands | TimescaleDB hypertable |
| `fact_load` | Hundreds of thousands | TimescaleDB hypertable |
| `fact_forecast` | Potentially millions | Partitioned table or hypertable |
| `fact_alarm_event` | Thousands to millions | Indexed relational table |

# 9. Data Quality Rules

The model must enforce:

- Unique primary keys
- Valid plant and equipment foreign keys
- UTC timestamps
- Canonical units
- Non-negative interval energy
- Valid operating states
- Valid severity codes
- Start timestamp not later than end timestamp
- Total cost equals labor cost plus parts cost where applicable
- Cumulative readings handled using reset-aware logic
- Data-quality codes retained for invalid or uncertain readings

# 10. Future Extensions

The model may later support:

- Battery energy storage systems
- Wind turbines
- String-level telemetry
- Spare-parts inventory
- Contractor management
- GIS layers
- Asset ownership structures
- Market bidding and dispatch
- Carbon accounting
- Digital-twin outputs

---

**End of Document**
