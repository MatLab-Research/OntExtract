#!/bin/bash

# OntExtract Database Restore Script
# Usage: ./restore_ontextract_db.sh <backup_file> <db_password>

set -e

if [ $# -lt 2 ]; then
    echo "Usage: $0 <backup_file> <db_password>"
    echo "Example: $0 ontextract_db_backup_20250901_172601.backup my_server_password"
    exit 1
fi

BACKUP_FILE="$1"
DB_PASSWORD="$2"
DB_HOST="localhost"  # Change this to your server host
DB_PORT="5432"
DB_NAME="ontextract_db"
DB_USER="ontextract_user"

echo "🔄 Restoring OntExtract database from $BACKUP_FILE..."

# Set password for pg_restore
export PGPASSWORD="$DB_PASSWORD"

# Check if database exists and drop it if it does
echo "📋 Checking if database exists..."
if psql --username="$DB_USER" --host="$DB_HOST" --port="$DB_PORT" --list | grep -q "$DB_NAME"; then
    echo "🗑️  Dropping existing database..."
    psql --username="$DB_USER" --host="$DB_HOST" --port="$DB_PORT" --command="DROP DATABASE IF EXISTS $DB_NAME;"
fi

# Create fresh database
echo "🆕 Creating new database..."
psql --username="$DB_USER" --host="$DB_HOST" --port="$DB_PORT" --command="CREATE DATABASE $DB_NAME;"

# Determine backup format and restore accordingly
if [[ "$BACKUP_FILE" == *.backup ]]; then
    echo "📦 Restoring from custom format backup..."
    pg_restore --username="$DB_USER" --host="$DB_HOST" --port="$DB_PORT" --dbname="$DB_NAME" --no-password --verbose "$BACKUP_FILE"
elif [[ "$BACKUP_FILE" == *.sql ]]; then
    echo "📄 Restoring from SQL format backup..."
    psql --username="$DB_USER" --host="$DB_HOST" --port="$DB_PORT" --dbname="$DB_NAME" --file="$BACKUP_FILE"
else
    echo "❌ Unknown backup format. Please use .backup or .sql files."
    exit 1
fi

echo "✅ Database restore completed successfully!"
echo "🔍 You can verify the restore by connecting to the database:"
echo "   psql --username=$DB_USER --host=$DB_HOST --port=$DB_PORT --dbname=$DB_NAME"
