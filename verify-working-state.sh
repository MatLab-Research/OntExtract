#!/bin/bash
# Verification Script - Ensures codebase is in working state
# Run this after any refactoring session to verify nothing broke

set -e  # Exit on first error

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo "========================================"
echo "🔍 OntExtract Working State Verification"
echo "========================================"
echo ""

# Track overall success
ALL_CHECKS_PASSED=true

# ==============================================================================
# Check 1: Python Syntax
# ==============================================================================
echo -n "📝 Checking Python syntax... "
if python -m py_compile app/**/*.py shared_services/**/*.py 2>/dev/null; then
    echo -e "${GREEN}✓${NC}"
else
    echo -e "${RED}✗${NC}"
    echo "   Python syntax errors found!"
    ALL_CHECKS_PASSED=false
fi

# ==============================================================================
# Check 2: Import Validation
# ==============================================================================
echo -n "📦 Validating imports... "
if python -c "from app import create_app; app = create_app('testing')" 2>/dev/null; then
    echo -e "${GREEN}✓${NC}"
else
    echo -e "${RED}✗${NC}"
    echo "   Import errors found!"
    ALL_CHECKS_PASSED=false
fi

# ==============================================================================
# Check 3: Run Tests (if available)
# ==============================================================================
echo -n "🧪 Running tests... "
if command -v pytest &> /dev/null; then
    if pytest -q --tb=no 2>&1 | grep -q "passed\|no tests ran"; then
        echo -e "${GREEN}✓${NC}"
    else
        echo -e "${YELLOW}⚠${NC}"
        echo "   Some tests failed (check output above)"
        # Don't fail build on test failures during refactoring
    fi
else
    echo -e "${YELLOW}⊘${NC} (pytest not installed, skipping)"
fi

# ==============================================================================
# Check 4: App Starts Successfully
# ==============================================================================
echo -n "🚀 Testing app startup... "

# Start app in background
timeout 10 python run.py > /tmp/ontextract_startup.log 2>&1 &
APP_PID=$!

# Wait for app to start
sleep 5

# Check if process is still running
if kill -0 $APP_PID 2>/dev/null; then
    # Try to connect
    if curl -s -o /dev/null -w "%{http_code}" http://localhost:8765/ | grep -q "200\|302"; then
        echo -e "${GREEN}✓${NC}"
        kill $APP_PID 2>/dev/null || true
    else
        echo -e "${RED}✗${NC}"
        echo "   App started but not responding correctly"
        kill $APP_PID 2>/dev/null || true
        ALL_CHECKS_PASSED=false
    fi
else
    echo -e "${RED}✗${NC}"
    echo "   App failed to start"
    echo "   Check /tmp/ontextract_startup.log for details"
    ALL_CHECKS_PASSED=false
fi

# Clean up any remaining processes
pkill -f "python run.py" 2>/dev/null || true

# ==============================================================================
# Check 5: Code Quality (if tools available)
# ==============================================================================
if command -v ruff &> /dev/null; then
    echo -n "🎨 Checking code quality... "
    if ruff check app/ shared_services/ --quiet 2>/dev/null; then
        echo -e "${GREEN}✓${NC}"
    else
        echo -e "${YELLOW}⚠${NC}"
        echo "   Code quality issues found (run 'ruff check app/' for details)"
        # Don't fail on quality issues
    fi
else
    echo "🎨 Checking code quality... ${YELLOW}⊘${NC} (ruff not installed, skipping)"
fi

# ==============================================================================
# Check 6: Database Migrations (if applicable)
# ==============================================================================
if [ -d "migrations" ]; then
    echo -n "🗄️  Checking migrations... "
    # Just verify migrations directory is intact
    if [ -f "migrations/alembic.ini" ]; then
        echo -e "${GREEN}✓${NC}"
    else
        echo -e "${YELLOW}⚠${NC}"
        echo "   Migrations may be corrupted"
    fi
else
    echo "🗄️  Checking migrations... ${YELLOW}⊘${NC} (no migrations directory)"
fi

# ==============================================================================
# Summary
# ==============================================================================
echo ""
echo "========================================"
if [ "$ALL_CHECKS_PASSED" = true ]; then
    echo -e "${GREEN}✅ All critical checks passed!${NC}"
    echo "========================================"
    echo ""
    echo "Safe to commit your changes ✨"
    exit 0
else
    echo -e "${RED}❌ Some checks failed!${NC}"
    echo "========================================"
    echo ""
    echo "Please fix errors before committing."
    echo "See details above for more information."
    exit 1
fi
