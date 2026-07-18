#!/usr/bin/env bash
set -euo pipefail

COMPOSE_PROJECT="${COMPOSE_PROJECT:-}"
POSTGRES_DB_NAME="${POSTGRES_DB:-english_ai_writing}"
POSTGRES_USER_NAME="${POSTGRES_USER:-english_ai}"

if [[ "${CONFIRM_RESET:-}" != "RESET_UAT_DB" ]]; then
  echo "Refusing to reset the database without CONFIRM_RESET=RESET_UAT_DB."
  echo "This deletes local UAT data and recreates the seeded database."
  exit 2
fi

compose() {
  if [[ -n "${COMPOSE_PROJECT}" ]]; then
    docker compose -p "${COMPOSE_PROJECT}" "$@"
  else
    docker compose "$@"
  fi
}

echo "Stopping app services that may hold database connections..."
compose stop api marking-worker web >/dev/null 2>&1 || true

echo "Terminating active connections to ${POSTGRES_DB_NAME}..."
compose exec -T postgres psql \
  -U "${POSTGRES_USER_NAME}" \
  -d postgres \
  -v ON_ERROR_STOP=1 \
  -c "select pg_terminate_backend(pid) from pg_stat_activity where datname = '${POSTGRES_DB_NAME}' and pid <> pg_backend_pid();"

echo "Dropping and recreating ${POSTGRES_DB_NAME}..."
compose exec -T postgres dropdb -U "${POSTGRES_USER_NAME}" --if-exists "${POSTGRES_DB_NAME}"
compose exec -T postgres createdb -U "${POSTGRES_USER_NAME}" "${POSTGRES_DB_NAME}"

echo "Starting dependencies and API..."
compose up -d postgres redis auth grammar-service api

echo "Running Alembic migrations and seeded baseline..."
compose exec -T api alembic upgrade head

echo "Starting web and worker..."
compose up -d web marking-worker

echo "UAT database reset complete."
