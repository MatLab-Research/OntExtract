#!/bin/bash
# OntExtract Production Deployment Script
# Run this script on the production server (DigitalOcean)
# Usage: ./scripts/deploy_production.sh [--skip-db] [--skip-restart]

set -e  # Exit on error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Parse arguments
SKIP_DB=false
SKIP_RESTART=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --skip-db)
            SKIP_DB=true
            shift
            ;;
        --skip-restart)
            SKIP_RESTART=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [--skip-db] [--skip-restart]"
            exit 1
            ;;
    esac
done

echo -e "${GREEN}=== OntExtract Production Deployment ===${NC}"
echo "Project directory: $PROJECT_DIR"
echo ""

# Step 1: Git pull
echo -e "${YELLOW}[1/5] Pulling latest code from GitHub...${NC}"
git fetch origin
git pull origin main

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Code updated successfully${NC}"
else
    echo -e "${RED}✗ Git pull failed${NC}"
    exit 1
fi
echo ""

# Step 2: Update dependencies
echo -e "${YELLOW}[2/5] Checking dependencies...${NC}"
if [ -f "requirements.txt" ]; then
    source venv/bin/activate

    # Check if requirements have changed
    pip list --format=freeze > /tmp/current_packages.txt
    if ! cmp -s requirements.txt /tmp/current_packages.txt > /dev/null 2>&1; then
        echo "Installing updated dependencies..."
        pip install -r requirements.txt
        echo -e "${GREEN}✓ Dependencies updated${NC}"
    else
        echo -e "${GREEN}✓ Dependencies are up to date${NC}"
    fi

    deactivate
else
    echo -e "${YELLOW}! No requirements.txt found, skipping dependency update${NC}"
fi
echo ""

# Step 3: Database updates
if [ "$SKIP_DB" = false ]; then
    echo -e "${YELLOW}[3/5] Applying database updates...${NC}"

    # Check if we need to apply FK constraint fix
    echo "Checking FK constraint on processing_artifact_groups..."
    FK_CHECK=$(sudo -u postgres psql -d ontextract_db -t -c "
        SELECT confdeltype
        FROM pg_constraint
        WHERE conrelid = 'processing_artifact_groups'::regclass
          AND confrelid = 'documents'::regclass
          AND conname = 'processing_artifact_groups_document_id_fkey';
    " 2>/dev/null | tr -d ' \n')

    if [ "$FK_CHECK" != "c" ]; then
        echo "Applying FK constraint CASCADE fix..."
        sudo -u postgres psql -d ontextract_db -c "
            ALTER TABLE processing_artifact_groups
            DROP CONSTRAINT IF EXISTS processing_artifact_groups_document_id_fkey,
            ADD CONSTRAINT processing_artifact_groups_document_id_fkey
            FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE;
        " > /dev/null 2>&1

        if [ $? -eq 0 ]; then
            echo -e "${GREEN}✓ FK constraint updated to CASCADE${NC}"
        else
            echo -e "${RED}✗ Failed to update FK constraint${NC}"
        fi
    else
        echo -e "${GREEN}✓ FK constraint already set to CASCADE${NC}"
    fi

    # Run any pending migrations
    if [ -d "migrations" ]; then
        echo "Checking for database migrations..."
        source venv/bin/activate
        flask db upgrade 2>&1 | grep -v "INFO" || echo -e "${GREEN}✓ Database is up to date${NC}"
        deactivate
    fi
else
    echo -e "${YELLOW}[3/5] Skipping database updates (--skip-db)${NC}"
fi
echo ""

# Step 4: Restart services
if [ "$SKIP_RESTART" = false ]; then
    echo -e "${YELLOW}[4/5] Restarting services...${NC}"

    echo "Restarting OntExtract Flask service..."
    sudo systemctl restart ontextract
    sleep 2

    if sudo systemctl is-active --quiet ontextract; then
        echo -e "${GREEN}✓ OntExtract service restarted${NC}"
    else
        echo -e "${RED}✗ OntExtract service failed to start${NC}"
        sudo systemctl status ontextract --no-pager -l
        exit 1
    fi

    echo "Restarting Celery worker..."
    sudo systemctl restart celery-ontextract
    sleep 2

    if sudo systemctl is-active --quiet celery-ontextract; then
        echo -e "${GREEN}✓ Celery worker restarted${NC}"
    else
        echo -e "${RED}✗ Celery worker failed to start${NC}"
        sudo systemctl status celery-ontextract --no-pager -l
        exit 1
    fi
else
    echo -e "${YELLOW}[4/5] Skipping service restart (--skip-restart)${NC}"
fi
echo ""

# Step 5: Verification
echo -e "${YELLOW}[5/5] Verifying deployment...${NC}"

# Check Flask service
if sudo systemctl is-active --quiet ontextract; then
    echo -e "${GREEN}✓ OntExtract service: Running${NC}"
else
    echo -e "${RED}✗ OntExtract service: Not running${NC}"
fi

# Check Celery service
if sudo systemctl is-active --quiet celery-ontextract; then
    echo -e "${GREEN}✓ Celery worker: Running${NC}"
else
    echo -e "${RED}✗ Celery worker: Not running${NC}"
fi

# Check Redis
if sudo systemctl is-active --quiet redis; then
    echo -e "${GREEN}✓ Redis: Running${NC}"
else
    echo -e "${YELLOW}! Redis: Not running (may affect background tasks)${NC}"
fi

# Check Nginx
if sudo systemctl is-active --quiet nginx; then
    echo -e "${GREEN}✓ Nginx: Running${NC}"
else
    echo -e "${YELLOW}! Nginx: Not running (may affect web access)${NC}"
fi

# Test HTTP endpoint
echo ""
echo "Testing HTTP endpoint..."
HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8080 2>/dev/null || echo "000")

if [ "$HTTP_STATUS" = "200" ] || [ "$HTTP_STATUS" = "302" ]; then
    echo -e "${GREEN}✓ Application responding (HTTP $HTTP_STATUS)${NC}"
else
    echo -e "${RED}✗ Application not responding (HTTP $HTTP_STATUS)${NC}"
fi

echo ""
echo -e "${GREEN}=== Deployment Complete ===${NC}"
echo ""
echo "Service Status:"
echo "  Flask:  sudo systemctl status ontextract"
echo "  Celery: sudo systemctl status celery-ontextract"
echo ""
echo "View Logs:"
echo "  Flask:  sudo journalctl -u ontextract -n 50 --follow"
echo "  Celery: sudo journalctl -u celery-ontextract -n 50 --follow"
echo ""
echo "Public URL: https://ontextract.ontorealm.net"
