#!/usr/bin/env bash
set -uo pipefail

DB_HOST="${EOIP_DATABASE_HOST:-localhost}"
DB_PORT="${EOIP_DATABASE_PORT:-5432}"
DB_NAME="${EOIP_DATABASE_NAME:-eoip}"
DB_USER="${EOIP_DATABASE_USER:-postgres}"
DB_PASSWORD="${EOIP_DATABASE_PASSWORD:-}"
API_BASE_URL="${EOIP_API_BASE_URL:-http://127.0.0.1:8000/api/v1}"
STREAMLIT_URL="${EOIP_STREAMLIT_BASE_URL:-http://127.0.0.1:8501}"

FAILURES=0

log_result() {
  local check_name="$1"
  local status="$2"
  local message="$3"

  if [[ "$status" == "PASS" ]]; then
    printf 'PASS: %s - %s\n' "$check_name" "$message"
  else
    printf 'FAIL: %s - %s\n' "$check_name" "$message"
    FAILURES=$((FAILURES + 1))
  fi
}

check_db_connection() {
  if [[ -z "$DB_PASSWORD" ]]; then
    log_result "Database reachable" "FAIL" "EOIP_DATABASE_PASSWORD is not set."
    return
  fi

  export PGPASSWORD="$DB_PASSWORD"

  if python - <<'PY' >/dev/null 2>&1
import os
import psycopg2

host = os.getenv('DB_HOST', 'localhost')
port = os.getenv('DB_PORT', '5432')
name = os.getenv('DB_NAME', 'eoip')
user = os.getenv('DB_USER', 'postgres')
password = os.getenv('DB_PASSWORD', '')

try:
    conn = psycopg2.connect(
        host=host,
        port=port,
        dbname=name,
        user=user,
        password=password,
        connect_timeout=5,
    )
    conn.close()
    raise SystemExit(0)
except Exception:
    raise SystemExit(1)
PY
  then
    log_result "Database reachable" "PASS" "Database is reachable on ${DB_HOST}:${DB_PORT}/${DB_NAME}."
  else
    log_result "Database reachable" "FAIL" "Database connection failed for ${DB_HOST}:${DB_PORT}/${DB_NAME}."
  fi
}

check_alembic_revision() {
  if ! command -v python >/dev/null 2>&1; then
    log_result "Alembic latest revision" "FAIL" "Python is not available."
    return
  fi

  local current_rev
  local head_rev

  current_rev="$(cd "$(dirname "$0")/.." && python -m alembic current 2>/dev/null | awk '{print $1}' | head -n 1)"
  head_rev="$(cd "$(dirname "$0")/.." && python -m alembic heads 2>/dev/null | awk '{print $1}' | head -n 1)"

  if [[ -n "$current_rev" && -n "$head_rev" && "$current_rev" == "$head_rev" ]]; then
    log_result "Alembic latest revision" "PASS" "Database is at the latest Alembic revision (${current_rev})."
  else
    log_result "Alembic latest revision" "FAIL" "Database revision is not at the latest head. Current=${current_rev:-unknown}; Head=${head_rev:-unknown}."
  fi
}

check_timescaledb_extension() {
  if [[ -z "$DB_PASSWORD" ]]; then
    log_result "TimescaleDB extension" "FAIL" "EOIP_DATABASE_PASSWORD is not set."
    return
  fi

  export PGPASSWORD="$DB_PASSWORD"

  if python - <<'PY' >/dev/null 2>&1
import os
import psycopg2

host = os.getenv('DB_HOST', 'localhost')
port = os.getenv('DB_PORT', '5432')
name = os.getenv('DB_NAME', 'eoip')
user = os.getenv('DB_USER', 'postgres')
password = os.getenv('DB_PASSWORD', '')

try:
    conn = psycopg2.connect(
        host=host,
        port=port,
        dbname=name,
        user=user,
        password=password,
        connect_timeout=5,
    )
    cur = conn.cursor()
    cur.execute("SELECT extversion FROM pg_extension WHERE extname='timescaledb';")
    result = cur.fetchone()
    cur.close()
    conn.close()
    raise SystemExit(0 if result and result[0] else 1)
except Exception:
    raise SystemExit(1)
PY
  then
    log_result "TimescaleDB extension" "PASS" "TimescaleDB extension is installed."
  else
    log_result "TimescaleDB extension" "FAIL" "TimescaleDB extension is not installed or not accessible."
  fi
}

check_http_endpoint() {
  local check_name="$1"
  local url="$2"
  local expected_status="$3"

  local http_code
  http_code="$(curl --silent --show-error --output /tmp/eoip_verify_body.txt --write-out '%{http_code}' --max-time 10 "$url" || true)"

  if [[ "$http_code" == "$expected_status" ]]; then
    log_result "$check_name" "PASS" "Endpoint ${url} returned HTTP ${http_code}."
  else
    log_result "$check_name" "FAIL" "Endpoint ${url} returned HTTP ${http_code}, expected ${expected_status}."
  fi
}

check_docker_running() {
  if ! command -v docker >/dev/null 2>&1; then
    log_result "Docker containers running" "FAIL" "Docker is not installed or not available in PATH."
    return
  fi

  local required_containers=("eoip-timescaledb" "eoip-api" "eoip-streamlit")
  local all_running=true

  for container in "${required_containers[@]}"; do
    if ! docker ps --format '{{.Names}}' | grep -Fxq "$container"; then
      all_running=false
      break
    fi
  done

  if [[ "$all_running" == true ]]; then
    log_result "Docker containers running" "PASS" "All required EOIP containers are running."
  else
    log_result "Docker containers running" "FAIL" "One or more required EOIP containers are not running."
  fi
}

check_db_connection
check_alembic_revision
check_timescaledb_extension
check_http_endpoint "FastAPI health endpoint" "${API_BASE_URL%/}/health" "200"
check_http_endpoint "Streamlit health endpoint" "${STREAMLIT_URL%/}/_stcore/health" "200"
check_docker_running

if [[ "$FAILURES" -eq 0 ]]; then
  echo
  echo "Deployment verification result: PASS"
  exit 0
else
  echo
  echo "Deployment verification result: FAIL"
  exit 1
fi
