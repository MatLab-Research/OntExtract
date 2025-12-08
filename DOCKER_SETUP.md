# OntExtract - Docker Setup

Quick start guide for running OntExtract using Docker Compose.

## Prerequisites

- Docker Engine 20.10+
- Docker Compose 2.0+
- 4GB RAM minimum
- 15GB free disk space (includes pre-downloaded ML models)

**For Windows Users**: Docker Desktop with WSL2 integration enabled
- Open Docker Desktop → Settings → Resources → WSL Integration
- Enable integration for your WSL2 distribution

**For Linux Users**: Docker Engine + Docker Compose plugin
**For macOS Users**: Docker Desktop

## Quick Start

### 1. Clone and Navigate
```bash
cd OntExtract
```

### 2. (Optional) Configure Environment

For LLM orchestration features and custom admin credentials, create `.env.local`:
```bash
cp .env.docker .env.local
nano .env.local
```

Add your settings:
```bash
# Optional: API key for LLM features
ANTHROPIC_API_KEY=sk-ant-your-key-here

# Optional: Custom admin credentials (defaults shown)
CREATE_DEFAULT_ADMIN=true
ADMIN_USERNAME=admin
ADMIN_PASSWORD=admin123
ADMIN_EMAIL=admin@ontextract.local
```

Or set environment variables inline:
```bash
export ANTHROPIC_API_KEY=sk-ant-your-key-here
export ADMIN_PASSWORD=mysecurepassword
```

### 3. Start All Services
```bash
docker-compose up -d
```

This will:
- Pull required images (PostgreSQL, Redis)
- Build the OntExtract application
- Start all services (web, database, redis, celery)
- Initialize the database

### 4. Access the Application
- **Web Interface**: http://localhost:8765
- **Default Admin Login**: `admin` / `admin123` (change in production!)
- **PostgreSQL**: localhost:5433 (user: postgres, password: ontextract_dev_password)
- **Redis**: localhost:6380

**Note**: A default admin account is automatically created on first startup. Change the password immediately in production!

### 5. View Logs
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f web
docker-compose logs -f celery
```

### 6. Stop Services
```bash
# Stop but keep data
docker-compose stop

# Stop and remove containers (keeps data volumes)
docker-compose down

# Stop and remove everything including data
docker-compose down -v
```

---

## Operational Modes

### Standalone Mode (No API Key)
Simply start the services without setting `ANTHROPIC_API_KEY`. The system will run with manual tool selection and local NLP libraries.

### API-Enhanced Mode (With API Key)
Set your Anthropic API key to enable:
- LLM-powered tool recommendations
- Automated document analysis
- Cross-document synthesis
- Enhanced context extraction

---

## Development Usage

### Rebuilding After Code Changes
```bash
docker-compose up -d --build
```

### Accessing the Database
```bash
docker-compose exec postgres psql -U postgres -d ontextract_db
```

### Running Tests
```bash
docker-compose exec web pytest
```

### Accessing Container Shell
```bash
docker-compose exec web bash
```

### Creating Additional Admin Users
```bash
# Interactive mode
docker-compose exec web python init_admin.py

# Or with environment variables
docker-compose exec web bash -c "ADMIN_USERNAME=newadmin ADMIN_PASSWORD=newpass ADMIN_EMAIL=new@example.com python init_admin.py"
```

### Checking Service Health
```bash
docker-compose ps
```

---

## Troubleshooting

### Port Already in Use
If ports 8765, 5433, or 6380 are already in use:

1. Stop conflicting services:
   ```bash
   sudo systemctl stop postgresql redis-server
   ```

2. Or modify ports in `docker-compose.yml`:
   ```yaml
   ports:
     - "8766:8765"  # Use different host port
   ```

### Container Won't Start
```bash
# View detailed logs
docker-compose logs web

# Check container status
docker-compose ps

# Restart specific service
docker-compose restart web
```

### Database Connection Issues
```bash
# Wait for PostgreSQL to be ready
docker-compose exec postgres pg_isready -U postgres

# Manually initialize database
docker-compose exec web flask db upgrade
```

### Permission Issues with Uploads
```bash
# Fix volume permissions
docker-compose exec web chown -R root:root /app/uploads /app/logs
```

---

## Production Deployment

For production use:

1. **Update secrets** in `docker-compose.yml`:
   - Change `SECRET_KEY`
   - Change database password
   - Use environment variables instead of hardcoded values

2. **Use production-ready settings**:
   ```yaml
   environment:
     - FLASK_ENV=production
     - FLASK_DEBUG=0
   ```

3. **Add reverse proxy** (nginx/traefik) for HTTPS

4. **Enable backups**:
   ```bash
   docker-compose exec postgres pg_dump -U postgres ontextract_db > backup.sql
   ```

5. **Use external volumes** for persistent data

---

## Resource Requirements

### Minimum
- **CPU**: 2 cores
- **RAM**: 4GB
- **Disk**: 15GB

### Recommended
- **CPU**: 4+ cores
- **RAM**: 8GB+
- **Disk**: 25GB+

### Pre-downloaded Models

The Docker image includes pre-downloaded ML models to avoid first-run delays:

| Model | Size | Purpose |
|-------|------|---------|
| `en_core_web_sm` (spaCy) | ~12MB | Sentence segmentation, NER |
| `facebook/bart-large-mnli` | ~1.6GB | Zero-shot classification (disabled by default) |

These models are downloaded during image build, not at runtime.

**Note**: Zero-shot classification for definition extraction is disabled by default due to CPU performance. Definition extraction uses pattern matching instead. Enable with `ENABLE_ZERO_SHOT_DEFINITIONS=true` if you have GPU acceleration.

---

## Architecture

```
┌─────────────────────────────────────────┐
│         docker-compose.yml              │
├─────────────────────────────────────────┤
│                                         │
│  ┌──────────┐  ┌──────────┐           │
│  │   Web    │  │  Celery  │           │
│  │ (Flask)  │  │ (Worker) │           │
│  └────┬─────┘  └────┬─────┘           │
│       │             │                  │
│  ┌────┴─────────────┴─────┐           │
│  │                          │           │
│  │  ┌──────────┐  ┌──────┐ │           │
│  │  │PostgreSQL│  │Redis │ │           │
│  │  └──────────┘  └──────┘ │           │
│  │                          │           │
│  └──────────────────────────┘           │
│                                         │
└─────────────────────────────────────────┘
```

---

## Manual Installation (Alternative)

If you cannot use Docker, you can install manually:

### Prerequisites
```bash
# Install system dependencies (Ubuntu/Debian)
sudo apt-get update
sudo apt-get install -y postgresql-14 redis-server python3.12 python3.12-venv

# Install pgvector extension
sudo apt-get install -y postgresql-14-pgvector
```

### Setup
```bash
# Create and activate virtual environment
python3.12 -m venv venv
source venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt
python -m spacy download en_core_web_sm

# Optional: Download BART model for zero-shot classification (~1.6GB)
# Only needed if you enable ENABLE_ZERO_SHOT_DEFINITIONS=true
# python -c "from transformers import pipeline; pipeline('zero-shot-classification', model='facebook/bart-large-mnli')"

# Configure PostgreSQL
sudo -u postgres psql -c "CREATE DATABASE ontextract_db;"
sudo -u postgres psql -d ontextract_db -c "CREATE EXTENSION vector;"

# Configure environment
cp .env.example .env
# Edit .env with your database credentials and settings

# Initialize database
flask db upgrade

# Seed default templates and settings
flask seed-defaults

# Create admin user (optional)
python init_admin.py
```

### Run Services
```bash
# Terminal 1: Start Redis (if not running as service)
redis-server

# Terminal 2: Start Celery worker
celery -A celery_config.celery worker --loglevel=info

# Terminal 3: Start Flask application
python run.py
```

Access at http://localhost:8765

**Note**: Manual installation requires more configuration and troubleshooting. Docker is strongly recommended for most users.

---

## Next Steps

After starting the services:

1. Open http://localhost:8765
2. Create an account or use default admin (Docker: `admin` / `admin123`)
3. Create a new experiment
4. Upload documents
5. Run analysis workflows

For detailed usage instructions, see the main [README.md](README.md).
