# Energy Operations Intelligence Platform (EOIP)

## Official Repository Structure

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
│   └── synthetic/
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
│       ├── api/
│       ├── config/
│       ├── core/
│       ├── database/
│       ├── etl/
│       ├── analytics/
│       ├── forecasting/
│       ├── machine_learning/
│       ├── recommendations/
│       ├── dashboard/
│       ├── visualization/
│       ├── validation/
│       ├── utilities/
│       └── testsupport/
│
├── tests/
│
├── .editorconfig
├── .gitignore
├── pyproject.toml
├── requirements.txt
├── requirements-dev.txt
├── README.md
└── PROJECT_STRUCTURE.md
```

## Purpose

This directory structure is the official layout for the EOIP project.

Future development must follow this structure. New modules should be added only within the designated directories to maintain consistency, scalability, and traceability throughout all project phases.