# EOIP Data Dictionary

## 1. Purpose

This data dictionary documents the core database tables used by the Energy Operations Intelligence Platform (EOIP). It is intended to help technical reviewers, project stakeholders, and analysts understand the structure of the platform’s operational data model and the key fields used across reporting, analytics, and dashboarding.

The dictionary focuses on the primary operational and analytical entities in the EOIP schema, including plant metadata, equipment, telemetry, weather, alarms, incidents, maintenance, budgets, tariffs, and model-supporting ground-truth events.

---

## 2. Conventions Used

- Primary key fields are labeled as such.
- Foreign keys indicate relationships to parent tables.
- Time-series tables are designed around timestamp-based queries and operational analytics.
- All tables include audit-related metadata such as created or updated timestamps where relevant.
- Field names are written in a consistent, database-oriented format.

---

## 3. Table Summary

| Table | Purpose | Key Relationship |
| --- | --- | --- |
| `plants` | Master data for each generation site | Parent to most operational tables |
| `equipment` | Asset inventory and hierarchy | Child of plants |
| `weather_observations` | Environmental conditions by site | Child of plants |
| `scada_observations` | Time-series operating telemetry | Child of plants and equipment |
| `alarms` | Active or historical alarm events | Child of plants and equipment |
| `incidents` | Significant operational events | Child of plants and equipment |
| `work_orders` | Maintenance tasks and service actions | Child of plants and equipment |
| `budgets` | Plant spend and allocation history | Child of plants |
| `tariffs` | Rate structures and commercial conditions | Child of plants |
| `ground_truth_events` | Validation and evaluation labels | Child of plants and equipment |

---

## 4. Table Definitions

### 4.1 `plants`

Purpose: Stores master information for each solar plant or generation site.

| Column | Type | Description | Key |
| --- | --- | --- | --- |
| `plant_id` | string | Unique identifier of the plant | PK |
| `plant_name` | string | Human-readable plant name |  |
| `region` | string | Geographic region or operating area |  |
| `latitude` | float | Plant latitude |  |
| `longitude` | float | Plant longitude |  |
| `dc_capacity_mw` | float | Installed DC generation capacity in MW |  |
| `ac_capacity_mw` | float | Installed AC generation capacity in MW |  |
| `commissioning_date` | date | Date the plant was commissioned |  |
| `status` | string | Operational state such as operational, outage, or decommissioned |  |
| `timezone_name` | string | Timezone for local operations context |  |
| `created_at` | datetime | Record creation timestamp |  |
| `updated_at` | datetime | Last update timestamp |  |

Relationships:

- one plant has many assets
- one plant has many telemetry records
- one plant has many alarms and incidents
- one plant has many forecast and evaluation outputs

---

### 4.2 `equipment`

Purpose: Stores inventory and hierarchy information for plant equipment such as inverters, transformers, weather stations, feeder systems, and revenue meters.

| Column | Type | Description | Key |
| --- | --- | --- | --- |
| `equipment_id` | string | Unique identifier for the asset | PK |
| `plant_id` | string | Plant to which the asset belongs | FK -> `plants.plant_id` |
| `equipment_name` | string | Friendly asset name |  |
| `equipment_type` | string | Asset category such as inverter, transformer, feeder, relay, or meter |  |
| `manufacturer` | string | Equipment manufacturer |  |
| `model_number` | string | Equipment model reference |  |
| `serial_number` | string | Unique serial number |  |
| `commissioning_date` | date | Date the asset entered service |  |
| `rated_power_kw` | float | Rated power of the equipment |  |
| `parent_equipment_id` | string | Parent asset in a hierarchical setup | FK -> `equipment.equipment_id` |
| `status` | string | Operational status such as operational or maintenance |  |
| `created_at` | datetime | Record creation timestamp |  |
| `updated_at` | datetime | Last update timestamp |  |

Relationships:

- many equipment records belong to one plant
- equipment may have parent/child hierarchy
- equipment has many telemetry observations, alarms, maintenance actions, and health scores

---

### 4.3 `weather_observations`

Purpose: Stores environmental and meteorological conditions associated with a plant or weather station.

| Column | Type | Description | Key |
| --- | --- | --- | --- |
| `plant_id` | string | Plant associated with the observation | FK -> `plants.plant_id` |
| `weather_station_id` | string | Station identifier for the weather source | PK |
| `timestamp` | datetime | Observation timestamp | PK |
| `ghi_wm2` | float | Global horizontal irradiance, W/m² |  |
| `dni_wm2` | float | Direct normal irradiance, W/m² |  |
| `dhi_wm2` | float | Diffuse horizontal irradiance, W/m² |  |
| `ambient_temperature_c` | float | Ambient air temperature in °C |  |
| `module_temperature_c` | float | Module temperature in °C |  |
| `wind_speed_ms` | float | Wind speed in m/s |  |
| `relative_humidity_pct` | float | Relative humidity in percent |  |
| `quality` | string | Data quality indicator such as valid or estimated |  |
| `inserted_at` | datetime | Record insertion timestamp |  |
| `updated_at` | datetime | Last update timestamp |  |

Relationships:

- many weather observations belong to one plant
- used in forecast and performance correlation logic

---

### 4.4 `scada_observations`

Purpose: Stores high-frequency operational telemetry for plant equipment, usually aligned to regular intervals such as 15-minute steps.

| Column | Type | Description | Key |
| --- | --- | --- | --- |
| `plant_id` | string | Plant associated with the observation | FK -> `plants.plant_id` |
| `equipment_id` | string | Equipment associated with the observation | PK + FK -> `equipment.equipment_id` |
| `timestamp` | datetime | Observation timestamp | PK |
| `active_power_kw` | float | Active power output in kW |  |
| `interval_energy_kwh` | float | Energy produced over the interval |  |
| `dc_voltage_v` | float | DC voltage in volts |  |
| `dc_current_a` | float | DC current in amps |  |
| `ac_voltage_v` | float | AC voltage in volts |  |
| `ac_current_a` | float | AC current in amps |  |
| `frequency_hz` | float | Electrical frequency |  |
| `power_factor` | float | Power factor indicator |  |
| `equipment_available` | boolean | Whether equipment is available |  |
| `grid_available` | boolean | Whether grid connection is available |  |
| `operating_state` | string | Operational state such as normal, derated, stopped, fault |  |
| `quality` | string | Data quality flag |  |
| `inserted_at` | datetime | Record insertion timestamp |  |
| `updated_at` | datetime | Last update timestamp |  |

Relationships:

- many SCADA observations belong to one piece of equipment
- supports plant performance analysis and anomaly detection

---

### 4.5 `alarms`

Purpose:Tracks alarms raised for equipment or plant conditions requiring investigation or action.

| Column | Type | Description | Key |
| --- | --- | --- | --- |
| `alarm_id` | string | Unique alarm record identifier | PK |
| `plant_id` | string | Plant associated with the alarm | FK -> `plants.plant_id` |
| `equipment_id` | string | Equipment associated with the alarm | FK -> `equipment.equipment_id` |
| `alarm_code` | string | Standardized alarm code |  |
| `alarm_name` | string | Alarm label |  |
| `category` | string | Alarm category such as equipment or communication |  |
| `severity` | string | Informational, warning, major, critical |  |
| `raised_at` | datetime | Time the alarm was raised |  |
| `status` | string | Active, acknowledged, or cleared |  |
| `acknowledged_at` | datetime | Time of acknowledgement |  |
| `cleared_at` | datetime | Time the alarm was cleared |  |
| `message` | string | Event description or diagnostic message |  |
| `is_synthetic_ground_truth` | boolean | Indicates whether it is a synthetic validation event |  |
| `created_at` | datetime | Record creation timestamp |  |
| `updated_at` | datetime | Last update timestamp |  |

Relationships:

- many alarms belong to one plant
- many alarms belong to one asset
- alarms can be linked to incidents and maintenance follow-up

---

### 4.6 `incidents`

Purpose: Captures significant operational events or disruptions that need formal investigation.

| Column | Type | Description | Key |
| --- | --- | --- | --- |
| `incident_id` | string | Unique incident identifier | PK |
| `plant_id` | string | Associated plant | FK -> `plants.plant_id` |
| `equipment_id` | string | Associated equipment | FK -> `equipment.equipment_id` |
| `incident_name` | string | Human-friendly event name |  |
| `category` | string | Type of event such as equipment failure or grid outage |  |
| `severity` | string | Severity level |  |
| `occurred_at` | datetime | Timestamp when the incident started |  |
| `status` | string | open, investigating, or resolved |  |
| `detected_at` | datetime | Time of detection |  |
| `resolved_at` | datetime | Time of resolution |  |
| `description` | string | Narrative description |  |
| `root_cause` | string | Root-cause note if known |  |
| `linked_alarm_id` | string | Related alarm if an alarm event triggered the incident | FK -> `alarms.alarm_id` |
| `is_synthetic_ground_truth` | boolean | Indicates whether this is a synthetic event for evaluation |  |
| `created_at` | datetime | Record creation timestamp |  |
| `updated_at` | datetime | Last update timestamp |  |

Relationships:

- many incidents belong to one plant
- incidents often connect to specific assets and alarms
- used for operational review and maintenance prioritization

---

### 4.7 `work_orders`

Purpose: Represents maintenance work required or completed for a plant or asset.

| Column | Type | Description | Key |
| --- | --- | --- | --- |
| `work_order_id` | string | Unique work order identifier | PK |
| `plant_id` | string | Associated plant | FK -> `plants.plant_id` |
| `equipment_id` | string | Associated equipment | FK -> `equipment.equipment_id` |
| `work_order_name` | string | Work order label |  |
| `work_order_type` | string | corrective, preventive, predictive, inspection, emergency |  |
| `priority` | string | low, medium, high, critical |  |
| `created_at` | datetime | Record creation time |  |
| `status` | string | open, assigned, in_progress, completed, cancelled |  |
| `linked_incident_id` | string | Related incident if the work order addresses an incident | FK -> `incidents.incident_id` |
| `assigned_team` | string | Team or function responsible |  |
| `scheduled_at` | datetime | Planned schedule date/time |  |
| `started_at` | datetime | Actual start time |  |
| `completed_at` | datetime | Completion timestamp |  |
| `cancelled_at` | datetime | Cancellation timestamp |  |
| `estimated_labor_hours` | float | Planned labor hours |  |
| `actual_labor_hours` | float | Actual labor used |  |
| `estimated_cost` | float | Estimated cost |  |
| `actual_cost` | float | Actual cost incurred |  |
| `notes` | string | Work details or operational notes |  |

Relationships:

- many work orders belong to one equipment asset
- maintenance tasks can be linked to a specific incident

---

### 4.8 `budgets`

Purpose: Captures financial allocation and spend tracking for a plant or operating area.

| Column | Type | Description | Key |
| --- | --- | --- | --- |
| `budget_id` | string | Unique budget identifier | PK |
| `plant_id` | string | Plant associated with the budget | FK -> `plants.plant_id` |
| `budget_name` | string | Budget label |  |
| `category` | string | operations, maintenance, capex, opex, or other |  |
| `fiscal_year` | integer | Budget year |  |
| `allocated_amount` | float | Approved annual or period budget |  |
| `spent_amount` | float | Amount already spent |  |
| `currency_code` | string | Currency code |  |
| `approved_on` | date | Approval date |  |
| `status` | string | draft, approved, or closed |  |
| `inserted_at` | datetime | Record insertion timestamp |  |
| `updated_at` | datetime | Last update timestamp |  |

Relationships:

- budgets are associated with one plant
- useful for operational finance and maintenance planning contexts

---

### 4.9 `tariffs`

Purpose: Stores commercial rate definitions that affect plant revenue, contracts, and energy value calculations.

| Column | Type | Description | Key |
| --- | --- | --- | --- |
| `tariff_id` | string | Unique tariff identifier | PK |
| `plant_id` | string | Plant associated with the tariff | FK -> `plants.plant_id` |
| `tariff_name` | string | Tariff label |  |
| `tariff_type` | string | fixed, time_of_use, feed_in, PPA, merchant |  |
| `currency_code` | string | Currency used for pricing |  |
| `energy_rate_per_kwh` | float | Price per kWh |  |
| `effective_from` | date | Start date of the tariff |  |
| `effective_to` | date | End date if applicable |  |
| `demand_rate_per_kw` | float | Demand charge for capacity-based billing |  |
| `escalation_rate_pct` | float | Annual escalation percentage |  |
| `status` | string | active, draft, expired, cancelled |  |
| `contract_reference` | string | External contract or reference document |  |
| `notes` | string | Additional commercial notes |  |
| `inserted_at` | datetime | Record creation timestamp |  |
| `updated_at` | datetime | Last update timestamp |  |

Relationships:

- tariffs are linked to a plant and support financial / revenue interpretation

---

### 4.10 `ground_truth_events`

Purpose: Stores synthetic evaluation labels and known operational events used to validate model accuracy and anomaly detection.

| Column | Type | Description | Key |
| --- | --- | --- | --- |
| `ground_truth_id` | string | Unique event identifier | PK |
| `plant_id` | string | Plant associated with the event | FK -> `plants.plant_id` |
| `equipment_id` | string | Optional asset associated with the event | FK -> `equipment.equipment_id` |
| `event_type` | string | Event type such as fault, curtailment, maintenance, or degradation |  |
| `severity` | string | low, moderate, high, critical |  |
| `started_at` | datetime | Event start time |  |
| `ended_at` | datetime | Event end time |  |
| `expected_power_loss_pct` | float | Estimated power loss percentage |  |
| `expected_energy_loss_kwh` | float | Estimated energy loss in kWh |  |
| `description` | string | Explanation of the event |  |
| `inserted_at` | datetime | Record insertion timestamp |  |
| `updated_at` | datetime | Last update timestamp |  |

Relationships:

- linked to plant and optionally an individual asset
- used for model validation and analytical benchmarking

---

## 5. Important Cross-Table Relationships

The core relationships in EOIP can be summarized as follows:

- `plants` is the master table for site context.
- `equipment` belongs to a plant and can be parented by another piece of equipment.
- `weather_observations` and `scada_observations` are time-series tables keyed by plant and/or equipment.
- `alarms` and `incidents` are operational event tables with direct links to assets and plants.
- `work_orders` track maintenance actions related to equipment and incidents.
- `budgets` and `tariffs` provide financial and commercial context at the plant level.
- `ground_truth_events` support evaluation and model validation context.

---

## 6. Data Quality Notes

A few considerations are important when interpreting this data model:

- time-series tables are often used for trend analysis and aggregation
- incident and alarm records should be reviewed together when investigating operational issues
- recommendations and dashboards often derive from a combination of plant, equipment, and event data
- ground-truth tables support model evaluation and should be kept separate from operational business data

---

## 7. Closing Statement

The EOIP data model is designed to support both operational monitoring and analytical intelligence. It combines a clear asset hierarchy, rich time-series telemetry, event context, and financial/maintenance metadata in a structure that is understandable to technical teams and suitable for dashboard-driven decision support.
