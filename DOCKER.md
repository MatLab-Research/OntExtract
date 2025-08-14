# OntExtract Docker Setup

This document describes how to run OntExtract using Docker containers.

## Architecture

The Docker setup consists of two services:
- **PostgreSQL Database** (`db`): PostgreSQL 15 with pgvector extension
- **Flask Application** (`web`): OntExtract web application

## Prerequisites

- Docker 
- Docker Compose
- Git (for git update functionality)

## Quick Start

### Development Mode (Recommended for Prototyping)
```bash
# Build and start services with live code reloading
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up --build

# Access the application at http://localhost:5000
```

### Production Mode
```bash
# Build and start services
docker-compose up --build -d

# Access the application at http://localhost:5000
```

## Configuration

### Environment Variables

**Production (docker-compose.yml):**
- `CHECK_GIT_UPDATES=true` - Enable git repository checking on startup
- `GIT_BRANCH=main` - Target branch for updates
- `FLASK_ENV=production` - Production mode
- `DEBUG=False` - Disable debug mode

**Development (docker-compose.dev.yml):**
- `CHECK_GIT_UPDATES=false` - Disable git checking (uses volume mount)
- `FLASK_ENV=development` - Development mode
- `DEBUG=True` - Enable debug mode

### Git Update Functionality

In production mode, the container can check for repository updates on startup:

1. **Enabled by default** in production mode
2. **Disabled by default** in development mode (uses volume mounting)
3. Configurable via `CHECK_GIT_UPDATES` environment variable
4. Pulls from the specified `GIT_BRANCH` (default: main)
5. Reinstalls dependencies if `requirements.txt` changes

## Commands

### Build and Start
```bash
# Development with live reloading
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up --build

# Production mode
docker-compose up --build -d

# Force rebuild
docker-compose build --no-cache
```

### Management
```bash
# View logs
docker-compose logs -f web
docker-compose logs -f db

# Stop services
docker-compose down

# Stop and remove volumes (WARNING: destroys data)
docker-compose down -v

# Access application container
docker-compose exec web bash

# Access database
docker-compose exec db psql -U postgres -d ontextract_db
```

### Database Operations
```bash
# Initialize database (done automatically on startup)
docker-compose exec web flask init-db

# Create admin user
docker-compose exec web flask create-admin

# Backup database
docker-compose exec db pg_dump -U postgres ontextract_db > backup.sql

# Restore database
docker-compose exec -T db psql -U postgres ontextract_db < backup.sql
```

## File Structure

```
├── Dockerfile                 # Main application container
├── docker-compose.yml         # Production configuration
├── docker-compose.dev.yml     # Development overrides
├── .dockerignore              # Docker build exclusions
└── scripts/
    ├── startup.sh             # Application startup script
    └── init-db.sql            # Database initialization
```

## Volumes

- `postgres_data`: Database files (persistent)
- `uploads_data`: User uploaded files (persistent)
- `logs_data`: Application logs (persistent)

In development mode, the entire source code is mounted as a volume for live reloading.

## Ports

- **5000**: Flask application (web interface)
- **5434**: PostgreSQL database (external access)

## Networking

Services communicate via the `ontextract_network` bridge network:
- Database hostname: `db`
- Web application hostname: `web`

## Health Checks

Both services include health checks:
- **Database**: PostgreSQL ready check
- **Web App**: HTTP endpoint availability

## Troubleshooting

### Common Issues

1. **Port conflicts**: Change ports in docker-compose.yml if 5000 or 5434 are in use
2. **Permission errors**: Ensure Docker daemon is running and user has permissions
3. **Build failures**: Check Docker logs and ensure all dependencies are available

### Debugging

```bash
# View container logs
docker-compose logs web
docker-compose logs db

# Access container shell
docker-compose exec web bash

# Check database connection
docker-compose exec web python -c "from app import db; print(db.engine.execute('SELECT 1').scalar())"

# Check git status (production mode)
docker-compose exec web git status
```

### Development vs Production

**Development Mode:**
- Code changes reflected immediately (volume mount)
- Flask development server with auto-reload
- Debug mode enabled
- Git updates disabled

**Production Mode:**
- Code baked into container image
- Gunicorn WSGI server (if available)
- Git updates enabled
- Security hardened

## Security Considerations

- Change default database password in production
- Use environment-specific secret keys
- Consider using Docker secrets for sensitive data
- Run containers as non-root user (implemented)

## Next Steps

1. Configure environment-specific variables
2. Set up SSL/TLS for production
3. Implement backup strategies
4. Configure log aggregation
5. Set up monitoring and alerts
