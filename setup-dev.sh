#!/bin/bash
# OntExtract Development Environment Setup Script

set -e  # Exit on error

echo "========================================"
echo "OntExtract Development Setup"
echo "========================================"
echo ""

# Check Python version
echo "Checking Python version..."
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
REQUIRED_VERSION="3.11"

if ! python3 -c "import sys; exit(0 if sys.version_info >= (3, 11) else 1)"; then
    echo "❌ Error: Python 3.11+ required. Found: $PYTHON_VERSION"
    exit 1
fi
echo "✅ Python $PYTHON_VERSION detected"
echo ""

# Create virtual environment
echo "Creating virtual environment..."
if [ ! -d ".venv" ]; then
    python3 -m venv .venv
    echo "✅ Virtual environment created"
else
    echo "✅ Virtual environment already exists"
fi
echo ""

# Activate virtual environment
echo "Activating virtual environment..."
source .venv/bin/activate
echo "✅ Virtual environment activated"
echo ""

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip wheel setuptools
echo ""

# Install production dependencies
echo "Installing production dependencies..."
pip install -r requirements.txt
echo "✅ Production dependencies installed"
echo ""

# Install development dependencies
echo "Installing development dependencies..."
pip install -r requirements-dev.txt
echo "✅ Development dependencies installed"
echo ""

# Install pre-commit hooks
echo "Setting up pre-commit hooks..."
pre-commit install
echo "✅ Pre-commit hooks installed"
echo ""

# Create necessary directories
echo "Creating necessary directories..."
mkdir -p uploads logs data ontology_cache
echo "✅ Directories created"
echo ""

# Check for .env file
echo "Checking environment configuration..."
if [ ! -f ".env" ]; then
    echo "⚠️  Warning: .env file not found"
    echo "   Please create .env file with required configuration"
    echo "   See CONTRIBUTING.md for details"
else
    echo "✅ .env file found"
fi
echo ""

# Database setup instructions
echo "========================================"
echo "Next Steps:"
echo "========================================"
echo ""
echo "1. Configure your .env file with:"
echo "   - DATABASE_URL (PostgreSQL with pgvector)"
echo "   - REDIS_URL"
echo "   - API keys (ANTHROPIC_API_KEY, etc.)"
echo ""
echo "2. Initialize the database:"
echo "   flask db upgrade"
echo "   flask init-db"
echo ""
echo "3. Create an admin user:"
echo "   flask create-admin"
echo ""
echo "4. Run the development server:"
echo "   python run.py"
echo ""
echo "5. Run tests:"
echo "   pytest"
echo ""
echo "6. Run code quality checks:"
echo "   ruff check ."
echo "   mypy app/"
echo "   pre-commit run --all-files"
echo ""
echo "========================================"
echo "Setup Complete! 🎉"
echo "========================================"
echo ""
echo "For more information, see CONTRIBUTING.md"
