# Energy Operations Intelligence Platform
# Data Dictionary

**Version:** 1.0

This document defines every field used throughout the Energy Operations Intelligence Platform.

---

# Table Classification

The platform uses two categories of tables:

- Dimension Tables
- Fact Tables

Dimension tables contain descriptive master data.

Fact tables contain operational events and measurements.

---

# Dimension Tables

## dim_plant

Purpose:

Stores master information for every solar power plant.

| Column | Data Type | Description |
|---------|-----------|-------------|
| plant_id | VARCHAR | Unique plant identifier |
| plant_name | VARCHAR | Official plant name |
| country | VARCHAR | Country where the plant operates |
| region | VARCHAR | Operational region |
| latitude | DECIMAL | Latitude coordinate |
| longitude | DECIMAL | Longitude coordinate |
| timezone | VARCHAR | Plant timezone |
| operator | VARCHAR | Operating company |
| plant_type | VARCHAR | Utility, C&I, Rooftop, Hybrid etc. |
| commissioning_date | DATE | Commercial operation date |
| dc_capacity_mwp | DECIMAL | Installed DC capacity (MWp) |
| ac_capacity_mw | DECIMAL | Installed AC export capacity (MW) |
| dc_ac_ratio | DECIMAL | DC capacity divided by AC capacity |
| grid_connection_voltage_kv | DECIMAL | Grid voltage level |
| tracking_type | VARCHAR | Fixed Tilt / Single Axis / Dual Axis |
| module_technology | VARCHAR | Mono PERC, TOPCon, HJT etc. |
| module_count | INTEGER | Total PV modules |
| inverter_count | INTEGER | Total inverters |
| contractual_availability_target_pct | DECIMAL | Contractual availability target |
| pr_target_pct | DECIMAL | Performance ratio target |
| annual_degradation_rate_pct | DECIMAL | Expected annual degradation |

---

## dim_equipment

Purpose:

Stores every physical asset within the plant hierarchy.

| Column | Data Type | Description |
|---------|-----------|-------------|
| equipment_id | VARCHAR | Unique equipment identifier |
| plant_id | VARCHAR | Parent plant |
| parent_equipment_id | VARCHAR | Parent equipment |
| equipment_type | VARCHAR | Inverter, Transformer, Meter etc. |
| subsystem | VARCHAR | Electrical subsystem |
| manufacturer | VARCHAR | Equipment manufacturer |
| model | VARCHAR | Equipment model |
| serial_number | VARCHAR | Manufacturer serial number |
| rated_power_kw | DECIMAL | Rated active power |
| rated_voltage_v | DECIMAL | Rated operating voltage |
| commissioning_date | DATE | Installation date |
| warranty_end_date | DATE | Warranty expiration |
| criticality_class | VARCHAR | High, Medium, Low |
| expected_life_years | INTEGER | Expected equipment life |
| firmware_version | VARCHAR | Firmware version |
| status | VARCHAR | Current operational status |

---

## `dim_sensor`

**Purpose:** Stores sensor metadata, engineering measurement definitions, valid limits, calibration dates, and data-source information.

| Column | Data Type | Description |
|---|---|---|
| `sensor_id` | VARCHAR | Unique sensor identifier |
| `equipment_id` | VARCHAR | Equipment linked to the sensor |
| `sensor_type` | VARCHAR | Physical sensor category, such as voltage, current, temperature, irradiance, or meter |
| `measurement_type` | VARCHAR | Engineering quantity measured by the sensor |
| `unit` | VARCHAR | Canonical engineering unit defined in `configs/units.yaml` |
| `sampling_interval_seconds` | INTEGER | Expected interval between readings |
| `accuracy_class` | DECIMAL | Manufacturer or metering accuracy classification |
| `lower_valid_limit` | DECIMAL | Lowest acceptable engineering value |
| `upper_valid_limit` | DECIMAL | Highest acceptable engineering value |
| `calibration_date` | DATE | Date of most recent calibration |
| `next_calibration_date` | DATE | Scheduled next calibration date |
| `data_source` | VARCHAR | Source system, protocol, or monitoring platform |

### Constraints

- `sensor_id` must be unique.
- `equipment_id` must exist in `dim_equipment`.
- `sampling_interval_seconds` must be greater than zero.
- `lower_valid_limit` must be less than `upper_valid_limit`.
- `unit` must comply with the canonical unit framework.

---

## `dim_fault_code`

**Purpose:** Standardizes fault classification, severity, probable cause, operational response, and SLA requirements.

| Column | Data Type | Description |
|---|---|---|
| `fault_code` | VARCHAR | Unique standardized fault code |
| `fault_category` | VARCHAR | High-level category, such as electrical, communication, thermal, grid, or mechanical |
| `fault_subcategory` | VARCHAR | More detailed fault classification |
| `fault_description` | TEXT | Business and engineering description of the fault |
| `default_severity` | VARCHAR | Standard severity assigned to the fault |
| `affected_equipment_type` | VARCHAR | Equipment class typically affected |
| `probable_cause` | TEXT | Most likely engineering cause |
| `standard_action` | TEXT | Recommended first-response action |
| `sla_response_minutes` | INTEGER | Maximum permitted response time |
| `sla_resolution_minutes` | INTEGER | Maximum permitted resolution time |

### Constraints

- `fault_code` must be unique.
- Severity must use an approved value such as `CRITICAL`, `HIGH`, `MEDIUM`, or `LOW`.
- SLA durations must be non-negative.
- Fault codes should remain stable once used in historical records.

---

## `dim_calendar`

**Purpose:** Provides standardized time intelligence for interval analytics, tariff classification, seasonal analysis, and reporting.

| Column | Data Type | Description |
|---|---|---|
| `timestamp_utc` | TIMESTAMPTZ | Canonical 15-minute interval-end timestamp in UTC |
| `local_timestamp` | TIMESTAMP | Plant-local timestamp used for display and reporting |
| `date` | DATE | Calendar date |
| `year` | SMALLINT | Calendar year |
| `quarter` | SMALLINT | Calendar quarter from 1 to 4 |
| `month` | SMALLINT | Calendar month from 1 to 12 |
| `week` | SMALLINT | ISO calendar week |
| `day_of_week` | SMALLINT | Day number or agreed business convention |
| `hour` | SMALLINT | Hour from 0 to 23 |
| `minute` | SMALLINT | Minute value, normally 0, 15, 30, or 45 |
| `is_daylight` | BOOLEAN | Indicates whether the interval occurs during daylight |
| `is_peak_tariff` | BOOLEAN | Indicates whether the interval falls within a peak tariff window |
| `season` | VARCHAR | Standard season classification |

### Constraints

- `timestamp_utc` must be unique.
- All timestamps follow the interval-end convention.
- `minute` should normally be one of `0`, `15`, `30`, or `45`.
- `local_timestamp` must be derived using the applicable plant timezone.
- Daylight classification should be based on plant geography rather than fixed clock hours where practical.

---

## `dim_operator`

**Purpose:** Stores operator attributes used for SOC workload, response-time, escalation, and alarm-handling analysis.

| Column | Data Type | Description |
|---|---|---|
| `operator_id` | VARCHAR | Unique operator identifier |
| `team` | VARCHAR | Assigned SOC, operations, engineering, or maintenance team |
| `shift` | VARCHAR | Assigned operating shift |
| `experience_level` | VARCHAR | Experience classification |
| `role` | VARCHAR | Operator or engineer role |

### Constraints

- `operator_id` must be unique.
- Role, shift, and experience values should come from approved reference lists.
- Personally identifiable details should not be required for the synthetic portfolio.
- Historical operator records should not be overwritten when role assignments change.

---

## `dim_simulation_scenario`

**Purpose:** Stores every synthetic scenario injected into the portfolio and preserves the ground-truth labels required for model evaluation.

| Column | Data Type | Description |
|---|---|---|
| `scenario_id` | VARCHAR | Unique scenario identifier |
| `scenario_name` | VARCHAR | Human-readable scenario name |
| `scenario_type` | VARCHAR | Scenario category, such as outage, degradation, alarm storm, curtailment, or sensor fault |
| `description` | TEXT | Detailed description of the injected scenario |
| `start_timestamp` | TIMESTAMPTZ | Scenario start timestamp in UTC |
| `end_timestamp` | TIMESTAMPTZ | Scenario end timestamp in UTC |
| `plant_id` | VARCHAR | Affected plant |
| `equipment_id` | VARCHAR | Affected equipment, where applicable |
| `severity` | VARCHAR | Scenario severity |
| `expected_operational_effect` | TEXT | Expected technical or operational effect |
| `expected_financial_effect` | DECIMAL | Estimated financial impact in USD |
| `ground_truth_label` | VARCHAR | Label used for validation and model evaluation |
| `simulation_seed` | INTEGER | Random seed used to reproduce the scenario |
| `generator_version` | VARCHAR | Version of the data generator that created the scenario |

### Constraints

- `scenario_id` must be unique.
- `start_timestamp` must not be later than `end_timestamp`.
- `plant_id` must exist in `dim_plant`.
- `equipment_id`, when populated, must exist in `dim_equipment`.
- `simulation_seed` and `generator_version` are mandatory for reproducibility.
- Ground-truth labels must not be altered by downstream analytical models.

---

# Dimension Table Relationship Summary

| Dimension Table | Primary Key | Main Relationships |
|---|---|---|
| `dim_plant` | `plant_id` | Parent of equipment, weather, SCADA, incidents, budgets, forecasts, and scenarios |
| `dim_equipment` | `equipment_id` | Child of plant and parent of sensors and equipment-level facts |
| `dim_sensor` | `sensor_id` | Child of equipment |
| `dim_fault_code` | `fault_code` | Referenced by alarm events |
| `dim_calendar` | `timestamp_utc` | Time-intelligence reference for interval facts |
| `dim_operator` | `operator_id` | Referenced by alarm actions, acknowledgements, and reviews |
| `dim_simulation_scenario` | `scenario_id` | Ground-truth reference for injected events |

---

# Dimension Data Governance Rules

1. Dimension keys must remain stable across all pipeline runs.
2. Duplicate dimension records must be rejected before curated loading.
3. Plant, equipment, and sensor identifiers must follow documented naming standards.
4. Equipment parent-child relationships must not create circular hierarchies.
5. Canonical units must comply with `configs/units.yaml`.
6. Slowly changing attributes must retain effective-date history where required.
7. Synthetic scenario records must retain seeds, versions, and ground-truth labels.
8. Reference values such as severity, status, role, shift, and equipment type must use controlled vocabularies.

# Fact Tables

Fact tables store operational events, telemetry, maintenance activities, forecasts, and machine learning outputs. Unlike dimension tables, fact tables are expected to grow continuously throughout the operational life of the platform.

---

## `fact_scada_reading`

**Purpose:** Stores 15-minute operational telemetry collected from SCADA and RMS systems.

**Grain:** One record per equipment per 15-minute interval.

| Column | Data Type | Description |
|---|---|---|
| timestamp_utc | TIMESTAMPTZ | Interval-end timestamp |
| plant_id | VARCHAR | Plant identifier |
| equipment_id | VARCHAR | Equipment identifier |
| operating_state | VARCHAR | Standardized equipment state |
| dc_voltage_v | DECIMAL | DC voltage |
| dc_current_a | DECIMAL | DC current |
| dc_power_kw | DECIMAL | DC power |
| ac_voltage_v | DECIMAL | AC voltage |
| ac_current_a | DECIMAL | AC current |
| ac_power_kw | DECIMAL | AC power |
| reactive_power_kvar | DECIMAL | Reactive power |
| frequency_hz | DECIMAL | Grid frequency |
| power_factor | DECIMAL | Power factor |
| energy_interval_kwh | DECIMAL | Energy generated during interval |
| cumulative_energy_kwh | DECIMAL | Lifetime cumulative energy |
| irradiance_poa_wm2 | DECIMAL | Plane-of-array irradiance |
| module_temperature_c | DECIMAL | Module temperature |
| ambient_temperature_c | DECIMAL | Ambient temperature |
| availability_flag | BOOLEAN | Equipment availability |
| curtailment_flag | BOOLEAN | Curtailment active |
| grid_connected_flag | BOOLEAN | Grid connection status |
| communication_quality_pct | DECIMAL | Communication health |
| data_quality_code | VARCHAR | Validation status |

---

## `fact_weather`

**Purpose:** Stores weather observations used for forecasting and performance analysis.

**Grain:** One row per plant every 15 minutes.

| Column | Data Type | Description |
|---|---|---|
| timestamp_utc | TIMESTAMPTZ | Interval timestamp |
| plant_id | VARCHAR | Plant identifier |
| ghi_wm2 | DECIMAL | Global Horizontal Irradiance |
| poa_irradiance_wm2 | DECIMAL | Plane-of-array irradiance |
| dni_wm2 | DECIMAL | Direct Normal Irradiance |
| ambient_temperature_c | DECIMAL | Ambient temperature |
| module_temperature_c | DECIMAL | Module temperature |
| wind_speed_ms | DECIMAL | Wind speed |
| wind_direction_deg | DECIMAL | Wind direction |
| humidity_pct | DECIMAL | Relative humidity |
| cloud_cover_pct | DECIMAL | Cloud cover |
| precipitation_mm | DECIMAL | Rainfall |
| weather_quality_code | VARCHAR | Data quality indicator |

---

## `fact_alarm_event`

**Purpose:** Stores every alarm generated by the monitoring platform.

**Grain:** One row per alarm occurrence.

| Column | Data Type | Description |
|---|---|---|
| alarm_event_id | BIGINT | Alarm identifier |
| timestamp_raised | TIMESTAMPTZ | Alarm creation time |
| timestamp_acknowledged | TIMESTAMPTZ | Acknowledgement time |
| timestamp_cleared | TIMESTAMPTZ | Alarm cleared time |
| plant_id | VARCHAR | Plant |
| equipment_id | VARCHAR | Equipment |
| fault_code | VARCHAR | Fault reference |
| severity | VARCHAR | Alarm severity |
| alarm_source | VARCHAR | SCADA/RMS/System |
| alarm_state | VARCHAR | Active, Acknowledged, Cleared |
| acknowledged_by | VARCHAR | Operator |
| escalation_level | INTEGER | Escalation stage |
| sla_breached_flag | BOOLEAN | SLA exceeded |
| suppressed_flag | BOOLEAN | Alarm suppression |
| parent_incident_id | BIGINT | Linked incident |

---

## `fact_alarm_action`

**Purpose:** Stores operator actions taken in response to alarms.

**Grain:** One row per action.

| Column | Data Type | Description |
|---|---|---|
| action_id | BIGINT | Action identifier |
| alarm_event_id | BIGINT | Alarm reference |
| operator_id | VARCHAR | Operator |
| action_timestamp | TIMESTAMPTZ | Time of action |
| action_type | VARCHAR | Ack, Escalate, Close |
| notes | TEXT | Operator notes |
| escalated_to | VARCHAR | Escalation destination |

---

## `fact_incident`

**Purpose:** Stores operational incidents and outages.

**Grain:** One record per incident.

| Column | Data Type | Description |
|---|---|---|
| incident_id | BIGINT | Incident identifier |
| incident_start | TIMESTAMPTZ | Start time |
| incident_end | TIMESTAMPTZ | End time |
| plant_id | VARCHAR | Plant |
| primary_equipment_id | VARCHAR | Primary failed asset |
| incident_category | VARCHAR | Category |
| root_cause | TEXT | Root cause |
| severity | VARCHAR | Severity |
| outage_type | VARCHAR | Planned/Forced |
| downtime_class | VARCHAR | Downtime classification |
| controllable_flag | BOOLEAN | Controllable outage |
| contractual_exclusion_flag | BOOLEAN | Excluded from availability |
| availability_exclusion_reason | TEXT | Reason |
| affected_capacity_kw | DECIMAL | Capacity affected |
| energy_not_generated_kwh | DECIMAL | Lost generation |
| financial_loss_usd | DECIMAL | Estimated loss |
| customer_impact | TEXT | Operational impact |
| resolution_summary | TEXT | Resolution |
| closed_by | VARCHAR | Incident closer |

---

## `fact_grid_event`

**Purpose:** Stores utility grid events that affect plant operation, export capability, or compliance.

**Grain:** One row per grid event.

| Column | Data Type | Description |
|---|---|---|
| grid_event_id | BIGINT | Unique grid event identifier |
| plant_id | VARCHAR | Plant identifier |
| start_time | TIMESTAMPTZ | Grid event start |
| end_time | TIMESTAMPTZ | Grid event end |
| grid_status | VARCHAR | Grid status (Available, Unavailable, Limited) |
| voltage_dip_pct | DECIMAL | Voltage dip percentage |
| frequency_deviation_hz | DECIMAL | Frequency deviation |
| curtailment_request_kw | DECIMAL | Requested generation reduction |
| export_limit_kw | DECIMAL | Temporary export limit |
| grid_unavailability_minutes | INTEGER | Total unavailable duration |

---

## `fact_work_order`

**Purpose:** Stores corrective and preventive maintenance work orders.

**Grain:** One row per work order.

| Column | Data Type | Description |
|---|---|---|
| work_order_id | BIGINT | Work order identifier |
| incident_id | BIGINT | Related incident |
| plant_id | VARCHAR | Plant |
| equipment_id | VARCHAR | Equipment |
| created_at | TIMESTAMPTZ | Work order creation |
| scheduled_start | TIMESTAMPTZ | Planned start |
| actual_start | TIMESTAMPTZ | Actual start |
| completed_at | TIMESTAMPTZ | Completion time |
| maintenance_type | VARCHAR | Preventive, Corrective, Predictive |
| priority | VARCHAR | Critical, High, Medium, Low |
| work_order_status | VARCHAR | Open, In Progress, Completed |
| technician_team | VARCHAR | Assigned maintenance team |
| labor_hours | DECIMAL | Labor effort |
| parts_cost_usd | DECIMAL | Replacement parts cost |
| labor_cost_usd | DECIMAL | Labor cost |
| total_cost_usd | DECIMAL | Total maintenance cost |
| action_taken | TEXT | Summary of work completed |
| failure_confirmed_flag | BOOLEAN | Whether failure was confirmed |

---

## `fact_component_replacement`

**Purpose:** Records all component replacements performed during maintenance.

**Grain:** One row per replaced component.

| Column | Data Type | Description |
|---|---|---|
| replacement_id | BIGINT | Replacement identifier |
| work_order_id | BIGINT | Parent work order |
| equipment_id | VARCHAR | Equipment |
| component_type | VARCHAR | Replaced component |
| old_component_age_days | INTEGER | Component age |
| replacement_cost_usd | DECIMAL | Replacement cost |
| replacement_reason | TEXT | Reason for replacement |

---

## `fact_tariff`

**Purpose:** Stores electricity pricing and tariff information.

**Grain:** One row per region, tariff type, and effective interval.

| Column | Data Type | Description |
|---|---|---|
| timestamp_utc | TIMESTAMPTZ | Effective timestamp |
| region | VARCHAR | Geographic region |
| tariff_type | VARCHAR | Fixed, TOU, Dynamic |
| import_rate_usd_kwh | DECIMAL | Import tariff |
| export_rate_usd_kwh | DECIMAL | Export tariff |
| demand_charge_usd_kw | DECIMAL | Demand charge |
| penalty_rate | DECIMAL | Penalty rate |
| currency | VARCHAR | Currency |

---

## `fact_load`

**Purpose:** Stores regional demand and feeder load information.

**Grain:** One row per feeder every 15 minutes.

| Column | Data Type | Description |
|---|---|---|
| timestamp_utc | TIMESTAMPTZ | Interval timestamp |
| region | VARCHAR | Region |
| feeder_id | VARCHAR | Feeder |
| active_power_kw | DECIMAL | Active power |
| reactive_power_kvar | DECIMAL | Reactive power |
| apparent_power_kva | DECIMAL | Apparent power |
| voltage_v | DECIMAL | Voltage |
| current_a | DECIMAL | Current |
| frequency_hz | DECIMAL | Frequency |
| power_factor | DECIMAL | Power factor |
| energy_consumed_kwh | DECIMAL | Energy consumed |
| peak_demand_flag | BOOLEAN | Peak demand indicator |

---

## `fact_budget_target`

**Purpose:** Stores monthly business targets for each plant.

**Grain:** One row per plant per reporting period.

| Column | Data Type | Description |
|---|---|---|
| period | DATE | Budget period |
| plant_id | VARCHAR | Plant |
| budget_generation_mwh | DECIMAL | Target generation |
| budget_revenue_usd | DECIMAL | Target revenue |
| target_pr_pct | DECIMAL | Target performance ratio |
| target_availability_pct | DECIMAL | Target availability |
| target_maintenance_cost | DECIMAL | Target maintenance cost |
| target_fault_rate | DECIMAL | Target fault rate |

---

## `fact_forecast`

**Purpose:** Stores forecasting results produced by analytical and machine learning models.

**Grain:** One row per forecast run, plant, target timestamp, and forecast type.

| Column | Data Type | Description |
|---|---|---|
| forecast_run_id | BIGINT | Forecast execution identifier |
| generated_at | TIMESTAMPTZ | Forecast generation timestamp |
| target_timestamp | TIMESTAMPTZ | Forecast target interval |
| plant_id | VARCHAR | Plant identifier |
| forecast_type | VARCHAR | Generation, Irradiance, Load, Revenue |
| model_name | VARCHAR | Forecasting model |
| horizon | INTEGER | Forecast horizon in intervals |
| predicted_value | DECIMAL | Forecasted value |
| lower_bound | DECIMAL | Lower confidence interval |
| upper_bound | DECIMAL | Upper confidence interval |
| actual_value | DECIMAL | Observed value after execution |
| model_version | VARCHAR | Model version |

### Constraints

- Forecasts must reference a valid plant.
- Confidence intervals must satisfy:

```text
lower_bound ≤ predicted_value ≤ upper_bound
```

- Every forecast must retain the model version used.

---

## `fact_model_alert`

**Purpose:** Stores alerts generated by anomaly detection, equipment health, and failure-risk models.

**Grain:** One row per model-generated alert.

| Column | Data Type | Description |
|---|---|---|
| model_alert_id | BIGINT | Alert identifier |
| timestamp_utc | TIMESTAMPTZ | Alert timestamp |
| plant_id | VARCHAR | Plant |
| equipment_id | VARCHAR | Equipment |
| model_name | VARCHAR | ML model |
| model_version | VARCHAR | Version used |
| anomaly_score | DECIMAL | Model anomaly score |
| risk_probability | DECIMAL | Failure probability |
| alert_category | VARCHAR | Alert classification |
| recommended_action | TEXT | Recommended response |
| review_status | VARCHAR | Review status |
| reviewed_by | VARCHAR | Reviewer |
| confirmed_fault_flag | BOOLEAN | Confirmed by engineering |
| operator_feedback | TEXT | Operator comments |
| false_positive_flag | BOOLEAN | False positive indicator |
| false_negative_review | BOOLEAN | False negative review |
| confirmed_root_cause | TEXT | Engineering root cause |
| action_taken | TEXT | Corrective action |
| reviewed_at | TIMESTAMPTZ | Review timestamp |

### Constraints

- One alert must reference one plant.
- Equipment must exist in `dim_equipment`.
- Risk probability must remain between 0 and 1.
- Alert review history must remain auditable.

---

## `fact_recommendation_action`

**Purpose:** Tracks recommendations from creation through implementation and realized operational benefit.

**Grain:** One row per recommendation.

| Column | Data Type | Description |
|---|---|---|
| recommendation_id | BIGINT | Recommendation identifier |
| created_at | TIMESTAMPTZ | Creation timestamp |
| plant_id | VARCHAR | Plant |
| equipment_id | VARCHAR | Equipment |
| recommendation_type | VARCHAR | Recommendation category |
| priority | VARCHAR | Business priority |
| owner | VARCHAR | Responsible owner |
| due_date | DATE | Due date |
| status | VARCHAR | Open, In Progress, Closed |
| estimated_benefit | DECIMAL | Estimated benefit (USD) |
| realized_benefit | DECIMAL | Realized benefit (USD) |
| completion_date | DATE | Completion date |
| evidence_reference | VARCHAR | Supporting evidence |

### Constraints

- Estimated and realized benefits must be non-negative.
- Completed recommendations require a completion date.
- Evidence references should link to dashboards, incidents, or reports.

---

## `fact_etl_run`

**Purpose:** Stores ETL execution history and pipeline quality metrics.

**Grain:** One row per ETL execution.

| Column | Data Type | Description |
|---|---|---|
| etl_run_id | BIGINT | ETL execution identifier |
| pipeline_name | VARCHAR | Pipeline executed |
| started_at | TIMESTAMPTZ | Pipeline start |
| completed_at | TIMESTAMPTZ | Pipeline completion |
| status | VARCHAR | Success, Failed, Warning |
| source_rows | INTEGER | Rows extracted |
| accepted_rows | INTEGER | Rows loaded |
| rejected_rows | INTEGER | Rows rejected |
| duplicate_rows | INTEGER | Duplicate rows |
| freshness_delay_minutes | INTEGER | Data freshness delay |
| error_message | TEXT | Error summary |
| git_commit_sha | VARCHAR | Git commit used for execution |

### Constraints

- Accepted rows cannot exceed source rows.
- Completed time must be greater than or equal to start time.
- Every ETL run should retain the Git commit SHA for reproducibility.

---

# Primary Keys

| Table | Primary Key |
|---|---|
| dim_plant | plant_id |
| dim_equipment | equipment_id |
| dim_sensor | sensor_id |
| dim_fault_code | fault_code |
| dim_calendar | timestamp_utc |
| dim_operator | operator_id |
| dim_simulation_scenario | scenario_id |
| fact_scada_reading | timestamp_utc + equipment_id |
| fact_weather | timestamp_utc + plant_id |
| fact_alarm_event | alarm_event_id |
| fact_alarm_action | action_id |
| fact_incident | incident_id |
| fact_grid_event | grid_event_id |
| fact_work_order | work_order_id |
| fact_component_replacement | replacement_id |
| fact_tariff | timestamp_utc + region + tariff_type |
| fact_load | timestamp_utc + feeder_id |
| fact_budget_target | period + plant_id |
| fact_forecast | forecast_run_id |
| fact_model_alert | model_alert_id |
| fact_recommendation_action | recommendation_id |
| fact_etl_run | etl_run_id |

---

# Data Dictionary Standards

The following conventions apply to all tables:

1. All timestamps are stored in UTC.
2. Canonical engineering units follow `configs/units.yaml`.
3. Financial values are stored in USD.
4. Nullable fields are minimized wherever practical.
5. Primary keys must remain immutable.
6. Foreign keys must enforce referential integrity.
7. Time-series tables should support partitioning or TimescaleDB hypertables.
8. All derived values must be traceable to source data.
9. Data quality status must be retained throughout the ETL pipeline.
10. Model outputs must remain reproducible through version tracking and audit metadata.

---

**End of Document**
