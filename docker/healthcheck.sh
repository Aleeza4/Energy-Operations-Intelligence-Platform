#!/usr/bin/env bash
set -euo pipefail

DB_HOST="${EOIP_DATABASE_HOST:-timescaledb}"
DB_PORT="${EOIP_DATABASE_PORT:-5432}"
DB_NAME="${EOIP_DATABASE_NAME:-eoip}"
DB_USER="${EOIP_DATABASE_USER:-eoip_user}"
API_URL="${EOIP_API_BASE_URL:-http://127.0.0.1:8000/api/v1}"
STREAMLIT_URL="${EOIP_STREAMLIT_BASE_URL:-http://127.0.0.1:8501}"

check_db() {
  if command -v pg_isready >/dev/null 2>&1; then
    pg_isready -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME"
  else
    python - <<'PY'
import os, sys
from urllib.parse import urlparse
import psycopg2

host = os.getenv('EOIP_DATABASE_HOST', 'timescaledb')
port = os.getenv('EOIP_DATABASE_PORT', '5432')
name = os.getenv('EOIP_DATABASE_NAME', 'eoip')
user = os.getenv('EOIP_DATABASE_USER', 'eoip_user')
password = os.getenv('EOIP_DATABASE_PASSWORD', 'eoip_password')

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
    print(f'Database health check passed: {host}:{port}/{name}')
except Exception as exc:  # pragma: no cover - runtime health check
    print(f'Database health check failed: {exc}', file=sys.stderr)
    raise SystemExit(1)
PY
  fi
}

check_api() {
  curl --silent --show-error --fail --max-time 10 "${API_URL}/health"
}

check_streamlit() {
  curl --silent --show-error --fail --max-time 10 "${STREAMLIT_URL}/_stcore/health"
}

main() {
  local target="${1:-all}"

  case "$target" in
    db)
      check_db
      ;;
    api)
      check_api
      ;;
    streamlit)
      check_streamlit
      ;;
    all)
      echo "Checking database..."
      check_db
      echo "Checking API..."
      check_api
      echo "Checking Streamlit..."
      check_streamlit
      echo "All EOIP services are healthy."
      ;;
    *)
      echo "Usage: $0 [db|api|streamlit|all]" >&2
      exit 2
      ;;
  esac
}

main "$@"
