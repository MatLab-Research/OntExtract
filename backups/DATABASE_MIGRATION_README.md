# OntExtract Database Migration Guide

## Backup Files Created

Two backup formats have been created for maximum compatibility:

1. **Custom Format** (`.backup`): `ontextract_db_backup_20250901_172601.backup` (209KB)
   - Compressed and efficient
   - Preserves all database objects, permissions, and metadata
   - Recommended for production restores

2. **Plain SQL Format** (`.sql`): `ontextract_db_backup_20250901_172618.sql` (400KB)
   - Human-readable SQL commands
   - Good for review and manual modifications
   - Compatible with most PostgreSQL versions

## Database Details

- **Database Name**: `ontextract_db`
- **Username**: `ontextract_user`
- **Host**: `localhost` (change to server host when restoring)
- **Port**: `5432`
- **Original Password**: `ontextract_development_password` (different on server)

## Migration Steps

### 1. Transfer Backup Files to Server

Copy the backup files to your server:
```bash
scp backups/ontextract_db_backup_20250901_172601.backup user@server:/path/to/backups/
scp backups/ontextract_db_backup_20250901_172618.sql user@server:/path/to/backups/
scp backups/restore_ontextract_db.sh user@server:/path/to/backups/
```

### 2. Prepare Server Environment

Ensure PostgreSQL is running and the `ontextract_user` exists on the server:
```bash
# Check PostgreSQL status
sudo systemctl status postgresql

# Create user if needed (adjust password for server)
sudo -u postgres psql -c "CREATE USER ontextract_user WITH PASSWORD 'your_server_password';"
sudo -u postgres psql -c "ALTER USER ontextract_user CREATEDB;"
```

### 3. Restore Database

#### Option A: Using the Restore Script (Recommended)

```bash
# Make script executable
chmod +x restore_ontextract_db.sh

# Run restore (replace with your server password)
./restore_ontextract_db.sh ontextract_db_backup_20250901_172601.backup your_server_password
```

#### Option B: Manual Restore

For custom format:
```bash
export PGPASSWORD='your_server_password'
pg_restore --username=ontextract_user --host=localhost --port=5432 --dbname=ontextract_db --no-password --verbose ontextract_db_backup_20250901_172601.backup
```

For SQL format:
```bash
export PGPASSWORD='your_server_password'
psql --username=ontextract_user --host=localhost --port=5432 --dbname=ontextract_db --file=ontextract_db_backup_20250901_172618.sql
```

### 4. Verify Restore

Connect to the database and verify the data:
```bash
psql --username=ontextract_user --host=localhost --port=5432 --dbname=ontextract_db

# Check tables
\d

# Check data in a few tables
SELECT COUNT(*) FROM documents;
SELECT COUNT(*) FROM ontologies;
SELECT COUNT(*) FROM extracted_entities;
```

## Important Notes

- **Password Difference**: The password on your server is different from the development environment
- **User Permissions**: Ensure `ontextract_user` has appropriate permissions on the server
- **Database Ownership**: The restore will maintain the original ownership structure
- **Backup Verification**: Always test restores in a non-production environment first

## Troubleshooting

If you encounter permission issues:
```bash
# Grant necessary permissions
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE ontextract_db TO ontextract_user;"
```

If the database already exists:
```bash
# Drop and recreate
sudo -u postgres psql -c "DROP DATABASE IF EXISTS ontextract_db;"
sudo -u postgres psql -c "CREATE DATABASE ontextract_db OWNER ontextract_user;"
```
