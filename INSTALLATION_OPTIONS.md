# OntExtract Installation Options Comparison

## For JCDL Demo Attendees

Quick decision guide for trying OntExtract locally.

---

## Option 1: Live Demo (Recommended for Quick Start)

**Best for**: Conference attendees who want to see the system immediately

✅ **Pros:**
- Zero installation
- Works on any device with a browser
- Pre-loaded demo data
- No API key needed to explore features

❌ **Cons:**
- Shared environment
- Demo account limitations
- Can't upload custom documents
- Internet connection required

**Setup Time**: 0 minutes

**Instructions**:
1. Go to https://ontextract.ontorealm.net
2. Login with `demo` / `demo123`
3. Explore pre-loaded experiment

---

## Option 2: Docker Compose (Recommended for Local Setup)

**Best for**: Researchers who want to try it locally with their own data

✅ **Pros:**
- One-command setup: `docker-compose up -d`
- Complete isolation (no system dependencies)
- Identical to production environment
- Easy cleanup: `docker-compose down`
- Works on Windows/Mac/Linux
- Can use your own API key

❌ **Cons:**
- Requires Docker installation (~500MB)
- Initial image build takes 5-10 minutes
- Uses 2-3GB RAM when running

**Prerequisites:**
- Docker Desktop (or Docker Engine + Docker Compose)
- 4GB RAM
- 10GB disk space

**Setup Time**: ~10 minutes (first time)

**Instructions**:
```bash
cd OntExtract

# Optional: add API key for LLM features
cp .env.docker .env.local
nano .env.local  # Add ANTHROPIC_API_KEY

# Start everything
docker-compose up -d

# Access at http://localhost:8765

# Stop when done
docker-compose down
```

**See**: [DOCKER_SETUP.md](DOCKER_SETUP.md) for full details

---

## Option 3: Manual Installation

**Best for**: Developers who want to modify code or avoid Docker

✅ **Pros:**
- Full control over environment
- No Docker overhead
- Can debug and modify code
- Best for development work

❌ **Cons:**
- Complex setup (PostgreSQL, Redis, Python)
- Platform-specific issues
- System-wide dependencies
- Harder to clean up

**Prerequisites:**
- Python 3.12+
- PostgreSQL 14+
- Redis 6+
- 4GB RAM
- Linux/Mac (WSL2 for Windows)

**Setup Time**: ~30-45 minutes

**Instructions**: See [DOCKER_SETUP.md](DOCKER_SETUP.md) or [docs-internal/SETUP_SECONDARY_DEV.md](docs-internal/SETUP_SECONDARY_DEV.md) for advanced manual setup

---

## Recommendations by Use Case

### "I want to see what OntExtract does"
→ **Option 1: Live Demo**

### "I want to try it with my own documents"
→ **Option 2: Docker** (easiest local setup)

### "I want to run it without internet/cloud"
→ **Option 2: Docker** (fully self-contained)

### "I want to develop or contribute code"
→ **Option 3: Manual** (best for development)

### "I'm at a conference with unreliable WiFi"
→ **Option 2: Docker** (pre-download, then offline)

---

## Quick Docker Command Reference

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down

# Rebuild after updates
docker-compose up -d --build

# Access database
docker-compose exec postgres psql -U postgres -d ontextract_db

# Check status
docker-compose ps
```

---

## What You Get

All options include:

**Core Features** (no API key needed):
- Manual document processing
- Named entity recognition
- Temporal expression extraction
- Text segmentation
- Embedding generation
- Definition extraction
- Sentiment analysis
- PROV-O provenance tracking

**LLM Features** (requires ANTHROPIC_API_KEY):
- Automated tool selection
- Cross-document synthesis
- LLM-generated insights
- Enhanced context extraction

---

## Resource Usage Comparison

| Option | Disk Space | RAM Usage | CPU Load |
|--------|------------|-----------|----------|
| Live Demo | 0 MB | 0 MB | None |
| Docker | ~3 GB | ~2 GB | Light |
| Manual | ~2 GB | ~1 GB | Light |

---

## Troubleshooting Quick Links

**Docker issues**: See [DOCKER_SETUP.md](DOCKER_SETUP.md#troubleshooting)

**Manual setup issues**: See [DOCKER_SETUP.md](DOCKER_SETUP.md#troubleshooting)

**General questions**: Open an issue on GitHub or email the authors

---

## After Installation

1. Create a user account
2. Create a new experiment
3. Upload some documents (PDF, DOCX, TXT)
4. Run document processing
5. Explore provenance graphs

**Example datasets** available in the demo account for reference.
