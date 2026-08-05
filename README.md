# Energy Operations Intelligence Platform (EOIP)

## Overview

The **Energy Operations Intelligence Platform (EOIP)** is a consultant-level, end-to-end energy analytics system designed to demonstrate modern data engineering, analytics, machine learning, and decision-support techniques for utility-scale solar operations.

The project simulates a production-inspired environment where operational data from multiple solar power plants is transformed into actionable engineering and business intelligence.

---

## Project Objectives

The platform is designed to:

- Consolidate operational data into a centralized analytical platform.
- Generate a physics-informed synthetic dataset representing utility-scale solar operations.
- Build a robust ETL pipeline with validation and logging.
- Store and analyze time-series data using PostgreSQL.
- Calculate engineering, operational, and financial KPIs.
- Forecast future energy generation.
- Detect operational anomalies.
- Predict equipment failures.
- Generate explainable maintenance recommendations.
- Provide interactive dashboards for executives and operations teams.

---

## Technology Stack

| Category | Technology |
|----------|------------|
| Programming Language | Python 3.12 |
| Database | PostgreSQL |
| Data Analysis | Pandas, NumPy |
| Visualization | Plotly, Streamlit |
| Machine Learning | Scikit-Learn, Prophet |
| ORM | SQLAlchemy |
| API | FastAPI |
| Version Control | Git, GitHub |
| Containerization | Docker |

---

## Project Status

**Current Phase:** Phase 1 – Repository & Engineering Foundation

Project development follows a structured, phase-by-phase implementation approach with documented deliverables, quality gates, and acceptance criteria.

---

## Repository Structure

The repository will be expanded incrementally throughout development. Each phase introduces new modules while maintaining a clean, production-inspired architecture.

---

## Local Environment Setup

Python 3.12 is required. From PowerShell in the repository root:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
Copy-Item .env.example .env
```

Update `EOIP_DATABASE_PASSWORD` in `.env` for your local PostgreSQL instance.
The application reads `.env` from the repository root. The real `.env` is ignored
by Git; `.env.example` is the tracked, secret-free template.

Verify the environment with:

```powershell
python -m pip check
python -c "from eoip.config.settings import settings; print(settings.project_name)"
python -m ruff check .
python -m pytest
```

---

## Documentation

Project documentation includes:

- Business Case
- User Personas
- KPI Dictionary
- Success Criteria
- Risk Register
- Assumptions & Limitations
- Acceptance Criteria

---

## Development Principles

This project follows the following engineering principles:

- One complete implementation per file.
- Modular and maintainable architecture.
- Consistent naming across all phases.
- Reproducible development environment.
- Comprehensive documentation.
- Professional Git history.
- Production-inspired coding standards.

---

## Author

Electrical Engineer with experience in:

- SOC Monitoring
- RMS Alarm Management
- Solar Plant Operations
- SCADA Monitoring
- Energy Performance Analytics

---

## License

This repository is intended for educational and portfolio purposes.
