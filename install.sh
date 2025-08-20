#!/bin/bash

# OntExtract Docker Installation Script
# This script sets up the complete OntExtract environment with Docker

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
echo "   OntExtract Installation Script"
echo "======================================"
echo ""

# Check for Docker
print_status "Checking for Docker..."
if ! command -v docker &> /dev/null; then
    print_error "Docker is not installed. Please install Docker first."
    echo "Visit: https://docs.docker.com/get-docker/"
    exit 1
fi

# Check for Docker Compose
print_status "Checking for Docker Compose..."
if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
    print_error "Docker Compose is not installed. Please install Docker Compose first."
    echo "Visit: https://docs.docker.com/compose/install/"
    exit 1
fi

# Check if .env exists
if [ ! -f .env ]; then
    print_warning ".env file not found."
    
    # Check if .env.production exists
    if [ -f .env.production ]; then
        print_status "Copying .env.production to .env..."
        cp .env.production .env
        print_warning "Please edit .env and add your API keys before continuing."
        echo "Press Enter when you've updated the .env file..."
        read
    else
        print_error "No .env or .env.production file found."
        echo "Please create a .env file with your configuration."
        echo "You can use .env.example as a template."
        exit 1
    fi
else
    print_status ".env file found."
fi

# Create necessary directories
print_status "Creating necessary directories..."
mkdir -p uploads logs ontology_cache

# Stop any existing containers
print_status "Stopping any existing containers..."
docker-compose down 2>/dev/null || true

# Build the Docker image
print_status "Building Docker image..."
docker-compose build

# Start the database first and wait for it to be ready
print_status "Starting database service..."
docker-compose up -d db

print_status "Waiting for database to be ready..."
sleep 5

# Check if database is ready
MAX_TRIES=30
TRIES=0
while ! docker-compose exec -T db pg_isready -U postgres > /dev/null 2>&1; do
    TRIES=$((TRIES+1))
    if [ $TRIES -gt $MAX_TRIES ]; then
        print_error "Database failed to start after $MAX_TRIES attempts."
        exit 1
    fi
    echo -n "."
    sleep 2
done
echo ""
print_status "Database is ready!"

# Initialize database
print_status "Initializing database..."
docker-compose up -d db_init
sleep 5

# Start the web application
print_status "Starting web application..."
docker-compose up -d web

# Wait for web application to be ready
print_status "Waiting for application to start..."
sleep 10

MAX_TRIES=30
TRIES=0
while ! curl -f http://localhost:8765/ > /dev/null 2>&1; do
    TRIES=$((TRIES+1))
    if [ $TRIES -gt $MAX_TRIES ]; then
        print_error "Application failed to start after $MAX_TRIES attempts."
        echo "Check logs with: docker-compose logs web"
        exit 1
    fi
    echo -n "."
    sleep 2
done
echo ""

# Success message
echo ""
echo "======================================"
echo -e "${GREEN}   Installation Complete!${NC}"
echo "======================================"
echo ""
print_status "OntExtract is now running!"
echo ""
echo "Access the application at: http://localhost:8765"
echo ""
echo "You can now:"
echo "  • Register a new account through the web interface"
echo "  • Or run the admin setup script if provided"
echo ""
echo "Useful commands:"
echo "  View logs:        docker-compose logs -f"
echo "  Stop services:    docker-compose stop"
echo "  Start services:   docker-compose start"
echo "  Update project:   ./update.sh"
echo ""
