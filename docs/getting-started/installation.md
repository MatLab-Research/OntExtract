# Installation

This guide covers installing OntExtract on your local machine.

## Quick Start Options

| Method | Best For | Time |
|--------|----------|------|
| **Live Demo** | Trying it out without installation | Instant |
| **Docker** | Local development, most users | 5 minutes |
| **Manual** | Contributors, custom deployments | 30+ minutes |

## Option 1: Live Demo

Access the live system at **https://ontextract.ontorealm.net**

- Demo credentials: `demo` / `demo123`
- Pre-loaded experiment with sample documents
- No installation required

## Option 2: Docker (Recommended)

Docker provides the fastest path to a working local installation.

### Prerequisites

- Docker Engine 20.10+
- Docker Compose 2.0+
- 4GB RAM minimum
- 10GB free disk space

**Windows**: Docker Desktop with WSL2 integration enabled

**macOS**: Docker Desktop

**Linux**: Docker Engine + Docker Compose plugin

### Quick Start

```bash
cd OntExtract
docker-compose up -d
```

This starts all services:
- Web application on http://localhost:8765
- PostgreSQL database
- Redis cache
- Celery background workers

### Default Login

- **Username**: `admin`
- **Password**: `admin123`

Change the password after first login in production!

### Enable LLM Features (Optional)

For AI-assisted orchestration, create `.env.local`:

```bash
cp .env.docker .env.local
```

Add your API key:

```bash
ANTHROPIC_API_KEY=sk-ant-your-key-here
```

Restart services:

```bash
docker-compose up -d
```

### Common Commands

```bash
# View logs
docker-compose logs -f

# Stop services (keeps data)
docker-compose stop

# Stop and remove containers (keeps data volumes)
docker-compose down

# Stop and remove everything including data
docker-compose down -v

# Rebuild after code changes
docker-compose up -d --build
```

### Troubleshooting Docker

**Port already in use**:
```bash
# Stop conflicting local services
sudo systemctl stop postgresql redis-server
```

**Container won't start**:
```bash
docker-compose logs web
docker-compose restart web
```

**Database connection issues**:
```bash
docker-compose exec postgres pg_isready -U postgres
docker-compose exec web flask db upgrade
```

## Option 3: Manual Installation

For advanced users who need to modify the code or can't use Docker.

### System Requirements

- Python 3.12+
- PostgreSQL 14+ with pgvector extension
- Redis 6+
- 2GB RAM minimum

### Ubuntu/Debian Setup

```bash
# Install system dependencies
sudo apt-get update
sudo apt-get install -y postgresql-14 postgresql-14-pgvector redis-server python3.12 python3.12-venv

# Create database
sudo -u postgres psql -c "CREATE DATABASE ontextract_db;"
sudo -u postgres psql -d ontextract_db -c "CREATE EXTENSION vector;"
```

### Python Environment

```bash
# Create virtual environment
python3.12 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
python -m spacy download en_core_web_sm
```

### Configuration

```bash
# Copy environment template
cp .env.example .env

# Edit with your settings
nano .env
```

Key settings in `.env`:

```bash
DATABASE_URL=postgresql://postgres:password@localhost:5432/ontextract_db
REDIS_URL=redis://localhost:6379/0
SECRET_KEY=your-secret-key-here
ANTHROPIC_API_KEY=sk-ant-your-key-here  # Optional
```

### Initialize Database

```bash
flask db upgrade
flask seed-defaults   # Seed prompt templates and settings
python init_admin.py  # Create admin user
```

### Start Services

You need three terminal sessions:

```bash
# Terminal 1: Redis (if not running as service)
redis-server

# Terminal 2: Celery worker
celery -A celery_config.celery worker --loglevel=info

# Terminal 3: Flask application
python run.py
```

Access at http://localhost:8765

## Resource Requirements

### Minimum

- **CPU**: 2 cores
- **RAM**: 4GB
- **Disk**: 10GB

### Recommended

- **CPU**: 4+ cores
- **RAM**: 8GB+
- **Disk**: 20GB+

## Next Steps

After installation:

1. [First Login](first-login.md) - Create your account and explore the interface
2. [Create Anchor Terms](../how-to/create-anchor-terms.md) - Define concepts to track
3. [Upload Documents](../how-to/upload-documents.md) - Add your source materials
4. [Create Experiment](../how-to/create-temporal-experiment.md) - Set up your first analysis
