# Git Deployment Sync Agent

Specialized agent for deploying OntExtract changes from local development (WSL) to production (DigitalOcean server at ontextract.ontorealm.net).

## Agent Purpose

This agent handles:
1. Code synchronization (local → GitHub → production)
2. Service management (nginx, gunicorn, systemd, Celery worker)
3. Database migrations and FK constraint updates
4. Environment-specific configuration differences
5. Verification and rollback procedures

## Production Server Details

**Server**: DigitalOcean droplet
**Domain**: ontextract.ontorealm.net
**SSH Access**: `ssh digitalocean` or `ssh chris@209.38.62.85`
**App Location**: `/opt/ontextract`
**Database**: PostgreSQL (ontextract_db)
**Services**:
- OntExtract Flask (systemd service: ontextract)
- Celery Worker (systemd service: celery-ontextract)
- Redis (for Celery broker)
- nginx (reverse proxy)
- gunicorn (WSGI server)

## Deployment Workflow

### Phase 1: Local Preparation

1. **Verify Local Changes**
   - Check git status for uncommitted changes
   - Review modified files
   - Ensure Flask and Celery are running locally
   - Test orchestration works locally

2. **Commit Current Changes**
   ```bash
   cd /home/chris/onto/OntExtract
   git status
   git add .
   git commit -m "Descriptive commit message"
   ```

### Phase 2: Git Operations

1. **Push to Development Branch**
   ```bash
   cd /home/chris/onto/OntExtract
   git push origin development
   ```

2. **Merge to Main (for production)**
   ```bash
   git checkout main
   git merge development
   git push origin main
   git checkout development  # Return to development
   ```

### Phase 3: Production Server Deployment

1. **SSH to Production**
   ```bash
   ssh digitalocean
   ```

2. **Deploy Code Updates**
   ```bash
   cd /opt/ontextract

   # Pull latest code
   git fetch origin
   git pull origin main

   # Activate virtual environment and update dependencies
   source venv/bin/activate
   pip install -r requirements.txt  # if requirements changed
   deactivate
   ```

3. **Apply Database Migrations** (if schema changed)
   ```bash
   # Run migrations
   cd /opt/ontextract
   source venv/bin/activate
   flask db upgrade
   deactivate
   ```

4. **Apply Database Fixes** (if needed for this deployment)
   ```bash
   # Example: Fix FK constraint for ProcessingArtifactGroup
   sudo -u postgres PGPASSWORD=PASS psql -d ontextract_db -c "
   ALTER TABLE processing_artifact_groups
   DROP CONSTRAINT IF EXISTS processing_artifact_groups_document_id_fkey,
   ADD CONSTRAINT processing_artifact_groups_document_id_fkey
   FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE;"

   # Add any other DB updates as needed
   ```

5. **Restart Services**
   ```bash
   # Restart Flask application
   sudo systemctl restart ontextract

   # Restart Celery worker
   sudo systemctl restart celery-ontextract

   # Verify services are running
   sudo systemctl status ontextract
   sudo systemctl status celery-ontextract
   sudo systemctl status redis
   ```

### Phase 4: Verification

1. **Check Service Status**
   ```bash
   sudo systemctl status ontextract
   sudo systemctl status celery-ontextract
   sudo systemctl status redis
   sudo systemctl status nginx
   ```

2. **Verify Application**
   ```bash
   # Local endpoint
   curl http://localhost:8080

   # Public endpoint
   curl https://ontextract.ontorealm.net
   ```

3. **Check Logs** (if issues)
   ```bash
   # Flask logs
   sudo journalctl -u ontextract -n 100 --follow

   # Celery logs
   sudo journalctl -u celery-ontextract -n 100 --follow

   # Nginx logs
   tail -f /var/log/nginx/error.log
   ```

4. **Test Orchestration**
   - Navigate to https://ontextract.ontorealm.net
   - Create or use an existing experiment
   - Run LLM orchestration
   - Verify ProcessingArtifactGroups are created
   - Check that processing results display in UI

### Phase 5: Rollback (if needed)

```bash
cd /opt/ontextract
git log --oneline -5  # Note the previous commit hash
git reset --hard <previous-commit-hash>
sudo systemctl restart ontextract
sudo systemctl restart celery-ontextract
```

## Environment Differences

### Development (WSL/Local)
- **Database**: ontextract_db (localhost:5432)
- **Port**: 8765 (Flask development server)
- **Debug**: Enabled
- **URL**: http://localhost:8765
- **User**: chris
- **Location**: /home/chris/onto/OntExtract
- **Celery**: Manual start via `./start_celery_worker.sh`
- **Redis**: localhost:6379
- **Virtual Environment**: venv-ontextract

### Production (DigitalOcean)
- **Database**: ontextract_db (localhost:5432, different server)
  - **DB User**: postgres (for admin)
  - **DB Password**: PASS
  - **Connection**: postgresql://postgres:PASS@localhost:5432/ontextract_db
- **Port**: 8080 (gunicorn) → nginx proxy → 80/443
- **Debug**: Disabled
- **URL**: https://ontextract.ontorealm.net
- **User**: chris (but app runs as systemd service)
- **Location**: /opt/ontextract
- **Celery**: systemd service (celery-ontextract)
- **Redis**: systemd service
- **Virtual Environment**: venv

### Configuration Files to Check

1. **Environment Variables**
   - Development: `.env` file (not committed, includes API keys)
   - Production: `/etc/systemd/system/ontextract.service` (Environment variables)

2. **Database Connections**
   - Both use postgres user with PASS password
   - Different database instances on different servers

3. **Service Configuration**
   - Development: Manual `python run.py` + manual Celery worker
   - Production: systemd services (ontextract + celery-ontextract) + gunicorn + nginx

## Service Files

### Flask Application Service
**Location**: `/etc/systemd/system/ontextract.service`

Key configuration:
- WorkingDirectory=/opt/ontextract
- ExecStart with gunicorn
- Environment variables (DATABASE_URL, API keys, etc.)

### Celery Worker Service
**Location**: `/etc/systemd/system/celery-ontextract.service`

Key configuration:
- WorkingDirectory=/opt/ontextract
- ExecStart with celery worker command
- Environment variables (must match Flask service)
- Requires Redis

### Nginx Configuration
**Location**: `/etc/nginx/sites-available/ontextract`

Key configuration:
- Proxy to localhost:8080
- SSL certificates
- Domain: ontextract.ontorealm.net

## Common Tasks

### Deploy Code Only (No Database Changes)
```bash
# Local
cd /home/chris/onto/OntExtract
git add .
git commit -m "Update message"
git push origin development
git checkout main && git merge development && git push origin main && git checkout development

# Production
ssh digitalocean "cd /opt/ontextract && git pull origin main && sudo systemctl restart ontextract && sudo systemctl restart celery-ontextract"
```

### Deploy Code + Database Schema Changes
```bash
# Local - commit and push code with migrations
cd /home/chris/onto/OntExtract
git add .
git commit -m "Update with schema changes"
git push origin development
git checkout main && git merge development && git push origin main && git checkout development

# Production - deploy code and run migrations
ssh digitalocean "cd /opt/ontextract && git pull origin main && source venv/bin/activate && flask db upgrade && deactivate && sudo systemctl restart ontextract && sudo systemctl restart celery-ontextract"
```

### Deploy Code + Database Fixes (like FK constraints)
```bash
# Local - commit and push code
cd /home/chris/onto/OntExtract
git add .
git commit -m "Fix FK constraints and artifact tracking"
git push origin development
git checkout main && git merge development && git push origin main && git checkout development

# Production - deploy code and apply DB fixes
ssh digitalocean << 'EOF'
cd /opt/ontextract
git pull origin main

# Apply FK constraint fix
sudo -u postgres PGPASSWORD=PASS psql -d ontextract_db -c "
ALTER TABLE processing_artifact_groups
DROP CONSTRAINT IF EXISTS processing_artifact_groups_document_id_fkey,
ADD CONSTRAINT processing_artifact_groups_document_id_fkey
FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE;"

# Restart services
sudo systemctl restart ontextract
sudo systemctl restart celery-ontextract
sudo systemctl status ontextract
sudo systemctl status celery-ontextract
EOF
```

### Check Service Logs
```bash
# Flask logs
ssh digitalocean "sudo journalctl -u ontextract -n 100 --follow"

# Celery logs
ssh digitalocean "sudo journalctl -u celery-ontextract -n 100 --follow"
```

### Restart Services
```bash
ssh digitalocean "sudo systemctl restart ontextract && sudo systemctl restart celery-ontextract && sudo systemctl status ontextract && sudo systemctl status celery-ontextract"
```

### Monitor Celery Worker
```bash
ssh digitalocean "ps aux | grep celery"
ssh digitalocean "sudo journalctl -u celery-ontextract -n 50 --follow"
```

## Pre-Deployment Checklist

- [ ] All local changes committed
- [ ] Flask and Celery running locally
- [ ] Orchestration tested locally (artifact groups created)
- [ ] Requirements.txt updated (if new dependencies)
- [ ] Migration files created (if database schema changed)
- [ ] Environment variables documented (if new variables added)
- [ ] Git main branch up to date
- [ ] FK constraint fixes documented (if needed)

## Post-Deployment Verification

- [ ] OntExtract service running: `sudo systemctl status ontextract`
- [ ] Celery service running: `sudo systemctl status celery-ontextract`
- [ ] Redis service running: `sudo systemctl status redis`
- [ ] Nginx service running: `sudo systemctl status nginx`
- [ ] Application responds: `curl https://ontextract.ontorealm.net`
- [ ] No errors in Flask logs: `sudo journalctl -u ontextract -n 50`
- [ ] No errors in Celery logs: `sudo journalctl -u celery-ontextract -n 50`
- [ ] Test orchestration workflow works (create experiment, run orchestration)
- [ ] ProcessingArtifactGroups created correctly
- [ ] Processing results display in UI

## Troubleshooting

### Flask Service Won't Start
```bash
sudo journalctl -u ontextract -n 100
# Check for Python errors, import errors, database connection issues
```

### Celery Worker Won't Start
```bash
sudo journalctl -u celery-ontextract -n 100
# Check for Redis connection, API key issues, import errors
```

### API Key Issues (401 Errors in Celery)
```bash
# Verify environment variables in Celery service
sudo systemctl cat celery-ontextract | grep ANTHROPIC_API_KEY

# Update service file if needed
sudo nano /etc/systemd/system/celery-ontextract.service
sudo systemctl daemon-reload
sudo systemctl restart celery-ontextract
```

### Database Connection Errors
```bash
# Check PostgreSQL is running
sudo systemctl status postgresql

# Test database connection
sudo -u postgres PGPASSWORD=PASS psql -d ontextract_db -c "SELECT COUNT(*) FROM documents;"
```

### Redis Connection Issues
```bash
# Check Redis is running
sudo systemctl status redis

# Test Redis connection
redis-cli ping  # Should return PONG
```

### Permission Issues
```bash
# Check file ownership
ls -la /opt/ontextract

# Fix ownership if needed
sudo chown -R chris:chris /opt/ontextract
```

### Nginx Issues
```bash
sudo nginx -t  # Test configuration
sudo systemctl status nginx
sudo tail -f /var/log/nginx/error.log
```

### Celery Worker Not Processing Tasks
```bash
# Check if worker is connected to Redis
redis-cli KEYS '*celery*'

# Check Celery logs
sudo journalctl -u celery-ontextract -n 200

# Restart Celery
sudo systemctl restart celery-ontextract
```

### FK Constraint Errors on Document Deletion
If you see "null value in column document_id violates not-null constraint" errors:

```bash
# Fix FK constraint to use CASCADE instead of SET NULL
sudo -u postgres PGPASSWORD=PASS psql -d ontextract_db -c "
ALTER TABLE processing_artifact_groups
DROP CONSTRAINT IF EXISTS processing_artifact_groups_document_id_fkey,
ADD CONSTRAINT processing_artifact_groups_document_id_fkey
FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE;"
```

## Current Deployment Context (Session 29)

**Changes to Deploy:**
1. ProcessingArtifactGroup tracking during LLM orchestration
2. Document ID type conversion fix (string to int)
3. Status field normalization ("success" → "executed") for UI compatibility
4. FK constraint fix (CASCADE on delete)

**Files Modified:**
- app/services/extraction_tools.py
- app/orchestration/experiment_nodes.py
- Database: processing_artifact_groups FK constraint

**Testing:**
- Local: Working (Celery + artifact tracking + UI display)
- Production: Needs deployment

## Agent Usage

When you need to deploy OntExtract to production, invoke this agent with:

**Code-only deployment:**
"Deploy the latest OntExtract changes to production"

**Code + database fixes:**
"Deploy OntExtract to production with FK constraint fixes"

**Code + migrations:**
"Deploy OntExtract to production with database migrations"

**Rollback:**
"Rollback OntExtract production to the previous version"

**Service restart only:**
"Restart OntExtract services on production"

The agent will handle the complete workflow including verification and error handling.
