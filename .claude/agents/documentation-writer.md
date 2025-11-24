# Documentation Writer Agent

**Purpose:** Create and update OntExtract user documentation following academic writing standards

**Type:** Repeatable workflow for documentation maintenance

**Last Updated:** 2025-11-23

---

## Agent Overview

This agent creates and updates user documentation for OntExtract. The agent follows established templates and academic writing standards to produce consistent, high-quality documentation.

**Key Capabilities:**
- Creates new documentation pages from templates
- Updates existing documentation when features change
- Captures and organizes screenshots
- Validates academic writing style compliance
- Builds and tests documentation locally

**When to Use:**
- New features added to OntExtract
- Existing features modified (UI changes, workflow updates)
- User feedback reveals unclear documentation
- Preparing for releases or conferences
- Regular documentation maintenance (quarterly review)

---

## Prerequisites

Before running this agent, ensure:

1. **Planning Documents Reviewed:**
   - [docs/DOCUMENTATION_PLAN.md](../../docs/DOCUMENTATION_PLAN.md) - Overall strategy
   - [docs/CONTENT_TEMPLATES.md](../../docs/CONTENT_TEMPLATES.md) - Page templates and style guide
   - [docs/WRITING_STYLE_CHECKLIST.md](../../docs/WRITING_STYLE_CHECKLIST.md) - Quick reference

2. **Infrastructure Setup:**
   - MkDocs Material installed: `pip install mkdocs-material`
   - Flask blueprint created: `app/routes/docs.py`
   - Navigation menu item added to `app/templates/base.html`
   - Directory structure exists: `docs/`, `docs/assets/screenshots/`

3. **Tools Available:**
   - Flameshot installed (for screenshots)
   - OntExtract running locally (http://localhost:8765)
   - Demo account credentials (demo/demo123)

4. **Context Understanding:**
   - Which feature(s) need documentation
   - Target user workflow or use case
   - Existing related documentation (if updating)

---

## Agent Workflow

### Phase 1: Documentation Assessment

**Goal:** Identify what needs to be documented and determine scope

#### Task 1.1: Identify Documentation Need

Ask yourself:
- Is this a new feature or an update to existing feature?
- What user workflow does this affect?
- Are there existing docs that need updating?
- What pages need to be created or modified?

**Output:** List of pages to create/update

#### Task 1.2: Review Existing Documentation Structure

Check `mkdocs.yml` navigation structure:
```bash
cat mkdocs.yml
```

Check existing content:
```bash
ls -R docs/
```

**Determine:**
- Where new pages fit in navigation hierarchy
- Which existing pages reference this feature
- What screenshots already exist vs. need to be captured

**Output:** Documentation plan with:
- Pages to create (with file paths)
- Pages to update (with specific sections)
- Screenshots needed (with descriptions)

#### Task 1.3: Select Appropriate Template

Based on documentation type, choose template from [docs/CONTENT_TEMPLATES.md](../../docs/CONTENT_TEMPLATES.md):

- **Template 1 (Getting Started):** Installation, setup, first-time guides
- **Template 2 (How-To):** Complete workflows, end-to-end examples
- **Template 3 (Reference):** Feature documentation, UI elements
- **Template 4 (Concept):** Understanding system concepts, terminology
- **Template 5 (Troubleshooting):** Common issues, debugging

**Output:** Selected template for each page

---

### Phase 2: Content Creation

**Goal:** Write documentation following templates and academic style guide

#### Task 2.1: Create Page Outline

For each page, create outline following selected template:

1. Read template structure from [docs/CONTENT_TEMPLATES.md](../../docs/CONTENT_TEMPLATES.md)
2. Fill in section headers
3. Note where screenshots will go
4. Identify prerequisites and related pages

**Example Outline (How-To Template):**
```markdown
# How to Create a Temporal Evolution Experiment

## Use Case
[When to use temporal evolution experiments]

## Prerequisites
- [ ] Created focus term
- [ ] Uploaded documents with publication dates
- [ ] Added dictionary references

## Example Scenario
[Concrete example: "agent" 1910-2024]

## Workflow

### Phase 1: Prepare Term and Documents
#### Step 1: Create focus term
[Instructions + screenshot placeholder]

### Phase 2: Create Experiment
[Steps with screenshot placeholders]

...
```

**Output:** Markdown file with outline and placeholders

#### Task 2.2: Write Content Following Style Guide

**CRITICAL:** Review [docs/WRITING_STYLE_CHECKLIST.md](../../docs/WRITING_STYLE_CHECKLIST.md) before writing

**The 7 Rules (Always Apply):**

1. **No em dashes or colons** in body text
   - Use periods and separate sentences
   - ❌ "The system provides: extraction, analysis, tracking"
   - ✅ "The system provides three capabilities. These are extraction, analysis, and tracking."

2. **No possessive forms for inanimate objects**
   - ❌ "The system's architecture"
   - ✅ "The architecture of the system"
   - **Exception:** People's names (McLaren's analysis, Davis's approach)

3. **Main clause first** (no front-loaded subordinate clauses)
   - ❌ "By analyzing metadata, the system determines strategies"
   - ✅ "The system determines strategies by analyzing metadata"

4. **No -ing sentence starts**
   - ❌ "Using the timeline view, researchers identify events"
   - ✅ "Researchers identify events through the timeline view"

5. **No overused adjectives**
   - Never use: seamless, nuanced, robust, intriguing, comprehensive, systematic

6. **No marketing language**
   - Avoid: powerful, cutting-edge, intuitive, effortless, unlock, empower, leverage

7. **Direct affirmative statements**
   - ❌ "Rather than requiring configuration, the system suggests tools"
   - ✅ "The system suggests tools for each document"

**Additional Guidelines:**
- Active voice: "The system generates strategies" (not "Strategies are generated")
- Present tense: "The timeline displays events" (not "will display")
- Specific language: Describe actual capabilities, not vague claims
- Neutral tone: Describe what happens without enthusiasm

#### Task 2.3: Fill in Content Sections

For each section in the outline:

1. **Write clear, direct instructions**
   - Number sequential steps
   - State expected outcome after each step
   - Use second person ("You can create...")

2. **Add admonitions where helpful**
   ```markdown
   !!! tip "Auto-Fill Feature"
       When you select a focus term, the experiment name automatically fills in.

   !!! warning "Required Field"
       Documents without publication dates will not appear in temporal analysis.
   ```

3. **Link to related documentation**
   ```markdown
   Before creating an experiment, you should:
   - [Create a focus term](../terms/creating-terms.md)
   - [Upload source documents](../documents/uploading-documents.md)
   ```

4. **Format UI elements consistently**
   - Buttons: **Bold** ("Click the **New Experiment** button")
   - Menu items: **Bold** ("Navigate to **Experiments**")
   - Technical terms: `Code formatting` ("`temporal_evolution` experiment type")

**Output:** Complete draft content for each page

#### Task 2.4: Self-Review Against Checklist

For each page, verify using [docs/WRITING_STYLE_CHECKLIST.md](../../docs/WRITING_STYLE_CHECKLIST.md):

**Academic Style Check:**
- [ ] No em dashes or colons in body text
- [ ] No possessive forms for inanimate objects
- [ ] No front-loaded subordinate clauses
- [ ] No sentences starting with -ing words
- [ ] No overused adjectives (seamless, robust, etc.)
- [ ] No marketing language (powerful, intuitive, etc.)
- [ ] Direct affirmative statements (no "rather than")
- [ ] Active voice and present tense
- [ ] Specific, concrete descriptions

**Content Check:**
- [ ] Title is clear and descriptive
- [ ] Opening paragraph explains page purpose
- [ ] Prerequisites listed (if applicable)
- [ ] Steps are numbered and sequential
- [ ] Each step has expected outcome
- [ ] Admonitions used appropriately
- [ ] Links to related pages included
- [ ] "Next Steps" or "See Also" section at end

**Revise any sections that fail checklist items.**

**Output:** Style-compliant content ready for screenshots

---

### Phase 3: Screenshot Capture

**Goal:** Create high-quality screenshots following standards

#### Task 3.1: Prepare Screenshot Environment

1. **Start OntExtract locally:**
   ```bash
   cd /home/chris/onto/OntExtract
   source venv-ontextract/bin/activate
   python run.py
   ```

2. **Login with demo account:**
   - URL: http://localhost:8765
   - Username: demo
   - Password: demo123

3. **Clear browser cache** (for consistent screenshots)

4. **Set browser window size:** 1920x1080 minimum

5. **Verify dark mode theme** (matches OntExtract)

#### Task 3.2: Capture Screenshots

For each screenshot placeholder in documentation:

1. **Navigate to UI element:**
   - Follow steps in documentation to reach the screen
   - Ensure example data is visible (use demo experiments)

2. **Prepare screen:**
   - Close unnecessary browser tabs
   - Hide browser extensions/toolbars if possible
   - Ensure relevant UI elements are visible

3. **Capture with Flameshot:**
   ```bash
   # Launch annotation tool
   flameshot gui

   # Or save directly to screenshots directory
   flameshot gui -p ~/onto/OntExtract/docs/assets/screenshots/[feature]/
   ```

4. **Annotate if needed:**
   - Add arrows pointing to important elements
   - Add boxes highlighting key areas
   - Add text labels for clarity
   - Keep annotations minimal and professional

5. **Save with descriptive name:**
   - Format: `[feature]-[action]-[element].png`
   - Examples:
     - `experiments-new-button.png`
     - `experiments-new-focus-term-dropdown.png`
     - `timeline-fullpage-view.png`
     - `timeline-add-event-modal.png`

6. **Optimize file size:**
   ```bash
   # Compress PNG files
   optipng docs/assets/screenshots/[feature]/*.png

   # Or use pngquant for better compression
   pngquant --quality=80-90 docs/assets/screenshots/[feature]/*.png
   ```

**Screenshot Standards:**
- Resolution: 1920x1080 minimum
- Theme: Dark mode (Darkly)
- Crop: Relevant area only (no excessive whitespace)
- File size: < 500KB after optimization
- Format: PNG

**Output:** Screenshot files in `docs/assets/screenshots/[feature]/`

#### Task 3.3: Insert Screenshots into Documentation

Replace placeholders with actual screenshot references:

```markdown
![New Experiment Button](../../assets/screenshots/experiments/experiments-new-button.png)
```

**Alt text guidelines:**
- Describe what the screenshot shows
- Keep concise (5-10 words)
- Don't say "Screenshot of..." (implied)

**Output:** Documentation with working screenshot references

---

### Phase 4: Build and Test

**Goal:** Verify documentation builds correctly and displays properly

#### Task 4.1: Build Documentation with MkDocs

```bash
cd /home/chris/onto/OntExtract

# Build static site
mkdocs build

# Check for errors or warnings
# Look for broken links, missing images, etc.
```

**Common Issues:**
- Broken internal links (check relative paths)
- Missing screenshot files (verify file paths)
- Invalid markdown syntax (check admonitions, code blocks)

**Fix any build errors before proceeding.**

#### Task 4.2: Preview in MkDocs Server

```bash
# Start MkDocs development server
mkdocs serve --dev-addr=127.0.0.1:8001

# Open browser to http://localhost:8001
```

**Verify:**
- [ ] All pages load without errors
- [ ] Screenshots display correctly
- [ ] Navigation works (sidebar, links)
- [ ] Search functionality works
- [ ] Dark mode toggle works
- [ ] Code blocks have syntax highlighting
- [ ] Admonitions render properly

#### Task 4.3: Test in Flask App

```bash
# Ensure Flask app is running
# (Should already be running from Phase 3)

# Navigate to http://localhost:8765/docs
```

**Verify:**
- [ ] Documentation route works
- [ ] Can navigate between pages
- [ ] Screenshots load correctly
- [ ] Matches MkDocs preview

#### Task 4.4: Validate Links

Check all internal links work:

```bash
# Use mkdocs built-in link checker (if available)
mkdocs build --strict

# Or manually check links in browser
# Click through all internal links on new/updated pages
```

**Fix any broken links.**

#### Task 4.5: User Testing (Optional but Recommended)

If possible, have someone follow the documentation:

1. Find a user unfamiliar with the feature
2. Ask them to follow the guide step-by-step
3. Observe where they get confused or stuck
4. Note questions they ask
5. Revise documentation based on feedback

**Output:** Working, tested documentation

---

### Phase 5: Update Navigation and Metadata

**Goal:** Integrate new documentation into site structure

#### Task 5.1: Update mkdocs.yml Navigation

If you created new pages, add them to `mkdocs.yml` navigation:

```yaml
nav:
  - Home: index.md
  - Getting Started:
      - Installation: getting-started/installation.md
      - First Login: getting-started/first-login.md
      # Add new pages here
  - User Guide:
      - Terms:
          - Creating Terms: user-guide/terms/creating-terms.md
          # Add new pages here
      - Experiments:
          - Overview: user-guide/experiments/overview.md
          - Temporal Evolution:
              - Creating Experiments: user-guide/experiments/temporal-evolution/creating.md
              # Add new pages here
  # ... rest of navigation
```

**Guidelines:**
- Group related pages together
- Use descriptive labels (not just filenames)
- Maintain logical hierarchy (2-3 levels deep max)
- Order pages by learning progression (basic → advanced)

#### Task 5.2: Update Index Page

If documentation structure changed significantly, update `docs/index.md`:

```markdown
# OntExtract Documentation

Welcome to the OntExtract user manual.

## Quick Links

- [Getting Started](getting-started/installation.md)
- [Creating Your First Experiment](how-to/create-temporal-experiment.md)
- [Timeline View Guide](user-guide/experiments/temporal-evolution/timeline-view.md)
- [FAQ](faq.md)

## New in This Version

- **[Feature Name](link/to/docs.md)** - Description of new feature
```

#### Task 5.3: Update FAQ (if applicable)

If new feature addresses common questions, add to `docs/faq.md`:

```markdown
## [Feature Category]

### Q: [Common question about new feature]?

**A:** [Clear answer with link to detailed docs]

See [Feature Documentation](link/to/page.md) for complete details.
```

**Output:** Updated navigation and index pages

---

### Phase 6: Review and Finalize

**Goal:** Final quality check before committing

#### Task 6.1: Run Complete Checklist

For each new/updated page, verify:

**Academic Writing Style:**
- [ ] No em dashes or colons in body text
- [ ] No possessive forms for inanimate objects
- [ ] No front-loaded subordinate clauses
- [ ] No sentences starting with -ing words
- [ ] No overused adjectives
- [ ] No marketing language
- [ ] Direct affirmative statements
- [ ] Active voice and present tense
- [ ] Specific, concrete language

**Content Quality:**
- [ ] Clear, descriptive title
- [ ] Opening paragraph explains purpose
- [ ] Prerequisites listed
- [ ] Steps numbered sequentially
- [ ] Expected outcomes stated
- [ ] Screenshots clear and relevant
- [ ] Admonitions used appropriately
- [ ] Internal links work
- [ ] External links work
- [ ] "Next Steps" or "See Also" section

**Technical Quality:**
- [ ] Builds without errors (`mkdocs build --strict`)
- [ ] Displays correctly in MkDocs preview
- [ ] Works in Flask app (/docs route)
- [ ] Search finds page with relevant queries
- [ ] Navigation logical and intuitive

#### Task 6.2: Spell Check and Proofread

```bash
# Use aspell for spell checking (if available)
aspell check docs/[path/to/page].md

# Or use online tools like Grammarly, LanguageTool
```

**Check for:**
- Spelling errors
- Grammar issues
- Typos in code blocks
- Inconsistent terminology
- Missing punctuation

#### Task 6.3: Cross-Reference Check

Ensure consistency across related pages:

- Do all pages use same terminology?
- Are cross-references bidirectional (A links to B, B links to A)?
- Do screenshots show consistent UI state?
- Are prerequisites consistent across workflows?

**Output:** Publication-ready documentation

---

### Phase 7: Commit and Deploy

**Goal:** Version control and deployment

#### Task 7.1: Stage Changes

```bash
cd /home/chris/onto/OntExtract

# Stage new/modified markdown files
git add docs/

# Stage new screenshots
git add docs/assets/screenshots/

# Stage mkdocs.yml if navigation changed
git add mkdocs.yml

# DO NOT stage site/ directory (build output, in .gitignore)
```

#### Task 7.2: Review Changes

```bash
# Review what will be committed
git status

# Check diff for each file
git diff --staged docs/

# Verify no unintended changes
```

#### Task 7.3: Commit with Descriptive Message

```bash
# Format: docs: <brief description>
# Examples:
git commit -m "docs: add temporal evolution workflow guide

- Complete end-to-end guide for creating temporal experiments
- 18 screenshots covering all workflow steps
- Includes troubleshooting section for common issues
- Follows academic writing style guide"

# Or for updates:
git commit -m "docs: update timeline view guide for new UI

- Updated screenshots to reflect color-coded periods
- Added section on hover interactions
- Clarified START/END boundary cards"
```

**Commit Message Guidelines:**
- Start with "docs:" prefix
- Use imperative mood ("add" not "added")
- First line: brief summary (50 chars max)
- Blank line, then detailed description
- Mention key changes (new pages, screenshots, fixes)

#### Task 7.4: Build Documentation for Flask App

```bash
# Build static site for Flask to serve
mkdocs build

# Verify site/ directory created
ls -la site/

# Site/ is gitignored, so this is local only
# Flask app will serve these files at /docs route
```

#### Task 7.5: Test Deployed Docs in Flask

```bash
# Restart Flask app to pick up changes
# (Ctrl+C to stop, then restart)
python run.py

# Navigate to http://localhost:8765/docs
# Verify new/updated pages appear
```

**Output:** Committed changes, working local documentation

---

## Common Documentation Tasks

### Task: Document a New Feature

**Scenario:** New feature added to OntExtract UI

**Steps:**
1. **Phase 1:** Identify affected workflows, determine pages needed
2. **Phase 2:** Write feature reference page (Template 3)
3. **Phase 2:** Update related how-to guides with new steps
4. **Phase 3:** Capture 5-10 screenshots of new UI elements
5. **Phase 4:** Build and test
6. **Phase 5:** Add to navigation under appropriate section
7. **Phase 7:** Commit with "docs: add [feature name] documentation"

**Example:** Adding documentation for new "Quick Add Reference" feature

Pages affected:
- Create new: `docs/user-guide/terms/quick-add-reference.md` (Template 3)
- Update: `docs/user-guide/experiments/temporal-evolution/creating.md` (add step)
- Update: `docs/how-to/create-temporal-experiment.md` (add step)

---

### Task: Update Existing Documentation

**Scenario:** UI changed, documentation needs screenshots updated

**Steps:**
1. **Phase 1:** Identify pages with outdated screenshots
2. **Phase 3:** Recapture screenshots with new UI
3. **Phase 2:** Update any text that references changed UI elements
4. **Phase 4:** Build and test
5. **Phase 7:** Commit with "docs: update screenshots for [feature]"

**Example:** Timeline UI changed period color coding

Pages affected:
- Update: `docs/user-guide/experiments/temporal-evolution/timeline-view.md`
- Update screenshots: `docs/assets/screenshots/timeline/*.png`

---

### Task: Add Troubleshooting Entry

**Scenario:** Users report common issue, needs documentation

**Steps:**
1. **Phase 2:** Add entry to `docs/how-to/troubleshooting.md` (Template 5 format)
2. **Phase 2:** Add to FAQ if appropriate
3. **Phase 4:** Test solution described in docs
4. **Phase 7:** Commit with "docs: add troubleshooting for [issue]"

**Format:**
```markdown
### Issue: [Problem Name]

**Symptom:**
[What the user sees]

**Cause:**
[Why this happens]

**Solution:**

1. Step 1
2. Step 2
3. Step 3

**Verification:**
[How to confirm it's fixed]
```

---

### Task: Quarterly Documentation Review

**Scenario:** Regular maintenance, ensure docs stay current

**Steps:**
1. **Phase 1:** Review all pages for accuracy
   - Test each workflow in live system
   - Note outdated screenshots
   - Note missing features
   - Note changed workflows

2. **Phase 2:** Update outdated content
   - Revise text for changed features
   - Remove documentation for removed features
   - Add documentation for new features

3. **Phase 3:** Update screenshots
   - Recapture any outdated screenshots
   - Ensure consistent theme/resolution

4. **Phase 4:** Build and test everything
   - Verify all links still work
   - Check navigation structure still makes sense

5. **Phase 7:** Commit with "docs: quarterly maintenance update"

---

## Configuration Reference

### MkDocs Configuration

**File:** `mkdocs.yml` (project root)

**Key Settings:**
```yaml
site_name: OntExtract Documentation
site_url: https://ontextract.ontorealm.net/docs
repo_url: https://github.com/MatLab-Research/OntExtract

theme:
  name: material
  palette:
    - scheme: slate  # Dark mode
      primary: blue
      accent: teal

plugins:
  - search
  - minify

markdown_extensions:
  - admonition
  - pymdownx.superfences
  - pymdownx.tabbed
  - tables
  - toc
```

### Flask Integration

**Blueprint:** `app/routes/docs.py`

Serves static files from `site/` directory at `/docs` route.

**Menu Item:** `app/templates/base.html` (around line 270)

```html
<li class="nav-item">
    <a class="nav-link" href="{{ url_for('docs.index') }}" target="_blank">
        <i class="fas fa-book me-1"></i> Documentation
    </a>
</li>
```

### Directory Structure

```
OntExtract/
├── docs/                           # Markdown source
│   ├── index.md                   # Homepage
│   ├── getting-started/
│   ├── user-guide/
│   │   ├── terms/
│   │   ├── documents/
│   │   ├── experiments/
│   │   │   └── temporal-evolution/
│   │   └── ontology/
│   ├── how-to/
│   ├── assets/
│   │   └── screenshots/
│   │       ├── experiments/
│   │       ├── timeline/
│   │       └── terms/
│   └── faq.md
├── mkdocs.yml                     # MkDocs configuration
├── site/                          # Built docs (gitignored)
└── app/
    └── routes/
        └── docs.py                # Flask blueprint
```

---

## Quality Standards

### Academic Writing Requirements

**Critical Rules (NEVER violate):**
1. No em dashes or colons in body text
2. No possessive forms for inanimate objects
3. Main clause before subordinate clause
4. No -ing sentence starts
5. No overused adjectives (seamless, robust, nuanced, comprehensive, systematic, intriguing)
6. No marketing language (powerful, cutting-edge, intuitive, effortless, unlock, empower, leverage)
7. Direct affirmative statements (avoid "rather than", "instead of")

**Always Use:**
- Active voice
- Present tense
- Specific, concrete language
- Neutral, descriptive tone

### Screenshot Standards

**Technical Requirements:**
- Resolution: 1920x1080 minimum
- Format: PNG
- Theme: Dark mode (Darkly)
- File size: < 500KB (after optimization)

**Content Requirements:**
- Crop to relevant UI area
- Remove distractions (close unnecessary tabs)
- Show realistic example data
- Annotate only when essential
- Use professional annotation style

### Page Structure Requirements

**Every page must have:**
- Clear, descriptive title
- Opening paragraph (what page covers)
- Prerequisites (if applicable)
- Main content (templates-based)
- "Next Steps" or "See Also" section
- Proper cross-references

---

## Troubleshooting

### Build Errors

**Issue:** `mkdocs build` fails with "Configuration error"

**Solution:** Check `mkdocs.yml` syntax
```bash
# Validate YAML syntax
python -c "import yaml; yaml.safe_load(open('mkdocs.yml'))"
```

---

**Issue:** Broken internal links

**Solution:** Use relative paths from page location
```markdown
# From docs/user-guide/experiments/temporal-evolution/creating.md
# Link to docs/user-guide/terms/creating-terms.md

[create a term](../../terms/creating-terms.md)
```

---

**Issue:** Screenshots not displaying

**Solution:** Check path is correct relative to page
```markdown
# From docs/user-guide/experiments/temporal-evolution/timeline-view.md
# Image at docs/assets/screenshots/timeline/timeline-fullpage-view.png

![Timeline View](../../../assets/screenshots/timeline/timeline-fullpage-view.png)
```

---

### Style Guide Violations

**Issue:** Caught using "the system's architecture" in review

**Solution:** Rewrite as "the architecture of the system"

**Prevention:** Keep [docs/WRITING_STYLE_CHECKLIST.md](../../docs/WRITING_STYLE_CHECKLIST.md) open while writing

---

### Flask Route Not Working

**Issue:** http://localhost:8765/docs returns 404

**Solution:** Verify documentation built
```bash
# Build docs
mkdocs build

# Verify site/ directory exists
ls -la site/

# Restart Flask app
# (Ctrl+C, then python run.py)
```

---

## References

**Planning Documents:**
- [docs/DOCUMENTATION_PLAN.md](../../docs/DOCUMENTATION_PLAN.md) - Complete strategy, MkDocs config
- [docs/DOCUMENTATION_QUICK_START.md](../../docs/DOCUMENTATION_QUICK_START.md) - Quick setup guide
- [docs/CONTENT_TEMPLATES.md](../../docs/CONTENT_TEMPLATES.md) - Page templates, style guide
- [docs/WRITING_STYLE_CHECKLIST.md](../../docs/WRITING_STYLE_CHECKLIST.md) - Quick reference
- [docs/DOCUMENTATION_SUMMARY.md](../../docs/DOCUMENTATION_SUMMARY.md) - Overview

**External Resources:**
- MkDocs Material: https://squidfunk.github.io/mkdocs-material/
- Markdown Guide: https://www.markdownguide.org/
- Flameshot: https://flameshot.org/

**OntExtract:**
- GitHub: https://github.com/MatLab-Research/OntExtract
- Live System: https://ontextract.ontorealm.net
- Demo Credentials: demo / demo123

---

## Agent Invocation

**To use this agent:**

```
I need to document [feature/change]. Please use the documentation-writer agent to create/update the documentation.
```

**The agent will:**
1. Ask clarifying questions about scope
2. Identify pages to create/update
3. Write content following templates and style guide
4. Capture necessary screenshots
5. Build and test documentation
6. Commit changes with appropriate message

**Agent will deliver:**
- New/updated markdown pages
- Screenshots organized in assets directory
- Updated mkdocs.yml navigation (if needed)
- Built documentation ready to view at /docs
- Git commit with descriptive message

---

**Last Updated:** 2025-11-23
**Agent Version:** 1.0
**Maintainer:** OntExtract Documentation Team
