# EOIP Deployment Guide

This document describes the deployment architecture, operational setup, verification steps, and day-2 operations for the Energy Operations Intelligence Platform (EOIP). It is intended for technical reviewers, operators, and client stakeholders reviewing the platform for the first time.

---

## 1. Prerequisites

Before deploying EOIP, ensure the following tools and services are available:

- Docker Engine and Docker Compose v2
- Git
- Python 3.12
- PostgreSQL client tools, including `pg_dump` and `pg_restore`
- `curl` for health checks
- Access to the project repository
- A Linux/macOS shell or a PowerShell-compatible environment for scripts
- Optional: `make` if you want to wrap commands in project automation

### Required local services

- A PostgreSQL-compatible database service such as TimescaleDB
- Access to ports:
  - 5432 for PostgreSQL / TimescaleDB
  - 8000 for the FastAPI service
  - 8501 for the Streamlit service
  - 9090 for Prometheus
  - 3000 for Grafana
  - 9093 for Alertmanager

### Repository prerequisites

The deployment files are included in the project root:

- `Dockerfile.api`
- `Dockerfile.streamlit`
- `docker-compose.yml`
- `.env.example`
- `scripts/backup.sh`
- `scripts/verify_deployment.sh`
- `docker/healthcheck.sh`
- `docker/logging.yml`
- `docker/monitoring.yml`

---

## 2. Quick start

The platform can be deployed using Docker Compose from the project root.

### Step 1: Configure environment variables

Copy the sample environment file and set the required values:

```bash
cp .env.example .env
```

Update the values for the database and API integration, especially:

- `EOIP_DATABASE_HOST`
- `EOIP_DATABASE_PORT`
- `EOIP_DATABASE_NAME`
- `EOIP_DATABASE_USER`
- `EOIP_DATABASE_PASSWORD`
- `EOIP_API_BASE_URL`

### Step 2: Build and start the services

```bash
docker compose up --build -d
```

This builds the API and Streamlit containers and starts the supporting PostgreSQL stack.

### Step 3: Verify the stack

```bash
chmod +x scripts/verify_deployment.sh
./scripts/verify_deployment.sh
```

### Step 4: View the application

- API: http://localhost:8000
- Streamlit UI: http://localhost:8501
- Prometheus: http://localhost:9090
- Grafana: http://localhost:3000
- Alertmanager: http://localhost:9093

### Step 5: Stop services

```bash
docker compose down
```

To remove persistent data volumes as well:

```bash
docker compose down -v
```

---

## 3. Environment variables

The deployment configuration uses the same environment variables documented in `.env.example`.

| Variable | Default | Description |
| --- | --- | --- |
| `EOIP_DATABASE_HOST` | `localhost` | Hostname of the PostgreSQL or TimescaleDB server. |
| `EOIP_DATABASE_PORT` | `5432` | Port used by the database server. |
| `EOIP_DATABASE_NAME` | `eoip` | Name of the EOIP database. |
| `EOIP_DATABASE_USER` | `postgres` | Database username used for application and admin connections. |
| `EOIP_DATABASE_PASSWORD` | `replace_with_your_local_postgresql_password` | Password used to authenticate to the database. |
| `EOIP_LOG_LEVEL` | `INFO` | Global log level for the application. |
| `EOIP_API_BASE_URL` | `http://127.0.0.1:8000/api/v1` | Base URL for the EOIP API consumed by the Streamlit frontend. |
| `EOIP_API_ACCESS_TOKEN` | empty | Optional bearer token for authenticated API calls. |
| `EOIP_API_REQUEST_TIMEOUT_SECONDS` | `10` | Timeout in seconds for outbound API requests. |
| `EOIP_BACKUP_DIR` | `/var/backups/eoip` | Directory used by the backup script to store compressed database dumps. |
| `EOIP_BACKUP_RETENTION_DAYS` | `7` | Number of days to keep backup files before removing them automatically. |
| `EOIP_STREAMLIT_BASE_URL` | `http://127.0.0.1:8501` | Base URL used by deployment validation checks for the Streamlit service. |

> The project should not commit a populated `.env` file. Store deployment credentials in a secure environment or secret manager in production.

---

## 4. Health checks

EOIP includes both service-level and deployment-level health checks.

### Run the shell health-check helper

```bash
chmod +x docker/healthcheck.sh
./docker/healthcheck.sh all
```

This checks:

- database connectivity
- API health endpoint
- Streamlit health endpoint

You can also run targeted checks:

```bash
./docker/healthcheck.sh db
./docker/healthcheck.sh api
./docker/healthcheck.sh streamlit
```

### Run deployment verification

```bash
chmod +x scripts/verify_deployment.sh
./scripts/verify_deployment.sh
```

The verification script prints a clear `PASS` or `FAIL` for each check and exits with:

- `0` if all checks succeed
- `1` if any check fails

Checks include:

- database reachability
- Alembic migration status
- TimescaleDB extension presence
- FastAPI health endpoint status
- Streamlit health endpoint status
- Docker container readiness

---

## 5. Backup and restore

### Create a backup

Use the backup script to export a compressed PostgreSQL dump:

```bash
chmod +x scripts/backup.sh
export EOIP_BACKUP_DIR="/var/backups/eoip"
export EOIP_DATABASE_HOST="timescaledb"
export EOIP_DATABASE_PORT="5432"
export EOIP_DATABASE_NAME="eoip"
export EOIP_DATABASE_USER="eoip_user"
export EOIP_DATABASE_PASSWORD="your_password"

./scripts/backup.sh
```

The script creates a timestamped file named:

```text
eoip_backup_YYYYMMDD_HHMMSS.sql.gz
```

It also deletes files older than 7 days automatically unless the retention window is changed with `EOIP_BACKUP_RETENTION_DAYS`.

### Restore from a backup

To restore a database dump, use `pg_restore` or `gunzip` in combination with `psql` depending on the backup format.

Example:

```bash
export PGPASSWORD="your_password"

gunzip -c /var/backups/eoip/eoip_backup_20260902_120000.sql.gz | psql \
  -h localhost \
  -p 5432 \
  -U eoip_user \
  -d eoip
```

For a custom restore path or a full database rebuild, connect to the target database server and run the restore command against the desired database.

> Always validate the restored state with the deployment verification script after a restore.

---

## 6. CI/CD

EOIP includes GitHub Actions automation for continuous integration and continuous deployment.

### CI workflow

The workflow in `.github/workflows/ci.yml` is responsible for:

- running on pushes and pull requests to the main branches
- setting up Python 3.12
- installing project dependencies
- connecting to a TimescaleDB test service
- running Alembic migrations
- executing formatting and lint checks
- running the test suite

### CD workflow

The workflow in `.github/workflows/cd.yml` is responsible for:

- building container images for the API and Streamlit services
- logging into GitHub Container Registry
- pushing Docker images to GHCR
- tagging images by branch and commit SHA

This makes delivery repeatable and reduces manual deployment steps.

---

## 7. Monitoring

EOIP includes a built-in monitoring stack for observability.

### Prometheus

- URL: http://localhost:9090
- Purpose: scrape service metrics and alert rules

### Grafana

- URL: http://localhost:3000
- Default credentials:
  - username: `admin`
  - password: `admin`
- Purpose: dashboards and operational visualization

### Alertmanager

- URL: http://localhost:9093
- Purpose: alert routing and notification handling

The monitoring configuration is defined under `docker/monitoring.yml`, `docker/monitoring/prometheus.yml`, and `docker/monitoring/alertmanager.yml`.

---

## 8. Troubleshooting

### 1. Docker containers are not starting

**Symptoms:** `docker compose up` shows failed services or containers exit immediately.

**Solution:**

- check logs with `docker compose logs`
- verify Docker daemon is running
- confirm there is enough disk space and memory
- rebuild containers with `docker compose up --build -d`

### 2. Database connection failures

**Symptoms:** verification script reports database unreachable or authentication errors.

**Solution:**

- confirm database credentials in `.env`
- ensure the container name or host is correct
- verify the TimescaleDB container is running
- confirm the port mapping is open and the service is healthy

### 3. Alembic migration is out of sync

**Symptoms:** the verification script displays a mismatch between current and head revision.

**Solution:**

```bash
docker compose run --rm migration alembic upgrade head
```

If needed, inspect the migration history and verify the latest revision is present in `migrations/versions/`.

### 4. FastAPI or Streamlit health checks return non-200 responses

**Symptoms:** HTTP status codes are not 200 and the deployment script reports failures.

**Solution:**

- confirm the container is running
- verify the service port mapping
- check the service logs with `docker compose logs api` or `docker compose logs streamlit`
- confirm the application is listening on the expected host and port

### 5. Backup script fails or no backups are created

**Symptoms:** backup command reports an error or no files appear in the backup directory.

**Solution:**

- ensure `pg_dump` is installed
- validate the environment variables for database host, port, username, and password
- create the target directory manually if needed
- confirm the backup directory has write permissions

---

## Summary

EOIP is designed to deploy in a repeatable Docker-based environment using a PostgreSQL-compatible database, a FastAPI application, a Streamlit user interface, and observability tooling for monitoring and alerting. With the included verification scripts, health checks, backup process, and CI/CD workflows, the platform can be deployable, maintainable, and operationally reviewable for stakeholder evaluation.
