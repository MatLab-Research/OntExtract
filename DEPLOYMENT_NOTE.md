# 🚨 DEPLOYMENT NOTE FOR SERVER - August 24, 2025

## CRITICAL: Major OntExtract Updates Ready for Production

This note is for Claude on the production server to execute the deployment of significant OntExtract changes.

## 📋 SUMMARY OF CHANGES

### 1. Term Management System Enhancement ✅
- **Citation Field Implementation**: Added `source_citation` field to `term_versions` table for PROV-O compliance
- **Dynamic Version Switching**: JavaScript-powered UI for switching between temporal versions
- **Merriam-Webster Integration**: Auto-population of citations from dictionary API
- **Admin Delete Functionality**: Safe cascade deletion with proper foreign key handling
- **Permission Controls**: Admin-only delete with Bootstrap confirmation modals

### 2. Database Schema Changes REQUIRED
- New column: `source_citation TEXT` added to `term_versions` table
- Migration script: `/home/chris/onto/OntExtract/migrations/add_citation_field.sql`

## 🚀 DEPLOYMENT STEPS

### Step 1: Backup Database
```bash
# CRITICAL: Create backup before any changes
pg_dump ontextract_db > backup_ontextract_$(date +%Y%m%d_%H%M%S).sql
```

### Step 2: Stop Application
```bash
# Stop the running container
docker-compose down
```

### Step 3: Pull Latest Code
```bash
cd /home/chris/onto/OntExtract
git pull origin dev  # or main, depending on which branch is deployed
```

### Step 4: Run Database Migration
```bash
# Apply the citation field migration
docker-compose run --rm web psql -h db -U postgres -d ontextract_db -f migrations/add_citation_field.sql

# Verify migration success
docker-compose run --rm web psql -h db -U postgres -d ontextract_db -c "SELECT column_name FROM information_schema.columns WHERE table_name = 'term_versions' AND column_name = 'source_citation';"
```

### Step 5: Rebuild and Start Application
```bash
# Rebuild with latest code changes
docker-compose build

# Start the application
docker-compose up -d

# Check logs for startup errors
docker-compose logs -f web
```

### Step 6: Verify Deployment
```bash
# Check application is running
curl -I http://localhost:8765

# Test term management page loads
curl -s http://localhost:8765/terms/ | grep -q "Terms" && echo "✅ Terms page working"

# Check database connection
docker-compose exec web python -c "from app import create_app, db; app = create_app(); app.app_context().push(); print('✅ Database connection OK')"
```

## 📂 FILES CHANGED

### New/Modified Files to Deploy:
```
app/models/term.py                     # MODIFIED - Added source_citation field
app/routes/terms.py                    # MODIFIED - Delete functionality, citation handling
app/templates/terms/index.html         # MODIFIED - Admin delete buttons, dynamic citations
app/forms.py                           # MODIFIED - Added citation field to forms
migrations/add_citation_field.sql      # NEW - Database migration script
```

### Frontend Changes:
- JavaScript for dynamic version switching in term detail view
- Bootstrap modal for delete confirmation
- Citation display in Term Information section

## ⚠️ ROLLBACK PROCEDURE (if needed)

```bash
# 1. Stop application
docker-compose down

# 2. Restore database backup
docker-compose run --rm db psql -U postgres -c "DROP DATABASE IF EXISTS ontextract_db;"
docker-compose run --rm db psql -U postgres -c "CREATE DATABASE ontextract_db;"
docker-compose run --rm db psql -U postgres ontextract_db < backup_ontextract_[timestamp].sql

# 3. Revert code
git checkout [previous-commit-hash]

# 4. Rebuild and restart
docker-compose build
docker-compose up -d
```

## ✅ POST-DEPLOYMENT VERIFICATION

### Functional Tests:
1. **Citation Display**: Navigate to any term, verify citation appears in Term Information
2. **Version Switching**: Use dropdown to switch versions, confirm citation updates dynamically
3. **Admin Delete**: Login as admin (Username: "Wook"), verify delete buttons appear
4. **Delete Cascade**: Test deleting a term with versions and anchors
5. **Form Submission**: Create new term with citation, verify it saves correctly

### Database Checks:
```sql
-- Verify citation column exists
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'term_versions' 
AND column_name = 'source_citation';

-- Check for any citation data
SELECT id, anchor_term, source_citation 
FROM term_versions 
WHERE source_citation IS NOT NULL 
LIMIT 5;
```

## 🔍 MONITORING AFTER DEPLOYMENT

Watch for these potential issues:
- Foreign key constraint violations on delete operations
- JavaScript errors in browser console on term detail pages
- 500 errors when accessing /terms/ routes
- Database connection issues after migration

## 📝 ADDITIONAL NOTES

### Environment Variables
No new environment variables required. System uses existing configuration.

### Dependencies
All Python dependencies already installed. No new packages needed.

### Performance Impact
- Minimal impact expected
- Citation field is nullable and indexed
- JavaScript version switching is client-side only

### Security Considerations
- Delete functionality restricted to admin users only
- CSRF protection maintained on all forms
- Cascade deletion properly handles all foreign key relationships

## 🚦 DEPLOYMENT READINESS

**Status**: ✅ READY FOR PRODUCTION  
**Risk Level**: LOW (additive changes, backward compatible)  
**Estimated Deployment Time**: 10-15 minutes  
**Required Downtime**: 2-3 minutes (for database migration)  

## 📞 TROUBLESHOOTING

If issues arise:
1. Check Docker logs: `docker-compose logs web`
2. Verify database migration: Check if `source_citation` column exists
3. Test database connection from app container
4. Ensure proper file permissions on new/modified files
5. Check browser console for JavaScript errors on term pages

---

**Created**: August 24, 2025  
**Purpose**: Guide server-side Claude through OntExtract deployment  
**Priority**: Deploy when convenient, but backup database first!