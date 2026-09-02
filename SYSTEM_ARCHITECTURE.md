# Energy Operations Intelligence Platform

> **Historical design document.** This file records broad original design
> intent and may describe configured or planned capabilities. The canonical
> current-state architecture and evidence boundaries are in
> [`docs/architecture/SYSTEM_ARCHITECTURE.md`](docs/architecture/SYSTEM_ARCHITECTURE.md).
> Do not interpret future-tense or financial fields below as verified production
> behavior.

## System Architecture

**Project:** Energy Operations Intelligence Platform (EOIP)  
**Document:** System Architecture  
**Version:** 1.0  
**Status:** Draft  
**Prepared By:** Energy Analytics Consultant  

---

# 1. Purpose

This document defines the official software architecture for the Energy Operations Intelligence Platform.

It establishes:

- System boundaries
- Architectural layers
- Package responsibilities
- Data flow
- Module ownership
- Dependency direction
- Naming conventions
- Integration patterns
- Deployment architecture
- Implementation order

This document is the architectural source of truth for all future EOIP development.

All future files, modules, classes, functions, services, database objects, dashboards, and APIs must follow this architecture unless a documented architectural change is approved.

---

# 2. Architecture Objectives

The EOIP architecture must support the following objectives:

1. Reproducible local development
2. Modular implementation
3. Clear separation of responsibilities
4. Centralized configuration
5. Centralized logging
6. Consistent error handling
7. Testable business logic
8. Traceable KPI calculations
9. Explainable machine learning
10. Scalable time-series analytics
11. Interactive decision-support dashboards
12. API-based access to analytics
13. Docker-based deployment
14. Professional GitHub presentation

---

# 3. System Context

EOIP is a production-inspired analytics and decision-support platform for utility-scale solar operations.

The platform simulates and analyzes operational data from a geographically distributed portfolio containing:

- 20 utility-scale solar plants
- Approximately 500 inverters
- Transformers
- Weather stations
- Revenue meters
- Protection relays
- Feeders
- Alarm systems
- Maintenance systems
- Financial and tariff data

The platform does not connect to live operational infrastructure during the portfolio implementation.

Instead, it uses a physics-informed synthetic dataset that reproduces realistic relationships between:

- Weather
- Irradiance
- Temperature
- Plant generation
- Equipment condition
- Grid availability
- Alarms
- Incidents
- Maintenance activities
- Financial impact

---

# 4. High-Level Architecture

```text
┌─────────────────────────────────────────────────────────────┐
│                       Data Sources                          │
│                                                             │
│  Plants | Equipment | Weather | SCADA | Alarms | Incidents │
│  Work Orders | Tariffs | Budgets | Ground-Truth Events     │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                 Synthetic Data Generation                   │
│                                                             │
│ Physics Rules | Statistical Distributions | Event Injection │
│ Referential Integrity | Ground-Truth Labels                 │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                        ETL Pipeline                         │
│                                                             │
│ Extract | Transform | Validate | Quarantine | Load | Audit  │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│               PostgreSQL + TimescaleDB Layer                │
│                                                             │
│ Relational Tables | Hypertables | Indexes | Views           │
│ Continuous Aggregates | Analytical Queries                 │
└───────────────┬───────────────────────────────┬─────────────┘
                │                               │
                ▼                               ▼
┌─────────────────────────────┐   ┌───────────────────────────┐
│      Analytics Layer        │   │ Machine Learning Layer    │
│                             │   │                           │
│ KPIs                        │   │ Forecasting               │
│ Reliability                 │   │ Anomaly Detection         │
│ Operations                  │   │ Predictive Maintenance    │
│ Financial Analysis          │   │ Equipment Health Scoring  │
│ Alarm Analytics             │   │ Model Explainability      │
└───────────────┬─────────────┘   └─────────────┬─────────────┘
                │                               │
                └───────────────┬───────────────┘
                                ▼
┌─────────────────────────────────────────────────────────────┐
│                    Recommendation Layer                     │
│                                                             │
│ Evidence | Risk | Energy Loss | Financial Impact | Priority │
└──────────────────────────────┬──────────────────────────────┘
                               │
                  ┌────────────┴────────────┐
                  ▼                         ▼
┌──────────────────────────┐   ┌──────────────────────────────┐
│   Streamlit Application  │   │        FastAPI Services      │
│                          │   │                              │
│ Executive Dashboard      │   │ Health API                   │
│ Operations Dashboard     │   │ KPI API                      │
│ Equipment Dashboard      │   │ Forecast API                 │
│ Forecast Dashboard       │   │ Recommendation API           │
│ Strategic Dashboard      │   │                              │
│ Platform Dashboard       │   │                              │
└──────────────────────────┘   └──────────────────────────────┘
```

---

# 5. Architectural Style

EOIP uses a layered modular architecture.

The principal layers are:

1. Core Infrastructure
2. Configuration
3. Domain and Common Types
4. Synthetic Data Generation
5. Validation
6. Database
7. ETL
8. Analytics
9. Forecasting
10. Machine Learning
11. Recommendations
12. Visualization
13. Dashboard
14. API
15. Testing and Test Support

Each layer has a defined responsibility and must not duplicate functionality owned by another layer.

---

# 6. Official Repository Structure

```text
Energy-Operations-Intelligence-Platform/
│
├── .github/
│   └── workflows/
│
├── config/
│
├── data/
│   ├── raw/
│   ├── interim/
│   ├── processed/
│   ├── external/
│   ├── synthetic/
│   └── quarantine/
│
├── docker/
│
├── docs/
│
├── logs/
│
├── notebooks/
│
├── scripts/
│
├── sql/
│   ├── ddl/
│   ├── dml/
│   ├── views/
│   └── analytics/
│
├── src/
│   └── eoip/
│       ├── __init__.py
│       │
│       ├── api/
│       │
│       ├── analytics/
│       │
│       ├── common/
│       │
│       ├── config/
│       │   └── settings.py
│       │
│       ├── core/
│       │   ├── constants.py
│       │   ├── directories.py
│       │   ├── exceptions.py
│       │   └── logging.py
│       │
│       ├── dashboard/
│       │
│       ├── database/
│       │
│       ├── etl/
│       │
│       ├── forecasting/
│       │
│       ├── machine_learning/
│       │
│       ├── recommendations/
│       │
│       ├── synthetic/
│       │
│       ├── testsupport/
│       │
│       ├── utilities/
│       │
│       ├── validation/
│       │
│       └── visualization/
│
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── performance/
│   └── acceptance/
│
├── .editorconfig
├── .gitignore
├── PROJECT_STRUCTURE.md
├── README.md
├── requirements-dev.txt
├── requirements.txt
├── pyproject.toml
└── SYSTEM_ARCHITECTURE.md
```

---

# 7. Package Responsibilities

## 7.1 `eoip.core`

The `core` package owns shared application infrastructure.

It contains:

- Project constants
- Directory definitions
- Custom exceptions
- Logging configuration
- Application bootstrap logic

The `core` package must not contain:

- Database queries
- KPI formulas
- Machine learning logic
- Dashboard rendering
- Synthetic data generation

Existing permanent modules:

```text
eoip.core.constants
eoip.core.directories
eoip.core.exceptions
eoip.core.logging
```

---

## 7.2 `eoip.config`

The `config` package owns application configuration.

It is responsible for:

- Environment-variable loading
- Configuration validation
- Database connection settings
- Logging settings
- File path settings
- Runtime environment settings

Existing permanent module:

```text
eoip.config.settings
```

Configuration values must not be hardcoded in operational modules.

---

## 7.3 `eoip.common`

The `common` package will contain domain-neutral shared types.

It may contain:

- Enumerations
- Shared type aliases
- Reusable data-transfer objects
- Result models
- Pagination models
- Date-range models

It must not become a collection of unrelated helper functions.

Generic helper functions belong in `eoip.utilities`.

---

## 7.4 `eoip.synthetic`

The `synthetic` package owns physics-informed data generation.

It will generate:

- Plant master data
- Equipment master data
- Weather observations
- SCADA telemetry
- Alarm records
- Incident records
- Work orders
- Tariffs
- Budgets
- Ground-truth events

It is responsible for:

- Deterministic random seeding
- Engineering relationships
- Statistical distributions
- Operational scenario injection
- Referential integrity
- Reproducible generation
- Dataset metadata

Synthetic generation must not write directly to PostgreSQL.

It produces validated source datasets that are later consumed by ETL.

---

## 7.5 `eoip.validation`

The `validation` package owns data-quality rules.

It is responsible for validating:

- Schemas
- Required fields
- Data types
- Timestamp completeness
- Identifier uniqueness
- Referential integrity
- Numeric ranges
- Engineering constraints
- Missing values
- Duplicate records
- Ground-truth consistency

Validation results must classify issues as:

- Critical
- Error
- Warning
- Informational

Critical validation failures must block downstream publication.

Invalid records must be written to the quarantine area when appropriate.

---

## 7.6 `eoip.database`

The `database` package owns programmatic database access.

It is responsible for:

- SQLAlchemy engine creation
- Session management
- Connection health checks
- Transaction handling
- Repository classes
- Query execution
- Database exception translation

Database schema definitions and analytical SQL remain in the `sql/` directory.

The database package must not own KPI definitions or machine learning logic.

---

## 7.7 `eoip.etl`

The `etl` package owns data movement and transformation.

It is responsible for:

- Extraction from generated files
- Standardization
- Cleaning
- Data-type conversion
- Missing-value treatment
- Duplicate handling
- Validation orchestration
- Loading into PostgreSQL
- Incremental processing
- Audit logging
- Quarantine handling
- Pipeline execution summaries

The ETL layer must call validation components rather than duplicating validation rules.

---

## 7.8 `eoip.analytics`

The `analytics` package owns deterministic business and engineering analytics.

It is responsible for:

- Solar performance KPIs
- Reliability KPIs
- Operations KPIs
- Alarm analytics
- Incident analytics
- Maintenance analytics
- Financial calculations
- Portfolio aggregations
- Plant comparisons
- Equipment comparisons

All KPI formulas must be traceable to the KPI Dictionary.

Machine learning predictions do not belong in this package.

---

## 7.9 `eoip.forecasting`

The `forecasting` package owns energy-generation forecasting.

It is responsible for:

- Forecast datasets
- Feature preparation
- Seasonal naïve baseline
- Prophet model training
- Rolling validation
- Forecast evaluation
- Forecast serialization
- Forecast uncertainty
- Forecast reporting

Forecast evaluation must include:

- MAE
- WAPE
- Baseline comparison
- Improvement percentage

---

## 7.10 `eoip.machine_learning`

The `machine_learning` package owns predictive and unsupervised models.

It includes:

- Anomaly detection
- Failure-risk prediction
- Equipment health scoring
- Feature engineering
- Model evaluation
- Explainability
- Model persistence
- Model metadata

The package must support:

- Isolation Forest
- Logistic Regression
- Random Forest
- Gradient-boosting models where approved
- SHAP-based explanations where compatible

Models must not directly render dashboard components.

---

## 7.11 `eoip.recommendations`

The `recommendations` package owns operational decision support.

It is responsible for converting evidence into prioritized actions.

Each recommendation must include:

- Recommendation identifier
- Asset or plant
- Evidence
- Operational issue
- Risk level
- Expected energy impact
- Estimated financial impact
- Priority
- Recommended action
- Confidence
- Traceability reference

Recommendations must be based on analytics, rules, or model outputs.

Recommendation logic must remain explainable.

---

## 7.12 `eoip.visualization`

The `visualization` package owns reusable chart construction.

It is responsible for:

- Plotly chart functions
- Shared chart formatting
- KPI cards
- Trend charts
- Heatmaps
- Reliability plots
- Forecast plots
- Equipment-health plots
- Financial-impact plots

Visualization functions must receive prepared data.

They must not execute database queries directly.

---

## 7.13 `eoip.dashboard`

The `dashboard` package owns the Streamlit application.

Planned pages:

1. Executive Dashboard
2. Operations Command Centre
3. Equipment Performance
4. Forecasting
5. Maintenance and Reliability
6. Strategic Recommendations
7. Platform and Data Quality

Dashboard responsibilities include:

- Page layout
- Navigation
- Filters
- Session state
- User-facing error messages
- Data downloads
- Integration with visualization functions

Business formulas must not be implemented directly inside dashboard pages.

---

## 7.14 `eoip.api`

The `api` package owns REST services.

Planned API groups:

- Health
- KPIs
- Forecasts
- Recommendations

The API layer is responsible for:

- Request validation
- Response schemas
- HTTP status codes
- Dependency injection
- Error translation
- Service orchestration
- OpenAPI documentation

API endpoints must not contain raw SQL or duplicate analytical logic.

---

## 7.15 `eoip.utilities`

The `utilities` package owns small, reusable technical helpers.

Examples include:

- Date and time utilities
- File-system helpers
- Serialization helpers
- Hashing utilities
- Retry utilities
- Identifier utilities

Utilities must be stateless wherever practical.

Business logic must not be hidden inside generic utility modules.

---

## 7.16 `eoip.testsupport`

The `testsupport` package owns reusable testing support.

It may contain:

- Test-data builders
- Deterministic fixtures
- Temporary database support
- Synthetic sample factories
- Assertion helpers

It must not contain production business logic.

---

# 8. Dependency Direction

Dependencies must flow inward toward stable foundational layers.

Approved dependency direction:

```text
Dashboard ───────┐
API ─────────────┤
Recommendations ─┤
Visualization ───┤
Machine Learning ┤
Forecasting ─────┤
Analytics ───────┤
ETL ─────────────┤
Database ────────┤
Validation ──────┤
Synthetic ───────┤
Common ──────────┤
Config ──────────┤
Core ────────────┘
```

Examples:

- `dashboard` may depend on `analytics`.
- `analytics` may depend on `database`.
- `database` may depend on `config` and `core`.
- `core` must not depend on `dashboard`, `analytics`, or `database`.
- `synthetic` may depend on `common`, `config`, and `core`.
- `validation` may depend on `common`, `config`, and `core`.
- `recommendations` may depend on `analytics`, `forecasting`, and `machine_learning`.

Circular imports are prohibited.

---

# 9. Import Standard

EOIP uses absolute imports from the installed `eoip` package.

Approved:

```python
from eoip.core.constants import PROJECT_NAME
from eoip.config.settings import settings
from eoip.core.logging import get_logger
```

Not approved:

```python
from src.eoip.core.constants import PROJECT_NAME
```

Also avoid fragile multi-level relative imports such as:

```python
from ...core.constants import PROJECT_NAME
```

The project must remain installed in editable mode during development:

```powershell
python -m pip install -e .
```

---

# 10. Data Architecture

## 10.1 Data Zones

EOIP uses the following data zones:

### Raw

```text
data/raw/
```

Contains source files exactly as received or generated before ETL processing.

### Interim

```text
data/interim/
```

Contains partially transformed datasets that are not yet approved for analytics.

### Processed

```text
data/processed/
```

Contains cleaned and validated analytical datasets.

### External

```text
data/external/
```

Contains approved external reference data.

### Synthetic

```text
data/synthetic/
```

Contains physics-informed generated datasets and generation metadata.

### Quarantine

```text
data/quarantine/
```

Contains invalid records rejected during validation or ETL.

---

## 10.2 Principal Data Entities

The core analytical entities are:

- Plant
- Equipment
- Inverter
- Transformer
- Weather station
- Meter
- Protection relay
- Feeder
- Weather observation
- SCADA observation
- Alarm
- Incident
- Work order
- Maintenance activity
- Tariff
- Budget
- Ground-truth event
- Forecast
- Anomaly
- Failure-risk prediction
- Health score
- Recommendation

---

## 10.3 Time Standard

All operational timestamps must use UTC.

The standard SCADA interval is:

```text
15 minutes
```

Timezone conversion for user presentation may occur only at the application boundary.

Internal storage and analytical processing must remain in UTC.

---

# 11. Database Architecture

EOIP uses PostgreSQL with TimescaleDB for time-series workloads.

## 11.1 Relational Tables

Relational tables will store:

- Plants
- Equipment
- Tariffs
- Budgets
- Incidents
- Work orders
- Maintenance records
- Model metadata
- Recommendations

## 11.2 Hypertables

TimescaleDB hypertables will store high-volume time-series data such as:

- SCADA telemetry
- Weather observations
- Alarm events where appropriate
- Forecast results
- Equipment-health history

## 11.3 Database Objects

Database implementation may include:

- Primary keys
- Foreign keys
- Unique constraints
- Check constraints
- Indexes
- Hypertables
- Views
- Materialized views
- Continuous aggregates

## 11.4 SQL Ownership

SQL files are organized as follows:

```text
sql/ddl/         Database schema and object creation
sql/dml/         Controlled inserts and reference-data loading
sql/views/       Reusable database views
sql/analytics/   Analytical and KPI queries
```

Every KPI implemented in SQL must be traceable to the KPI Dictionary.

---

# 12. ETL Architecture

The ETL workflow is:

```text
Discover Input
      ↓
Extract
      ↓
Validate Source Schema
      ↓
Transform
      ↓
Apply Business and Engineering Rules
      ↓
Validate Transformed Data
      ↓
Quarantine Invalid Records
      ↓
Load Valid Records
      ↓
Write Audit Results
      ↓
Publish Completion Summary
```

Each ETL run must record:

- Pipeline name
- Run identifier
- Start time
- End time
- Input record count
- Valid record count
- Rejected record count
- Loaded record count
- Processing status
- Error message where applicable

---

# 13. Analytics Architecture

Analytical calculations must be:

- Deterministic
- Documented
- Testable
- Traceable
- Reproducible

Examples include:

- Actual energy generation
- Expected energy
- Performance ratio
- Capacity factor
- Technical availability
- Grid availability
- MTBF
- MTTR
- Alarm response time
- Repeat fault rate
- Recoverable energy opportunity
- Financial exposure
- Maintenance cost impact

A KPI must be implemented once in its approved analytical owner.

Dashboard, API, and recommendation components must consume the approved KPI output rather than reimplementing the formula.

---

# 14. Machine Learning Architecture

## 14.1 Forecasting

Forecasting compares Prophet against a seasonal naïve baseline.

The minimum acceptance requirement is:

- Prophet must improve MAE and WAPE by at least 10% over the seasonal naïve baseline.

## 14.2 Anomaly Detection

Isolation Forest will identify unusual operational behavior.

An anomaly is not automatically classified as a failure.

Anomaly results must retain:

- Input features
- Anomaly score
- Threshold
- Detection timestamp
- Asset identifier
- Supporting context

## 14.3 Predictive Maintenance

Failure-risk models may use:

- Fault frequency
- Equipment age
- Maintenance history
- Operational loading
- Temperature exposure
- Availability history
- Alarm history
- Previous failures

Minimum target metrics include:

- PR-AUC greater than or equal to 0.80
- Critical recall greater than or equal to 95%
- False alerts below 0.20 per asset-day

## 14.4 Equipment Health Score

The health score is a composite decision-support indicator.

It may include:

- Performance
- Reliability
- Fault history
- Maintenance history
- Operational efficiency
- Data quality

The health score must remain explainable and reproducible.

---

# 15. Recommendation Architecture

The recommendation engine follows this decision flow:

```text
Operational Evidence
        ↓
Issue Classification
        ↓
Risk Assessment
        ↓
Energy-Loss Estimate
        ↓
Financial-Impact Estimate
        ↓
Action Selection
        ↓
Priority Ranking
        ↓
Explainable Recommendation
```

Recommendation outputs must achieve complete traceability.

Every recommendation must be linked to:

- Source evidence
- Applied rule or model
- Calculation method
- Priority logic
- Expected impact

---

# 16. Dashboard Architecture

The Streamlit application will use a multipage structure.

## 16.1 Executive Dashboard

Primary questions:

- How is the portfolio performing?
- Where is revenue at risk?
- Which plants require attention?
- What are the highest-value actions?

## 16.2 Operations Command Centre

Primary questions:

- Which alarms are active?
- Which incidents require escalation?
- Where are SLA risks increasing?
- Which plants are unavailable?

## 16.3 Equipment Dashboard

Primary questions:

- Which assets are underperforming?
- Which assets have recurring faults?
- Which assets have low health scores?
- Which equipment requires inspection?

## 16.4 Forecast Dashboard

Primary questions:

- What generation is expected?
- How accurate is the current forecast?
- What is the forecast uncertainty?
- Which plants show forecast deviation?

## 16.5 Strategic Dashboard

Primary questions:

- Which recommendations have the highest value?
- What energy is recoverable?
- What financial exposure exists?
- Which actions should be prioritized?

## 16.6 Platform Dashboard

Primary questions:

- Is the data pipeline healthy?
- Are validation rules passing?
- Are models current?
- Are data-quality issues increasing?

---

# 17. API Architecture

The FastAPI application will expose versioned endpoints.

Planned structure:

```text
/api/v1/health
/api/v1/kpis
/api/v1/forecasts
/api/v1/recommendations
```

API responses must use documented Pydantic schemas.

The API must provide:

- Input validation
- Clear error messages
- Appropriate HTTP status codes
- OpenAPI documentation
- Response-time monitoring
- Correlation or request identifiers where appropriate

The acceptance target for standard analytical responses is:

```text
Less than 500 milliseconds
```

---

# 18. Configuration Architecture

Configuration sources are applied in this order:

```text
Code Defaults
      ↓
Configuration Files
      ↓
Environment Variables
      ↓
Runtime Overrides
```

Sensitive values must never be committed to Git.

Examples include:

- Database passwords
- Secret keys
- Deployment credentials

The local `.env` file must remain ignored by Git.

A future `.env.example` file will document required variables without containing secrets.

---

# 19. Logging Architecture

All production modules must obtain loggers from:

```python
from eoip.core.logging import get_logger
```

Logging must support:

- Console output
- File output
- Timestamp
- Log level
- Module name
- Source file
- Line number
- Message

Errors must include enough information to identify:

- What failed
- Where it failed
- Why it failed
- How the user or developer can correct it

Bare `except` statements are prohibited.

---

# 20. Exception Architecture

All EOIP-specific errors inherit from:

```text
EOIPError
```

Existing exception categories include:

- ConfigurationError
- DatabaseError
- ValidationError
- ETLError
- DataGenerationError
- ModelError
- DashboardError
- APIError

Future exception classes may be added only when they represent a distinct failure category that cannot be expressed clearly using an existing exception.

---

# 21. Testing Architecture

EOIP uses four testing levels.

## 21.1 Unit Tests

Location:

```text
tests/unit/
```

Purpose:

- Test individual functions and classes
- Validate deterministic calculations
- Test error handling
- Test edge cases

## 21.2 Integration Tests

Location:

```text
tests/integration/
```

Purpose:

- Test package interactions
- Test ETL-to-database flows
- Test repository behavior
- Test API-service integration

## 21.3 Performance Tests

Location:

```text
tests/performance/
```

Purpose:

- ETL timing
- SQL query timing
- Dashboard data-load timing
- API response timing
- Model prediction timing

## 21.4 Acceptance Tests

Location:

```text
tests/acceptance/
```

Purpose:

- Validate phase-level Definition of Done
- Verify documented quality gates
- Support final project sign-off

---

# 22. Code Quality Standards

All Python code must follow:

- Python 3.12
- Black formatting
- Ruff linting
- Type hints where appropriate
- Descriptive naming
- Explicit error handling
- Modular functions
- Clear docstrings
- Absolute package imports
- No duplicated business logic

The standard validation commands will include:

```powershell
python -m black --check src tests
python -m ruff check src tests
python -m pytest
```

---

# 23. Security and Data Protection

Although EOIP uses synthetic data, the architecture must follow safe engineering practices.

Requirements include:

- No secrets committed to Git
- Environment-based credentials
- Parameterized SQL
- Validated API inputs
- Controlled database permissions
- Clear separation between configuration and code
- Sanitized logs
- No confidential operational data

---

# 24. Deployment Architecture

The target deployment uses Docker Compose.

Planned services:

```text
eoip-database
eoip-api
eoip-dashboard
```

Future supporting services may be added when justified.

Conceptual deployment:

```text
┌─────────────────────┐
│   Streamlit UI      │
│   Port 8501         │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│     FastAPI         │
│     Port 8000       │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ PostgreSQL and      │
│ TimescaleDB         │
│ Port 5432           │
└─────────────────────┘
```

Docker deployment must support:

- Reproducible builds
- Health checks
- Environment configuration
- Persistent database storage
- Service networking
- Clean startup from GitHub

---

# 25. CI/CD Architecture

GitHub Actions will eventually validate:

1. Dependency installation
2. Black formatting
3. Ruff linting
4. Unit tests
5. Integration tests where supported
6. Package build
7. Docker build

No change should be considered production-ready when mandatory CI checks fail.

---

# 26. Phase-to-Architecture Mapping

| Phase | Primary Architectural Areas |
|---|---|
| Phase 0 | Business, governance, requirements, acceptance |
| Phase 1 | Core, configuration, repository, logging |
| Phase 2 | Synthetic, common, validation |
| Phase 3 | ETL, validation, database |
| Phase 4 | Database, SQL DDL, TimescaleDB |
| Phase 5 | Analytics, SQL analytics |
| Phase 6 | Forecasting |
| Phase 7 | Machine learning |
| Phase 8 | Recommendations |
| Phase 9 | Dashboard, visualization |
| Phase 10 | API |
| Phase 11 | Testing and test support |
| Phase 12 | Docker, deployment, CI/CD |
| Phase 13 | Documentation and portfolio presentation |

---

# 27. Implementation Order

The approved implementation sequence is:

1. Finalize repository and package foundation
2. Validate existing core modules
3. Create environment configuration template
4. Create application bootstrap
5. Add foundational tests
6. Create synthetic-data domain definitions
7. Implement synthetic master data
8. Implement weather generation
9. Implement SCADA generation
10. Implement operational event injection
11. Implement validation framework
12. Implement database schema
13. Implement database access
14. Implement ETL
15. Implement SQL analytics
16. Implement forecasting
17. Implement anomaly detection
18. Implement predictive maintenance
19. Implement equipment health scoring
20. Implement recommendation engine
21. Implement visualizations
22. Implement Streamlit application
23. Implement FastAPI
24. Complete automated testing
25. Containerize services
26. Configure CI/CD
27. Finalize documentation and case study

---

# 28. Architectural Rules

The following rules are mandatory.

## Rule A — Single Ownership

Every responsibility must have one approved owner.

Examples:

- Logging configuration belongs to `eoip.core.logging`.
- Environment settings belong to `eoip.config.settings`.
- KPI calculations belong to `eoip.analytics`.
- Chart construction belongs to `eoip.visualization`.
- Dashboard layout belongs to `eoip.dashboard`.

## Rule B — No Duplicate Logic

A formula, rule, transformation, or helper must not be reimplemented in multiple modules.

## Rule C — Stable Naming

Approved names must remain unchanged unless an explicit migration is documented.

## Rule D — No Direct Cross-Layer Shortcuts

Dashboard pages must not execute raw SQL.

API endpoints must not duplicate service logic.

Visualization functions must not load data directly.

## Rule E — Explicit Errors

Failures must raise meaningful exceptions and include corrective guidance.

## Rule F — Reproducibility

Data generation, model training, ETL, and deployment must be reproducible.

## Rule G — Traceability

KPIs, predictions, and recommendations must link to their evidence and implementation source.

---

# 29. Architecture Change Control

Any future architectural change must document:

- Current design
- Proposed design
- Reason for change
- Affected files
- Import changes
- Data migration impact
- Testing impact
- Backward-compatibility impact

Architectural changes must be made before dependent implementation expands.

Silent renaming or relocation is prohibited.

---

# 30. Phase 1 Architecture Completion Criteria

The architecture portion of Phase 1 is complete when:

- Repository layout is documented.
- Package layout is stable.
- Absolute imports work.
- Core infrastructure modules are in permanent locations.
- Configuration ownership is established.
- Logging ownership is established.
- Exception ownership is established.
- Dependency direction is documented.
- Testing structure is documented.
- Deployment architecture is documented.
- Future implementation order is approved.

---

# 31. Conclusion

The EOIP architecture separates infrastructure, data generation, validation, storage, analytics, machine learning, recommendations, visualization, user interfaces, and APIs into clearly owned modules.

This structure supports the project's main objectives:

- Engineering realism
- Analytical traceability
- Maintainable code
- Explainable decision support
- Reproducible execution
- Professional deployment
- Portfolio-level presentation

All future EOIP implementation must follow this architecture so that the project remains consistent from Phase 1 through final deployment and documentation.
