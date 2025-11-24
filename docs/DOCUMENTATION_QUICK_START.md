# Documentation Quick Start Guide

**For:** Getting documentation infrastructure running quickly
**See Also:** [DOCUMENTATION_PLAN.md](DOCUMENTATION_PLAN.md) for complete details

---

## TL;DR

1. Install MkDocs Material
2. Create basic structure
3. Add Flask route for `/docs`
4. Add menu item to navbar
5. Start writing pages

**First Priority Pages:**
- Getting Started (installation, login)
- Creating Temporal Evolution Experiment (complete workflow)
- Timeline View (how to use)

---

## Installation (5 minutes)

```bash
# From OntExtract root directory
cd /home/chris/onto/OntExtract

# Install MkDocs Material
pip install mkdocs-material mkdocs-minify-plugin mkdocs-git-revision-date-localized-plugin

# Add to requirements.txt
echo "mkdocs-material>=9.0.0" >> requirements.txt
echo "mkdocs-minify-plugin>=0.6.0" >> requirements.txt
```

---

## Create Basic Structure (10 minutes)

```bash
# Create documentation directories
mkdir -p docs/getting-started
mkdir -p docs/user-guide/terms
mkdir -p docs/user-guide/documents
mkdir -p docs/user-guide/experiments/temporal-evolution
mkdir -p docs/user-guide/ontology
mkdir -p docs/how-to
mkdir -p docs/assets/screenshots

# Create placeholder index
cat > docs/index.md << 'EOF'
# OntExtract Documentation

Welcome to the OntExtract user manual.

## Quick Links

- [Getting Started](getting-started/installation.md)
- [Creating Your First Experiment](how-to/create-temporal-experiment.md)
- [FAQ](faq.md)

## About OntExtract

OntExtract is a digital humanities platform for analyzing historical documents.
EOF

# Create mkdocs.yml configuration file
# (Copy from DOCUMENTATION_PLAN.md or create minimal version)
```

---

## Minimal mkdocs.yml

Create `mkdocs.yml` in project root:

```yaml
site_name: OntExtract Documentation
site_description: User manual for OntExtract

theme:
  name: material
  palette:
    - scheme: slate
      primary: blue
      accent: teal

plugins:
  - search

markdown_extensions:
  - admonition
  - pymdownx.details
  - pymdownx.superfences
  - attr_list
  - tables
  - toc:
      permalink: true

nav:
  - Home: index.md
```

---

## Test Locally (2 minutes)

```bash
# Preview documentation (separate port from Flask app)
mkdocs serve --dev-addr=127.0.0.1:8001

# Open browser to: http://localhost:8001
# Should see basic documentation site

# Build static site
mkdocs build

# Output in site/ directory
ls -la site/
```

---

## Flask Integration (15 minutes)

### Step 1: Create docs blueprint

Create `app/routes/docs.py`:

```python
from flask import Blueprint, send_from_directory, abort
from pathlib import Path

docs_bp = Blueprint('docs', __name__, url_prefix='/docs')

# Path to MkDocs build output
DOCS_DIR = Path(__file__).parent.parent.parent / 'site'

@docs_bp.route('/')
@docs_bp.route('/<path:path>')
def index(path='index.html'):
    """Serve documentation static files"""
    if not DOCS_DIR.exists():
        abort(404, description="Documentation not built. Run 'mkdocs build' first.")

    # Handle clean URLs
    if path and not any(path.endswith(ext) for ext in ['.html', '.css', '.js', '.png', '.jpg', '.svg', '.woff', '.woff2']):
        # Try path/index.html for clean URLs
        test_path = DOCS_DIR / path / 'index.html'
        if test_path.exists():
            path = f"{path}/index.html"
        else:
            path = f"{path}.html"

    if not path:
        path = 'index.html'

    try:
        return send_from_directory(DOCS_DIR, path)
    except FileNotFoundError:
        abort(404)
```

### Step 2: Register blueprint

In `app/__init__.py`, add:

```python
# Add with other blueprint imports
from app.routes.docs import docs_bp

# Register with other blueprints
app.register_blueprint(docs_bp)
```

### Step 3: Add to navbar

In `app/templates/base.html`, find the navbar section (around line 270) and add:

```html
<!-- Add after Linked Data nav item, before user dropdown -->
<li class="nav-item">
    <a class="nav-link" href="{{ url_for('docs.index') }}" target="_blank">
        <i class="fas fa-book me-1"></i> Documentation
    </a>
</li>
```

**Note:** `target="_blank"` opens docs in new tab (optional, remove if you prefer same tab)

### Step 4: Build and test

```bash
# Build documentation
mkdocs build

# Start Flask app
python run.py

# Visit: http://localhost:8765/docs
# Should see documentation homepage
```

---

## Add to .gitignore

```bash
# Add to .gitignore
echo "site/" >> .gitignore

# Commit changes
git add docs/ mkdocs.yml app/routes/docs.py app/__init__.py app/templates/base.html requirements.txt .gitignore
git commit -m "docs: add MkDocs documentation infrastructure"
```

---

## First 3 Pages to Write

### Priority 1: Getting Started

**File:** `docs/getting-started/installation.md`

**Content:**
- System requirements (Python, PostgreSQL)
- Installation steps (clone, venv, pip install, database setup)
- Starting the application
- Creating first user account

### Priority 2: Complete Workflow

**File:** `docs/how-to/create-temporal-experiment.md`

**Content:**
- Step-by-step guide using "agent" example
- Screenshot of each step
- Expected outcomes
- Common issues

### Priority 3: Timeline View

**File:** `docs/user-guide/experiments/temporal-evolution/timeline-view.md`

**Content:**
- Management view vs full-page view
- Understanding period colors
- Hover interactions
- Creating/editing events
- Interpreting event cards

---

## Screenshot Workflow

### Tools

**Flameshot (WSL/Linux):**
```bash
# Verify Flameshot is installed
which flameshot

# Take screenshot with annotation tools
flameshot gui

# Or capture full screen
flameshot full -p ~/onto/OntExtract/docs/assets/screenshots/
```

**Save to:** `docs/assets/screenshots/[feature]/[descriptive-name].png`

### Naming Convention

- `experiments-new-button.png` - New Experiment button on experiments list
- `experiments-new-focus-term.png` - Focus term dropdown in new experiment form
- `timeline-fullpage-view.png` - Full-page timeline view
- `timeline-add-event-modal.png` - Add semantic event modal

### Screenshot Checklist

- [ ] High resolution (1920x1080 minimum)
- [ ] Dark mode (matches app theme)
- [ ] Crop to relevant area (no excessive whitespace)
- [ ] Annotate if needed (arrows, boxes, highlights)
- [ ] Compress (use `optipng` or similar)

---

## Writing Tips

**IMPORTANT:** Follow academic writing style guide in [CONTENT_TEMPLATES.md](CONTENT_TEMPLATES.md).

Key rules:
- No em dashes or colons in body text
- No possessive forms for inanimate objects (the system's → of the system)
- Main clause first (avoid front-loaded subordinate clauses)
- No sentences starting with -ing words
- Avoid marketing language (seamless, robust, powerful, intuitive, etc.)
- Use direct affirmative statements
- Active voice and present tense

### Use Admonitions

```markdown
!!! tip "Auto-Fill Feature"
    When you select a focus term, the experiment name automatically fills in. You can customize this if needed.

!!! warning "Publication Date Required"
    Documents without publication dates won't appear in temporal analysis.
```

### Use Clear Steps

```markdown
## Step 1: Navigate to Experiments

1. Click **Experiments** in the main navigation bar
2. Click the blue **New Experiment** button in the top-right corner

![New Experiment Button](../../assets/screenshots/experiments/experiments-new-button.png)
```

### Link to Related Pages

```markdown
Before creating an experiment, you should:

- [Create a focus term](../terms/creating-terms.md)
- [Upload source documents](../documents/uploading-documents.md)
```

---

## Common MkDocs Commands

```bash
# Serve with auto-reload (development)
mkdocs serve --dev-addr=127.0.0.1:8001

# Build static site
mkdocs build

# Build and deploy to GitHub Pages (future)
mkdocs gh-deploy

# Clean build directory
rm -rf site/

# Validate configuration
mkdocs build --strict
```

---

## Troubleshooting

### "Documentation not built" error in Flask

**Solution:** Run `mkdocs build` before starting Flask app

### Broken links in documentation

**Solution:** Use relative links, test with `mkdocs serve`

### Screenshots not displaying

**Solution:** Check path is correct: `![Alt text](../../assets/screenshots/file.png)`

### Search not working

**Solution:** Make sure `search` plugin is in `mkdocs.yml` plugins section

---

## Next Steps After Infrastructure Setup

1. **Write 3 priority pages** (installation, workflow, timeline)
2. **Capture 10-15 screenshots** (main workflows)
3. **Test with a user** (watch them follow a guide)
4. **Iterate based on feedback**
5. **Expand to remaining sections**

---

## Development Workflow

```bash
# Terminal 1: MkDocs auto-reload
cd /home/chris/onto/OntExtract
mkdocs serve --dev-addr=127.0.0.1:8001

# Terminal 2: Flask app
python run.py

# Terminal 3: Edit docs
cd docs
vim user-guide/experiments/temporal-evolution/creating.md

# Browser 1: Preview docs at http://localhost:8001
# Browser 2: Reference app at http://localhost:8765
```

---

## Questions?

**See Also:**
- [DOCUMENTATION_PLAN.md](DOCUMENTATION_PLAN.md) - Complete strategy and content structure
- [CONTENT_TEMPLATES.md](CONTENT_TEMPLATES.md) - Page templates and academic writing style guide

**GitHub Repository:** https://github.com/MatLab-Research/OntExtract

---

**Last Updated:** 2025-11-23
