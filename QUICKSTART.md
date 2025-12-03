# OntExtract - Quick Start

Get OntExtract running in 5 minutes.

---

## Choose Your Path

### 🌐 Just Want to Try It? → [Live Demo](https://ontextract.ontorealm.net)
No installation needed. Login with `demo` / `demo123`

### 🐳 Want to Run Locally? → Docker (Recommended)

```bash
# 1. Make sure Docker is installed
docker --version

# 2. Clone/navigate to OntExtract
cd OntExtract

# 3. (Optional) Add API key for LLM features
echo "ANTHROPIC_API_KEY=your-key-here" > .env.local

# 4. Start everything
docker-compose up -d

# 5. Open browser and login
# http://localhost:8765
# Login: admin / admin123
```

**First time setup creates a default admin account automatically!**

See [DOCKER_SETUP.md](DOCKER_SETUP.md) for more details and customization options.

### 🛠️ Want Full Control? → Manual Install
See [DOCKER_SETUP.md](DOCKER_SETUP.md) for complete installation instructions.

For advanced manual setup, see [docs-internal/SETUP_SECONDARY_DEV.md](docs-internal/SETUP_SECONDARY_DEV.md).

---

## Not Sure Which Option?

See [INSTALLATION_OPTIONS.md](INSTALLATION_OPTIONS.md) for a detailed comparison.

---

## After Installation

1. **Login**
   - Docker: `admin` / `admin123` (created automatically)
   - Live demo: `demo` / `demo123`
   - Or register a new account
2. **Create an experiment**
   - Navigate to "Experiments" → "New Experiment"
   - Give it a name and description
3. **Upload documents**
   - Supports: PDF, DOCX, TXT, HTML, Markdown
4. **Run processing**
   - Select tools manually, or
   - Use LLM orchestration (requires API key)
5. **Explore results**
   - View extracted entities, temporal expressions, definitions
   - Export provenance graphs (PROV-O format)

---

## Key Features

### Without API Key (Standalone Mode)
- ✅ Named entity recognition
- ✅ Temporal expression extraction
- ✅ Definition extraction
- ✅ Text segmentation
- ✅ Sentiment analysis
- ✅ PROV-O provenance tracking

### With Anthropic API Key (Enhanced Mode)
- ✅ All standalone features, plus:
- ✅ LLM-powered tool recommendations
- ✅ Automated document analysis
- ✅ Cross-document synthesis
- ✅ Enhanced context extraction

---

## Need Help?

- **Docker issues**: [DOCKER_SETUP.md](DOCKER_SETUP.md#troubleshooting)
- **Usage questions**: See main [README.md](README.md)
- **Development guide**: [docs-internal/DEVELOPMENT_GUIDE.md](docs-internal/DEVELOPMENT_GUIDE.md)

---

## For JCDL 2025 Demo

This system was presented at JCDL 2025. See our paper:
[OntExtract_JCDL2025.pdf](papers/OntExtract_JCDL2025.pdf)

**Live demo credentials**: `demo` / `demo123`

**Demo experiment**: Agent Temporal Evolution (1910-2024)
