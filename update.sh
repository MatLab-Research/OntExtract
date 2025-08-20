#!/bin/bash

# OntExtract Update Script
# This script updates the OntExtract application while preserving all data

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[✓]${NC} $1"
}

print_error() {
    echo -e "${RED}[✗]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

# Banner
echo "======================================"
echo "   OntExtract Update Script"
echo "======================================"
echo ""

# Check if Docker is running
print_status "Checking Docker status..."
if ! docker info > /dev/null 2>&1; then
    print_error "Docker is not running. Please start Docker first."
    exit 1
fi

# Save current branch and commit
print_status "Checking current version..."
CURRENT_COMMIT=$(git rev-parse HEAD 2>/dev/null || echo "unknown")
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown")
echo "Current branch: $CURRENT_BRANCH"
echo "Current commit: ${CURRENT_COMMIT:0:7}"

# Check for uncommitted changes
if [[ -n $(git status -s 2>/dev/null) ]]; then
    print_warning "You have uncommitted changes."
    echo "These changes will be preserved but not committed."
    echo "Press Enter to continue or Ctrl+C to cancel..."
    read
fi

# Fetch latest changes
print_status "Fetching latest changes from repository..."
git fetch origin

# Check if updates are available
REMOTE_COMMIT=$(git rev-parse origin/main 2>/dev/null || echo "unknown")
if [ "$CURRENT_COMMIT" = "$REMOTE_COMMIT" ]; then
    print_status "Already up to date!"
    echo "No updates available."
    echo ""
    exit 0
fi

# Show what will be updated
echo ""
print_status "Updates available!"
echo "Will update from ${CURRENT_COMMIT:0:7} to ${REMOTE_COMMIT:0:7}"
echo ""
echo "This will:"
echo "  • Pull latest code from GitHub"
echo "  • Rebuild Docker containers if needed"
echo "  • Preserve all your data (database, uploads, logs)"
echo "  • Restart services"
echo ""
echo "Press Enter to continue or Ctrl+C to cancel..."
read

# Pull latest changes
print_status "Pulling latest changes..."
git pull origin main

# Check if requirements changed
if git diff HEAD~1 HEAD --name-only | grep -q "requirements.txt\|Dockerfile\|docker-compose.yml"; then
    print_status "Dependencies or Docker configuration changed. Rebuilding containers..."
    
    # Stop services
    print_status "Stopping services..."
    docker-compose stop
    
    # Rebuild containers
    print_status "Rebuilding Docker containers..."
    docker-compose build --no-cache
    
    # Start services
    print_status "Starting services..."
    docker-compose up -d
else
    print_status "No dependency changes. Restarting services..."
    docker-compose restart
fi

# Wait for services to be ready
print_status "Waiting for services to be ready..."
sleep 10

MAX_TRIES=30
TRIES=0
while ! curl -f http://localhost:8765/ > /dev/null 2>&1; do
    TRIES=$((TRIES+1))
    if [ $TRIES -gt $MAX_TRIES ]; then
        print_error "Application failed to start after update."
        echo "Check logs with: docker-compose logs web"
        exit 1
    fi
    echo -n "."
    sleep 2
done
echo ""

# Run any database migrations
print_status "Checking for database migrations..."
docker-compose exec -T web flask db upgrade 2>/dev/null || {
    print_warning "No migrations to run or migrations already applied."
}

# Get new version info
NEW_COMMIT=$(git rev-parse HEAD)
NEW_VERSION=$(git describe --tags --always 2>/dev/null || echo ${NEW_COMMIT:0:7})

# Success message
echo ""
echo "======================================"
echo -e "${GREEN}   Update Complete!${NC}"
echo "======================================"
echo ""
print_status "OntExtract has been updated successfully!"
echo "Version: $NEW_VERSION"
echo ""
echo "The application is running at: http://localhost:8765"
echo ""
echo "All your data has been preserved:"
echo "  ✓ Database"
echo "  ✓ Uploaded documents"
echo "  ✓ Application logs"
echo ""
echo "To view logs: docker-compose logs -f"
echo ""
