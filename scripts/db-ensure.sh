#!/usr/bin/env bash
set -euo pipefail

HOST="${DB_HOST:-db}"
PORT="${DB_PORT:-5432}"
USER="${POSTGRES_USER:-postgres}"
DB_NAME="${POSTGRES_DB:-ontextract_db}"

export PGPASSWORD="${POSTGRES_PASSWORD:-PASS}"

echo "Waiting for Postgres at ${HOST}:${PORT}..."
until pg_isready -h "$HOST" -p "$PORT" -U "$USER" -d postgres >/dev/null 2>&1; do
  sleep 1
done

echo "Ensuring database '${DB_NAME}' exists..."
DB_EXISTS=$(psql -h "$HOST" -p "$PORT" -U "$USER" -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname='${DB_NAME}'" || echo "")
if [[ "$DB_EXISTS" != "1" ]]; then
  psql -h "$HOST" -p "$PORT" -U "$USER" -d postgres -c "CREATE DATABASE ${DB_NAME};"
  echo "Created database ${DB_NAME}"
else
  echo "Database ${DB_NAME} already exists"
fi

echo "Ensuring required extensions are installed..."
psql -h "$HOST" -p "$PORT" -U "$USER" -d "$DB_NAME" -v ON_ERROR_STOP=1 <<'SQL'
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS pg_trgm;
SQL

# Set DB timezone (idempotent; ignore errors)
psql -h "$HOST" -p "$PORT" -U "$USER" -d postgres -c "ALTER DATABASE ${DB_NAME} SET timezone TO 'UTC';" || true

echo "DB ensure complete."
