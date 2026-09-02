# EOIP ER Diagram Description

## 1. Purpose

This document describes the logical entity relationship model for the Energy Operations Intelligence Platform. It outlines the primary database tables and the relationships between them so that a visual ER diagram can be created accurately for architecture reviews, technical documentation, or client presentations.

The design is centered on renewable energy operations and supports the capture of plant and equipment metadata, time-series telemetry, alarms, maintenance records, forecast outputs, and analytical recommendations.

---

## 2. Core Design Principles

The ER model follows a few basic principles:

- plants contain multiple assets and devices
- equipment belongs to a plant and may have many telemetry observations
- operational events such as alarms and incidents are linked to assets or plants
- forecasts and model outputs are stored separately from source data
- maintenance and health scores are associated with equipment over time
- recommendations link back to the underlying operational context and evidence

This structure keeps the database understandable while supporting reporting, forecasting, anomaly review, and operational insight generation.

---

## 3. Primary Tables and Relationships

### Plants

The `plants` table stores the highest-level operational grouping in the system.

Key attributes typically include:

- plant ID
- plant name
- region or geography
- commissioning date
- status
- capacity
- installed generation technology
- site metadata

A plant can have many associated assets, weather stations, alarms, telemetry records, and performance observations.

Relationship:

- one plant has many assets
- one plant has many telemetry records
- one plant may have many alarms and incidents
- one plant may have many forecast records

### Equipment and Assets

The `equipment` or `assets` table represents the operational components within a plant, such as inverters, transformers, feeders, weather stations, revenue meters, and protection relays.

Typical fields include:

- asset ID
- plant ID
- asset type
- manufacturer
- model
- serial number
- install date
- status
- location or site segment

Relationship:

- many assets belong to one plant
- one asset can have many telemetry entries
- one asset can have many maintenance records
- one asset can have many alarms or incidents
- one asset can have many health score records

### Weather

The `weather` table stores environmental conditions relevant to plant operations. This includes irradiance, temperature, wind, humidity, and related metrics.

Typical fields include:

- weather record ID
- plant ID or site ID
- timestamp
- irradiance
- ambient temperature
- wind speed
- humidity
- other environmental metrics

Relationship:

- many weather records belong to one plant
- weather records support power generation and forecasting analyses

### Telemetry

The `telemetry` table is one of the most important time-series structures in the system. It records the operational performance metrics for plants and assets over time.

Typical fields include:

- telemetry ID
- asset ID or plant ID
- timestamp
- power output
- current
- voltage
- temperature
- availability
- performance ratio
- other technical measurements

Relationship:

- many telemetry records belong to one asset or plant
- telemetry records join to weather and forecast data through timestamp and plant context

### Alarms

The `alarms` table stores operational events that require investigation or response.

Typical fields include:

- alarm ID
- plant ID
- asset ID
- timestamp
- severity
- alarm code
- description
- status
- acknowledged flag
- cleared timestamp

Relationship:

- many alarms belong to one plant
- many alarms belong to one asset
- alarms may relate to incidents or maintenance work

### Incidents

The `incidents` table captures significant operational interruptions or disruption events.

Typical fields include:

- incident ID
- plant ID
- asset ID
- timestamp
- category
- cause
- impact summary
- duration
- affected system or subsystem
- severity

Relationship:

- many incidents are associated with one plant
- incidents may involve one or more assets
- incidents can be linked to maintenance records and recommendations

### Maintenance

The `maintenance` table stores work orders, actions, and service records for equipment.

Typical fields include:

- maintenance ID
- asset ID
- plant ID
- work order number
- maintenance type
- scheduled date
- completed date
- technician or owner
- description
- status
- cost or labor estimate

Relationship:

- many maintenance actions belong to one asset
- maintenance records can influence or explain health and performance degradation
- maintenance actions may connect to recommendations

### Equipment Health

The `equipment_health` or `asset_health` table stores health scores over time.

Typical fields include:

- health ID
- asset ID
- timestamp
- score
- health category
- degradation indicator
- anomaly evidence count
- confidence score

Relationship:

- many health records belong to one asset
- health records can be reviewed alongside alarms, maintenance, and performance trends

### Forecasts

The `forecasts` table stores predicted generation or operational summaries generated by forecasting models.

Typical fields include:

- forecast ID
- plant ID
- model name
- forecast timestamp
- prediction horizon
- target metric
- predicted value
- lower bound
- upper bound
- evaluation metrics

Relationship:

- many forecast records belong to one plant
- forecast rows are usually compared against actual telemetry

### Model Evaluations

The `model_evaluations` table stores error and performance metrics for forecasting, anomaly, or maintenance models.

Typical fields include:

- evaluation ID
- model name
- metric name
- metric value
- evaluation timestamp
- dataset or sample window
- model version

Relationship:

- one model may have many evaluation records
- evaluations support documentation, comparison, and evidence reporting

### Recommendations

The `recommendations` table stores operational suggestions derived from analytics and evidence.

Typical fields include:

- recommendation ID
- plant ID
- asset ID
- created timestamp
- priority
- recommendation type
- description
- confidence
- status
- rationale or evidence source

Relationship:

- many recommendations belong to one plant
- recommendations may reference one or more assets
- recommendations often connect to alarms, incidents, maintenance, or model outputs

---

## 4. Relationship Summary

The main relationships can be summarized as follows:

- Plant 1 to many Asset
- Plant 1 to many Weather
- Plant 1 to many Telemetry
- Plant 1 to many Alarm
- Plant 1 to many Incident
- Plant 1 to many Forecast
- Plant 1 to many Recommendation
- Asset many to one Plant
- Asset 1 to many Telemetry
- Asset 1 to many Maintenance
- Asset 1 to many Alarm
- Asset 1 to many Incident
- Asset 1 to many Equipment Health
- Asset many to one Recommendation
- Forecast many to one Plant
- Model Evaluation many to one Model or Model Type
- Recommendation many to one Incident or Alarm (conceptual linkage)

---

## 5. Conceptual ER Diagram Structure

A simple conceptual ER diagram would be organized like this:

- `plants` at the top level
- `assets` connected to plants
- `weather`, `telemetry`, `alarms`, and `incidents` as operational child tables
- `maintenance` and `equipment_health` linked to assets
- `forecasts` and `model_evaluations` linked to plant and model context
- `recommendations` linked to plants, assets, and event context

This structure creates a clear operational and analytic database model that supports both daily operations and executive reporting.

---

## 6. Diagram-Friendly Notes for Drawing

When creating the visual ER diagram, these are the most useful grouping cues:

- Plant and Geographic Metadata
- Asset Inventory and Hierarchy
- Time-Series Operational Tables
- Event and Incident Tables
- Maintenance and Health Tables
- Forecast and Analytical Output Tables
- Recommendation and Governance Tables

This grouping makes the schema easier to communicate visually in a presentation or architecture document.

---

## 7. Closing Statement

The EOIP database schema is designed around renewable energy operational realities: plants, assets, telemetry, alarms, maintenance, health scoring, forecasting, and recommendations. This relational structure supports clear reporting, operational monitoring, and predictive intelligence while remaining understandable enough for a senior technical or stakeholder audience.
