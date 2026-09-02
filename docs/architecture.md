# EOIP System Architecture Description

## 1. Purpose

The Energy Operations Intelligence Platform (EOIP) is designed to support renewable-energy operations teams by combining plant-level telemetry, weather and operational context, anomaly detection, forecasting, asset health monitoring, and decision support in one integrated system. The architecture is structured to show how raw operational data flows through ingestion, validation, storage, analytics, and visualization layers before it reaches operators and decision-makers.

This document describes the system as a conceptual architecture for implementation and portfolio presentation. It is written to support a visual diagram that can be created in a diagramming tool such as Mermaid, draw.io, PowerPoint, or Visio.

---

## 2. High-Level Architecture

EOIP can be described as a layered system with five major domains:

1. Data sources and ingestion
2. Data processing and ETL
3. Storage and persistence
4. Analytics and intelligence layer
5. Presentation and operational decision support

At a high level, operational data is generated from renewable energy assets and environmental systems, then passed through validation and transformation steps before being stored in a structured time-series database. Analytics modules read from this data to compute forecasts, detect anomalies, assess equipment health, and prioritize maintenance actions. Results are then surfaced through a user-facing dashboard and API layer.

---

## 3. Data Sources

The platform is built around representative renewable-energy source data. These sources can include:

- plant generation data
- inverter and equipment telemetry
- weather and irradiance data
- alarms and incidents
- maintenance history
- transformer and feeder data
- tariff and financial context
- operational events and site metadata

These data sources are represented by synthetic but realistic operational patterns to support portfolio intelligence workflows. They provide the base context for plant performance, risk analysis, and forecasting.

---

## 4. Ingestion and ETL Layer

The ingestion and ETL layer is responsible for the movement and quality control of data as it enters the system. In the architecture, this layer sits between source systems and the persistent database.

The ETL functions include:

- extracting raw operational records from source files or generated datasets
- validating schema, types, and completeness
- standardizing time stamps and units
- normalizing plant, asset, and equipment identifiers
- detecting missing or invalid values
- quarantining records that fail validation
- transforming data into a consistent format for analysis
- loading records into database tables and time-series structures

This layer is important because it ensures the downstream analytics and dashboarding layers operate on clean and interpretable data.

---

## 5. Persistence Layer

The persistence layer is built around PostgreSQL and TimescaleDB, which provide structured storage for operational time-series data and supporting relational tables.

Core database responsibilities include:

- storing plant metadata and asset hierarchy
- storing telemetry and operational time-series information
- preserving alarm and incident records
- storing forecast outputs and model results
- storing maintenance risk and equipment-health scores
- supporting relational joins between plants, assets, and events
- enabling time-based analytical queries for operational monitoring

The database layer also supports data quality checks, historical trend analysis, and aggregation for dashboards and reports.

---

## 6. Analytics and Intelligence Layer

The analytics layer sits above the data persistence layer and transforms operational data into decisions and insight. This is where the platform creates value beyond simple reporting.

### Forecasting

The forecasting module generates expected generation or load forecasts for plants and portfolios. It compares predicted behavior with actual observed performance and is used for planning, operational awareness, and exception analysis.

### Anomaly Detection

The anomaly detection layer identifies unusual patterns in plant performance, alarms, or equipment behavior. It highlights deviations that may warrant investigation or operational response.

### Predictive Maintenance

The predictive maintenance system analyzes asset health and operational history to estimate failure risk or maintenance attention priority. It helps prioritize engineering actions based on equipment degradation and operational context.

### Equipment Health

Equipment health scoring assesses the current condition of critical assets by combining operational metrics, maintenance context, and performance trends. This supports asset-level monitoring and engineering review.

### Recommendation Logic

The recommendation layer synthesizes operational findings into prioritized actions. It connects evidence from data quality, model outputs, and asset conditions into a clear action recommendation for the user.

---

## 7. Application Service Layer

EOIP includes a service layer based on FastAPI. This layer exposes structured access to operational data and health information.

Key service responsibilities:

- exposing health and readiness endpoints
- serving API requests for dashboard data
- supporting operational queries for plant and asset information
- providing structured access to analytics outputs
- enabling standard client interaction from the Streamlit interface

The API layer is positioned between the database and the presentation layer so that the user experience remains clean and decoupled from raw database access.

---

## 8. Presentation Layer

The presentation layer is implemented as a Streamlit application. It is the primary user interface for the platform and organizes information into operational dashboards and decision-support pages.

Example dashboard groups include:

- executive overview
- operations and plant performance
- alarms and incidents
- forecast dashboards
- anomaly dashboards
- maintenance and health views
- recommendations
- administration and data quality views

The presentation layer is designed for non-technical users and operational teams who need a straightforward view of performance and recommended actions.

---

## 9. Security and Governance Considerations

Although the project is primarily a platform demonstration, its architecture includes governance and operational controls that matter in enterprise deployment:

- controlled access to sensitive operational views
- clear ownership of asset and plant metadata
- traceability of recommendation source data
- standardization of IDs and relationships
- explicit separation between model output and operational fact
- environment-based configuration for database and API access

These governance patterns are especially important when the platform is used for executive reporting or engineering decision support.

---

## 10. Deployment Architecture

The platform is designed for container-based deployment using Docker and Docker Compose. The deployment architecture includes:

- a PostgreSQL or TimescaleDB database service
- a migration service for schema changes
- a FastAPI API service
- a Streamlit frontend service
- monitoring services for Prometheus and Grafana
- alerting through Alertmanager
- optional centralized logging to a Loki-based workflow

This deployment model makes the platform easy to run in local development, staging, and demonstrative production-like environments.

---

## 11. Conceptual System Flow

The architecture can be described conceptually as the following pipeline:

1. Renewable asset data and operational sources are created or ingested.
2. ETL validation and transformation prepare the data for analysis.
3. Clean data is stored in PostgreSQL / TimescaleDB.
4. Forecast, anomaly, maintenance, and health logic read from the data store.
5. Insights are exposed through an API layer.
6. The Streamlit interface presents results to operational users.
7. Executive, engineering, and maintenance teams use the interface to monitor status and act on recommendations.

---

## 12. Diagram-Friendly Summary

For a visual diagram, the architecture can be shown using these major blocks:

- Source Systems
- ETL and Validation
- PostgreSQL / TimescaleDB
- Analytics Engine
  - Forecasting
  - Anomaly Detection
  - Predictive Maintenance
  - Equipment Health
  - Recommendation Generation
- FastAPI Services
- Streamlit Dashboards
- Monitoring and Observability
- Deployment / Docker Compose

This block structure provides a clean basis for a diagram that can be shared in presentations, architecture reviews, and project documentation.

---

## 13. Closing Statement

EOIP’s architecture is intentionally designed to be understandable to technical and non-technical stakeholders. It clearly separates source data, operational processing, analytics outcomes, and user-facing decision support while remaining practical to implement and demonstrate in a real project environment.
