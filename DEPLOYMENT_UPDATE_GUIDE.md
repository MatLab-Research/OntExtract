# OntExtract Production Deployment Update Guide

**Target Environment**: OntServe.net production server (nginx + gunicorn)
**Last Updated**: December 21, 2025
**Update Type**: Enhanced Entity Extraction + Live Processing Dashboard

---

## Pre-Deployment Assessment

### Database Changes Analysis
The recent updates include significant database model changes:

1. **New Models Added**:
   - `ExperimentDocumentProcessing` - Core processing operations tracking
   - `ProcessingArtifact` - Individual processing results storage
   - `DocumentProcessingIndex` - Processing operation indexing

2. **Schema Modifications**:
   - Enhanced experiment processing with detailed status tracking
   - Character-level positioning for entity extraction
   - Processing metadata and artifact storage

3. **Data Relationships**:
   - New foreign key relationships between experiments, documents, and processing operations
   - Complex data dependencies that would be difficult to recreate

### Recommended Approach: Database Migration (NOT Full Dump/Restore)

**Reasoning**:
- **Preserve Existing Data**: Production likely has experiments and documents that shouldn't be lost
- **Schema Evolution**: Migrations handle incremental changes better than full replacement
- **Rollback Safety**: Migrations can be more easily reversed if issues occur
- **Data Integrity**: Avoids potential foreign key constraint issues during restore

---

## Step-by-Step Deployment Process

### Phase 1: Pre-Deployment Preparation

1. **Create Database Backup** (Safety First):
   ```bash
   # On production server
   sudo -u postgres pg_dump ontextract_db > /opt/ontextract/backups/pre_update_$(date +%Y%m%d_%H%M%S).sql
   ```

2. **Check Current Production Schema**:
   ```bash
   # Connect to production database
   sudo -u postgres psql ontextract_db
   \dt  # List all tables
   \d experiment_documents_v2  # Check if new models exist
   \d experiment_document_processing  # Check processing table
   \q
   ```

3. **Prepare Migration Files**:
   ```bash
   # Create migration script if needed
   # Check what tables/columns need to be added
   ```

### Phase 2: Application Code Deployment

1. **Stop Gunicorn Service**:
   ```bash
   sudo systemctl stop ontextract
   # or
   sudo supervisorctl stop ontextract
   ```

2. **Backup Current Code**:
   ```bash
   cd /opt/ontextract
   sudo cp -r . ../ontextract_backup_$(date +%Y%m%d_%H%M%S)
   ```

3. **Deploy New Code**:
   ```bash
   # Option A: Git pull (if using git)
   sudo git pull origin main

   # Option B: File transfer (if copying from development)
   # rsync or scp the updated files
   sudo rsync -av --exclude='.git' /path/to/local/OntExtract/ /opt/ontextract/
   ```

4. **Update Dependencies**:
   ```bash
   cd /opt/ontextract
   sudo -u ontextract /opt/ontextract/venv/bin/pip install -r requirements.txt
   ```

### Phase 3: Database Migration

1. **Check Flask Migration System**:
   ```bash
   cd /opt/ontextract
   sudo -u ontextract /opt/ontextract/venv/bin/python -c "
   from flask import Flask
   from app import create_app, db
   app = create_app()
   with app.app_context():
       from sqlalchemy import inspect
       inspector = inspect(db.engine)
       tables = inspector.get_table_names()
       print('Current tables:', tables)
   "
   ```

2. **Run Database Initialization/Migration**:
   ```bash
   # Initialize database schema with new models
   sudo -u ontextract /opt/ontextract/venv/bin/python -c "
   from app import create_app, db
   app = create_app()
   with app.app_context():
       db.create_all()  # Creates new tables, preserves existing data
       print('Database schema updated successfully')
   "
   ```

3. **Verify Migration Success**:
   ```bash
   # Check that new tables exist
   sudo -u postgres psql ontextract_db -c "\dt"
   sudo -u postgres psql ontextract_db -c "\d experiment_document_processing"
   ```

### Phase 4: Environment Configuration

1. **Update Environment Variables** (if needed):
   ```bash
   # Check /opt/ontextract/.env for any new variables
   # Ensure GOOGLE_GEMINI_API_KEY is set for enhanced entity extraction
   sudo nano /opt/ontextract/.env
   ```

2. **Verify Nginx Configuration**:
   ```bash
   # Check nginx config is still correct
   sudo nginx -t
   # Reload if needed
   sudo systemctl reload nginx
   ```

### Phase 5: Service Restart and Verification

1. **Start Gunicorn Service**:
   ```bash
   sudo systemctl start ontextract
   sudo systemctl status ontextract

   # Check logs for any errors
   sudo journalctl -u ontextract -f
   ```

2. **Verify Application Health**:
   ```bash
   # Test application endpoints
   curl -s http://localhost:8765/ | grep -i "ontextract"
   curl -s http://localhost:8765/process/ | grep -i "processing"
   ```

3. **Test New Features**:
   - Visit OntServe.net/process/ to verify live dashboard
   - Test entity extraction with LangExtract + Gemini
   - Verify experiment processing operations display correctly

---

## Rollback Plan (If Issues Occur)

### Emergency Rollback:
1. **Stop Service**: `sudo systemctl stop ontextract`
2. **Restore Code**: `sudo cp -r ../ontextract_backup_[timestamp]/* /opt/ontextract/`
3. **Restore Database**: `sudo -u postgres psql ontextract_db < /opt/ontextract/backups/pre_update_[timestamp].sql`
4. **Restart Service**: `sudo systemctl start ontextract`

### Partial Rollback (Code Only):
If database migration succeeded but application has issues:
1. Fix code issues in development
2. Redeploy just the application code
3. Database schema can remain as new models are backward compatible

---

## Post-Deployment Verification Checklist

- [ ] Application starts without errors
- [ ] Processing dashboard shows live data (not placeholder)
- [ ] Entity extraction modals show "LangExtract + Gemini" options
- [ ] All navigation links work correctly
- [ ] Database contains new processing tables
- [ ] Log files show no critical errors
- [ ] Performance is acceptable

---

## Key Files That Changed

### Application Code:
- `app/routes/experiments.py` - Enhanced entity extraction with LangExtract
- `app/routes/processing.py` - Live processing dashboard data
- `app/services/integrated_langextract_service.py` - New entity extraction method
- `app/services/langextract_document_analyzer.py` - Enhanced entity analysis
- `app/templates/processing/` - Updated dashboard templates
- `app/templates/experiments/` - Updated processing modals

### Database Models:
- `app/models/experiment_processing.py` - New processing tracking models
- Existing experiment and document models (no breaking changes)

### Environment Requirements:
- GOOGLE_GEMINI_API_KEY required for enhanced entity extraction
- All existing environment variables remain the same

---

## Troubleshooting Common Issues

### Issue: Import Errors for New Models
**Solution**: Ensure all new model files are deployed and Python can import them

### Issue: Database Connection Errors
**Solution**: Verify database credentials and connection string in environment

### Issue: Missing API Key Errors
**Solution**: Set GOOGLE_GEMINI_API_KEY in production environment

### Issue: Template Not Found Errors
**Solution**: Verify all template files were deployed correctly

### Issue: 404 Errors on Processing Pages
**Solution**: Check URL routing and ensure blueprint registration

---

## Contact Information

If deployment issues occur:
- Check application logs: `/opt/ontextract/logs/` or `journalctl -u ontextract`
- Verify nginx logs: `/var/log/nginx/error.log`
- Database issues: Check PostgreSQL logs
- Emergency rollback: Use the rollback plan above

**Remember**: This update enhances existing functionality without removing features. The migration approach preserves all existing data while adding new capabilities.