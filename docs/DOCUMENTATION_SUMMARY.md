# OntExtract Documentation Summary

**Status:** Planning Complete
**Ready for:** Phase 1 Implementation
**Last Updated:** 2025-11-23

---

## Quick Reference

**GitHub Repository:** https://github.com/MatLab-Research/OntExtract

**Documentation Tool:** MkDocs Material

**Target Audience:** Digital humanities researchers with NLP knowledge, minimal coding experience

**Visual Content:** Static screenshots using Flameshot (no videos)

**Contribution Model:** Open to community contributions (eventually)

---

## Documentation Files

### Planning Documents

1. **[DOCUMENTATION_PLAN.md](DOCUMENTATION_PLAN.md)** (12,000+ words)
   - Complete documentation strategy
   - MkDocs Material setup and configuration
   - Content structure (3 phases)
   - Flask integration details
   - GitHub Pages migration plan (4 phases)
   - Maintenance workflow
   - Success criteria

2. **[DOCUMENTATION_QUICK_START.md](DOCUMENTATION_QUICK_START.md)** (2,500+ words)
   - Get infrastructure running in under 1 hour
   - Installation steps
   - Flask blueprint setup
   - Testing workflow
   - First 3 priority pages to write
   - Flameshot screenshot workflow

3. **[CONTENT_TEMPLATES.md](CONTENT_TEMPLATES.md)** (8,000+ words)
   - 5 page templates (Getting Started, How-To, Reference, Concept, Troubleshooting)
   - Complete outlines for 3 priority pages
   - **Academic Writing Style Guide** (detailed)
   - Writing and screenshot checklists
   - Style guide quick reference

4. **[DOCUMENTATION_SUMMARY.md](DOCUMENTATION_SUMMARY.md)** (this file)
   - Overview of documentation plan
   - Quick reference for implementation

---

## Academic Writing Style (CRITICAL)

### Core Principle

Maintain neutral academic tone throughout all documentation. Avoid marketing language, sales pitches, and constructions commonly associated with promotional content.

### Seven Prohibited Constructions

1. **No em dashes or colons** in body text
   - Use periods and separate sentences
   - "The system provides three capabilities. These are..." (not "three capabilities: X, Y, Z")

2. **No possessive forms for inanimate objects**
   - "The architecture of the system" (not "the system's architecture")
   - **Exception:** People's names (McLaren's analysis, Davis's approach)

3. **No front-loaded subordinate clauses**
   - Put main clause first
   - "The system analyzes documents by examining metadata" (not "By examining metadata, the system analyzes documents")

4. **No sentences starting with -ing words**
   - "Researchers identify events through the timeline view" (not "Using the timeline view, researchers identify events")

5. **No overused adjectives**
   - Never use: seamless, nuanced, robust, intriguing, comprehensive, systematic

6. **No marketing language**
   - Avoid: powerful, cutting-edge, intuitive, effortless, unlock, empower, leverage, state-of-the-art

7. **Use direct affirmative statements**
   - State what the system does
   - Avoid "rather than," "instead of," "not X but Y" unless essential

### Recommended Practices

- **Active voice:** "The system generates strategies" (not "Strategies are generated")
- **Present tense:** "The timeline displays events" (not "will display")
- **Specific language:** Describe actual capabilities, not vague claims
- **Neutral tone:** Describe what happens without enthusiasm

### Example Transformation

**Before (Marketing):**
```
OntExtract's powerful LLM orchestration seamlessly integrates cutting-edge NLP tools,
providing researchers with a comprehensive and robust framework for nuanced analysis.
```

**After (Academic):**
```
OntExtract uses LLM orchestration to suggest NLP tool configurations for document
processing. The system analyzes document characteristics and research goals, then
recommends processing strategies for user review.
```

---

## Priority Content (Phase 1)

### First 3 Pages to Write

1. **Installation Guide** ([docs/getting-started/installation.md](getting-started/installation.md))
   - System requirements
   - Installation steps
   - Database setup
   - Starting the application
   - Creating first user
   - Verification checklist

2. **Create Temporal Evolution Experiment** ([docs/how-to/create-temporal-experiment.md](how-to/create-temporal-experiment.md))
   - Complete end-to-end workflow
   - Example using "agent" (1910-2024)
   - 5 phases: Prepare, Create, Define Periods, Add Events, View Timeline
   - 15-20 screenshots
   - Common issues

3. **Timeline View Guide** ([docs/user-guide/experiments/temporal-evolution/timeline-view.md](user-guide/experiments/temporal-evolution/timeline-view.md))
   - Management view vs full-page view
   - Visual elements (period colors, START/END cards, event cards)
   - Hover interactions
   - Event type information (ontology-backed)
   - Managing timeline elements
   - Interpreting semantic change

### Phase 1 Deliverables

- Working `/docs` route in Flask app
- 3 core pages published
- 30-40 screenshots captured
- Basic navigation structure
- Search functionality working

---

## Implementation Checklist

### Infrastructure Setup (4-6 hours)

- [ ] Install MkDocs Material: `pip install mkdocs-material`
- [ ] Create `mkdocs.yml` configuration (copy from DOCUMENTATION_PLAN.md)
- [ ] Create directory structure: `docs/`, `docs/assets/screenshots/`
- [ ] Create Flask blueprint: `app/routes/docs.py`
- [ ] Register blueprint in `app/__init__.py`
- [ ] Add menu item to `app/templates/base.html`
- [ ] Build docs: `mkdocs build`
- [ ] Test route: http://localhost:8765/docs
- [ ] Add to `.gitignore`: `site/`

### Content Creation (20-30 hours)

- [ ] Write `docs/index.md` (welcome page)
- [ ] Write installation guide
- [ ] Capture 10-15 screenshots for installation
- [ ] Write temporal evolution workflow guide
- [ ] Capture 15-20 screenshots for workflow
- [ ] Write timeline view guide
- [ ] Capture 10-15 screenshots for timeline
- [ ] Create FAQ page skeleton
- [ ] Test all links work
- [ ] Review against academic writing checklist

### Quality Assurance

- [ ] User test: Follow installation guide from scratch
- [ ] User test: Create experiment following workflow guide
- [ ] Check all screenshots load correctly
- [ ] Verify search functionality works
- [ ] Test on different screen sizes
- [ ] Spell check all pages
- [ ] Review for marketing language (use checklist)

---

## Screenshot Standards

### Tool

**Flameshot** (installed on WSL)

```bash
# Launch annotation tool
flameshot gui

# Capture full screen to directory
flameshot full -p ~/onto/OntExtract/docs/assets/screenshots/
```

### Requirements

- High resolution (1920x1080 minimum)
- Dark mode (matches OntExtract Darkly theme)
- Crop to relevant UI elements
- Annotate if needed (arrows, boxes, highlights)
- Compress after editing (`optipng`)

### Naming Convention

`[feature]-[action]-[element].png`

Examples:
- `experiments-new-button.png`
- `experiments-new-focus-term-dropdown.png`
- `timeline-fullpage-view.png`
- `timeline-add-event-modal.png`
- `terms-quick-add-reference.png`

### Organization

```
docs/assets/screenshots/
├── experiments/
│   ├── experiments-list.png
│   ├── experiments-new-button.png
│   └── experiments-new-form.png
├── timeline/
│   ├── timeline-management-view.png
│   ├── timeline-fullpage-view.png
│   └── timeline-event-modal.png
└── terms/
    ├── terms-list.png
    └── terms-quick-add.png
```

---

## MkDocs Configuration

**File:** `mkdocs.yml` (project root)

**Key Settings:**
- Site URL: https://ontextract.ontorealm.net/docs
- Repository: https://github.com/MatLab-Research/OntExtract
- Theme: Material with dark mode (slate scheme)
- Plugins: search, minify
- Navigation: 4 top-level sections (Home, Getting Started, User Guide, How-To)

**Build Command:** `mkdocs build`

**Output:** `site/` directory (served by Flask at `/docs`)

Full configuration in [DOCUMENTATION_PLAN.md](DOCUMENTATION_PLAN.md).

---

## Flask Integration

### New Blueprint

**File:** `app/routes/docs.py`

Serves static files from `site/` directory at `/docs` route.

### Navigation Menu

**File:** `app/templates/base.html`

Add after Linked Data nav item (around line 270):

```html
<li class="nav-item">
    <a class="nav-link" href="{{ url_for('docs.index') }}" target="_blank">
        <i class="fas fa-book me-1"></i> Documentation
    </a>
</li>
```

### Registration

**File:** `app/__init__.py`

```python
from app.routes.docs import docs_bp
app.register_blueprint(docs_bp)
```

---

## GitHub Pages Migration (Future)

### Phase 1: Local Development (Current)

Docs served at `/docs` route in Flask app for offline users.

### Phase 2: GitHub Repository Setup

1. Create `.github/workflows/docs.yml` (GitHub Actions)
2. Configure GitHub Pages (gh-pages branch)
3. Test deployment

### Phase 3: Dual Deployment

Keep both Flask route (offline) and GitHub Pages (online).

### Phase 4: Full Migration

Point all documentation links to GitHub Pages.

URL: https://matlab-research.github.io/OntExtract/

---

## Writing Workflow

### Development Environment

**Terminal 1:** MkDocs auto-reload
```bash
mkdocs serve --dev-addr=127.0.0.1:8001
```

**Terminal 2:** Flask app
```bash
python run.py
```

**Terminal 3:** Edit docs
```bash
cd docs
vim user-guide/experiments/temporal-evolution/creating.md
```

**Browser 1:** Preview docs at http://localhost:8001

**Browser 2:** Reference app at http://localhost:8765

### Process

1. Write content in markdown
2. Preview in MkDocs server
3. Capture screenshots in Flameshot
4. Add screenshots to markdown
5. Review against academic writing checklist
6. Build: `mkdocs build`
7. Test in Flask app
8. Commit to git

---

## Success Metrics

### Immediate (After Phase 1)

- Users can complete temporal evolution workflow without assistance
- All demo experiment steps documented
- Zero navigation confusion (menu item works, links work)

### Short-term (After Phase 2)

- Support questions reduced by 50%
- Users reference docs before asking questions
- Conference attendees use docs during presentations

### Long-term (After Phase 4)

- Community contributions to documentation
- Search resolves 80% of user queries
- Docs maintained alongside code updates

---

## Common MkDocs Commands

```bash
# Serve with auto-reload (development)
mkdocs serve --dev-addr=127.0.0.1:8001

# Build static site
mkdocs build

# Clean build directory
rm -rf site/

# Validate configuration
mkdocs build --strict

# Deploy to GitHub Pages (future)
mkdocs gh-deploy
```

---

## Resources

**Planning Documents:**
- [DOCUMENTATION_PLAN.md](DOCUMENTATION_PLAN.md) - Complete strategy
- [DOCUMENTATION_QUICK_START.md](DOCUMENTATION_QUICK_START.md) - Quick implementation guide
- [CONTENT_TEMPLATES.md](CONTENT_TEMPLATES.md) - Templates and style guide

**External Resources:**
- MkDocs Material: https://squidfunk.github.io/mkdocs-material/
- Flameshot: https://flameshot.org/
- GitHub Pages: https://pages.github.com/

**OntExtract:**
- GitHub: https://github.com/MatLab-Research/OntExtract
- Live System: https://ontextract.ontorealm.net
- JCDL Paper: December 15-19, 2025

---

## Next Steps

1. **Review planning documents** - Ensure alignment with project goals
2. **Install MkDocs** - Follow DOCUMENTATION_QUICK_START.md
3. **Set up infrastructure** - Flask blueprint, menu item (4-6 hours)
4. **Write first page** - Installation guide using template (3-5 hours)
5. **Capture screenshots** - 10-15 for installation (2-3 hours)
6. **Test with user** - Validate clarity and completeness
7. **Iterate** - Refine based on feedback
8. **Expand** - Write remaining Phase 1 pages

---

**Status:** Planning complete, ready for implementation

**Timeline Estimate:**
- Infrastructure setup: 4-6 hours
- Phase 1 content (3 pages): 20-30 hours
- Phase 2 content (full manual): 20-30 hours
- Total to complete documentation: 44-66 hours

**Contact:** Documentation issues can be reported at https://github.com/MatLab-Research/OntExtract/issues

---

**Last Updated:** 2025-11-23
