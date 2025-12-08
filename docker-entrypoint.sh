#!/bin/bash
set -e

echo "=========================================="
echo "OntExtract Docker Container Starting"
echo "=========================================="

# Wait for PostgreSQL to be ready
echo "Waiting for PostgreSQL..."
until PGPASSWORD=$POSTGRES_PASSWORD psql -h "postgres" -U "postgres" -d "$POSTGRES_DB" -c '\q' 2>/dev/null; do
  >&2 echo "PostgreSQL is unavailable - sleeping"
  sleep 2
done
echo "PostgreSQL is ready"

# Wait for Redis to be ready
echo "Waiting for Redis..."
until redis-cli -u "$REDIS_URL" ping 2>/dev/null; do
  >&2 echo "Redis is unavailable - sleeping"
  sleep 2
done
echo "Redis is ready"

# Only initialize database for web service (not celery workers)
if [[ "$1" == "python" ]] && [[ "$2" == "run.py" ]]; then
    echo "Initializing database schema..."

    # Check if alembic_version table exists
    if PGPASSWORD=$POSTGRES_PASSWORD psql -h "postgres" -U "postgres" -d "$POSTGRES_DB" -c "SELECT 1 FROM alembic_version LIMIT 1;" 2>/dev/null; then
        echo "Database already initialized, running migrations..."
        flask db upgrade || echo "Migrations failed or not needed"
    else
        echo "Fresh database detected, creating schema..."
        python -c "from app import create_app, db; app = create_app(); app.app_context().push(); db.create_all(); print('Schema created')"

        # Stamp database with current migration
        echo "Marking database as up-to-date..."
        flask db stamp head
    fi

    # Create default admin user if environment variables are set
    if [ -n "$CREATE_DEFAULT_ADMIN" ] && [ "$CREATE_DEFAULT_ADMIN" = "true" ]; then
        echo "Creating default admin user..."
        python init_admin.py || echo "Admin user may already exist"
    fi

    # Seed default prompt templates and settings
    echo "Seeding default templates and settings..."
    flask seed-defaults || echo "Defaults may already exist"
else
    echo "Celery worker - skipping database initialization"
fi

echo "=========================================="
echo "Starting application..."
echo "=========================================="

# Execute the main command
exec "$@"
