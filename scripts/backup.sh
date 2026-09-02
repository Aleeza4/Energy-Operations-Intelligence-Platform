#!/usr/bin/env bash
set -euo pipefail

BACKUP_DIR="${EOIP_BACKUP_DIR:-/var/backups/eoip}"
DB_HOST="${EOIP_DATABASE_HOST:-timescaledb}"
DB_PORT="${EOIP_DATABASE_PORT:-5432}"
DB_NAME="${EOIP_DATABASE_NAME:-eoip}"
DB_USER="${EOIP_DATABASE_USER:-eoip_user}"
DB_PASSWORD="${EOIP_DATABASE_PASSWORD:-eoip_password}"
RETENTION_DAYS="${EOIP_BACKUP_RETENTION_DAYS:-7}"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
BACKUP_FILE="eoip_backup_${TIMESTAMP}.sql.gz"
BACKUP_PATH="${BACKUP_DIR}/${BACKUP_FILE}"
LOG_PREFIX="[EOIP BACKUP]"

mkdir -p "${BACKUP_DIR}"

log() {
  echo "${LOG_PREFIX} $1"
}

cleanup_old_backups() {
  if [[ -d "${BACKUP_DIR}" ]]; then
    find "${BACKUP_DIR}" -type f -name 'eoip_backup_*.sql.gz' -mtime +"${RETENTION_DAYS}" -delete
    log "Removed backups older than ${RETENTION_DAYS} days in ${BACKUP_DIR}."
  fi
}

main() {
  if ! command -v pg_dump >/dev/null 2>&1; then
    log "ERROR: pg_dump is not installed or not in PATH."
    exit 1
  fi

  export PGPASSWORD="${DB_PASSWORD}"

  log "Starting backup for database '${DB_NAME}' from host '${DB_HOST}:${DB_PORT}'"

  if pg_dump \
    -h "${DB_HOST}" \
    -p "${DB_PORT}" \
    -U "${DB_USER}" \
    -d "${DB_NAME}" \
    --clean \
    --if-exists \
    --create \
    --compress=9 \
    | gzip -c > "${BACKUP_PATH}"; then
    log "SUCCESS: Backup created successfully at ${BACKUP_PATH}"
    cleanup_old_backups
    exit 0
  else
    log "ERROR: Backup failed for database '${DB_NAME}'."
    if [[ -f "${BACKUP_PATH}" ]]; then
      rm -f "${BACKUP_PATH}"
    fi
    exit 1
  fi
}

main "$@"
