#!/bin/bash
# Setup pgvector extension for local PostgreSQL installation
# Run this script to enable pgvector on your manual dev setup

set -e

echo "=========================================="
echo "Setting up pgvector for OntExtract"
echo "=========================================="

# Check if PostgreSQL is running
if ! pg_isready > /dev/null 2>&1; then
    echo "❌ PostgreSQL is not running. Please start it first:"
    echo "   sudo systemctl start postgresql"
    exit 1
fi

echo "✓ PostgreSQL is running"

# Check PostgreSQL version
PG_VERSION=$(psql --version | grep -oP '\d+' | head -1)
echo "PostgreSQL version: $PG_VERSION"

# Check if pgvector is already installed
if psql -U postgres -d ontextract_db -c "SELECT extname FROM pg_extension WHERE extname = 'vector';" 2>/dev/null | grep -q vector; then
    echo "✓ pgvector extension is already installed and enabled"
    exit 0
fi

echo ""
echo "Installing pgvector extension..."
echo ""

# Instructions for different systems
echo "================================================"
echo "pgvector Installation Instructions"
echo "================================================"
echo ""
echo "For Ubuntu/Debian:"
echo "  sudo apt install postgresql-$PG_VERSION-pgvector"
echo ""
echo "For other systems, see: https://github.com/pgvector/pgvector#installation"
echo ""
echo "After installing, run this script again to enable the extension."
echo ""

# Try to install if on Ubuntu/Debian
if command -v apt-get > /dev/null; then
    echo "Attempting to install postgresql-$PG_VERSION-pgvector..."
    sudo apt-get update
    sudo apt-get install -y postgresql-$PG_VERSION-pgvector

    echo ""
    echo "Enabling pgvector extension in ontextract_db..."

    # Enable extension
    sudo -u postgres psql -d ontextract_db -c "CREATE EXTENSION IF NOT EXISTS vector;"

    # Verify
    if sudo -u postgres psql -d ontextract_db -c "SELECT extname, extversion FROM pg_extension WHERE extname = 'vector';" | grep -q vector; then
        echo "✓ pgvector extension enabled successfully!"
    else
        echo "❌ Failed to enable pgvector extension"
        exit 1
    fi
else
    echo "Not on Ubuntu/Debian. Please install pgvector manually and run this script again."
    exit 1
fi

echo ""
echo "=========================================="
echo "pgvector setup complete!"
echo "=========================================="
