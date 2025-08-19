# Claude Development Guidelines for OntExtract

## Project Organization

### Directory Structure
- **`tests/`** - Formal test files that are part of the test suite. Use pytest naming conventions.
- **`scratch/`** - Temporary test files, experiments, and quick prototypes (e.g., `test_oed_full_capture.py`).
- **`docs/`** - All documentation files go here. Keep documentation organized and out of root.
- **`archive/`** - Old code, deprecated features, or files to be retained for reference.
- **`pending_delete/`** - Files marked for deletion but requiring review before permanent removal.

### Clean Repository Practices
1. **No Root Clutter**: Avoid creating new files in the root directory unless absolutely necessary (e.g., config files like `.env`, `requirements.txt`)
2. **Test Organization**: 
   - **Formal tests**: Place in `tests/` folder following pytest conventions
   - **Temporary/experimental tests**: Place in `scratch/` folder for quick experiments
3. **Documentation**: New documentation should be created in `docs/` with clear, descriptive names
4. **Temporary Files**: Use `pending_delete/` for files that might be removed, allowing for review before deletion
5. **Legacy Code**: Move outdated but potentially useful code to `archive/` with date stamps
6. **Scratch Work**: Use `scratch/` for temporary test files, data output, and experimental code

## Application Configuration

### Ports
- **Flask Web Server**: Port `8765` (changed from default 5000)
- **PostgreSQL Database**: Port `5434` (via Docker container `ontextract_db`)
- **Note**: ProEthica application uses PostgreSQL on port `5433` (separate container)

### Database Connection
- **Development**: `postgresql://postgres:PASS@localhost:5434/ontextract_db`
- **Docker Internal**: `postgresql://postgres:PASS@db:5432/ontextract_db`
- The database container maps external port 5434 to internal port 5432

### Docker Containers
- `ontextract_db` - PostgreSQL database (port 5434)
- `ontextract_web` - Flask application (port 8765)
- `ontextract_db_init` - Database initialization (runs once)

## Development Commands

### Starting the Application
```bash
# Start database only
docker start ontextract_db

# Start full application with Docker Compose
docker-compose up

# Start Flask development server (requires database running)
python run.py
```

### Database Management
```bash
# Check database status
docker ps | grep ontextract_db

# View database logs
docker logs ontextract_db

# Connect to database
psql -h localhost -p 5434 -U postgres -d ontextract_db
```

### Testing
```bash
# Run tests (from project root)
pytest tests/

# Run specific test file
pytest tests/test_specific_feature.py
```

## Code Quality Standards

### UI/UX Conventions

#### Button Styling Guidelines
- **Primary Actions** (`btn-primary`): Main call-to-action buttons
  - Examples: "Create Experiment", "Submit", "Save"
- **Secondary Actions** (`btn-secondary`): Active but non-primary buttons
  - Examples: "Wizard", "Cancel", "Back", "Create Sample"
  - This is the default style for buttons that perform actions but aren't the main focus
- **Outline Buttons** (`btn-outline-*`): Used for small utility actions or icon-only buttons
  - Examples: Action buttons in tables (view, edit, delete)
  - Small utility buttons like "Select All" when space is limited
- **Danger Actions** (`btn-danger`): Destructive actions
  - Examples: "Delete", "Remove"

### Before Committing
1. **Lint Check**: Run linting if configured (`npm run lint`, `ruff`, `flake8`, etc.)
2. **Type Check**: Run type checking if available (`npm run typecheck`, `mypy`, etc.)
3. **Tests**: Ensure all tests pass
4. **Clean Up**: Move any temporary files to appropriate folders

### File Naming Conventions
- Test files: `test_*.py`
- Documentation: Use descriptive names with underscores (e.g., `api_reference.md`)
- Archive files: Include date stamp (e.g., `old_parser_20240819.py`)

## Environment Variables

Key environment variables are configured in `.env`:
- `DATABASE_URL` - PostgreSQL connection string
- `SECRET_KEY` - Flask secret key
- `FLASK_ENV` - Development/production mode
- `ANTHROPIC_API_KEY` - For Claude API
- `OPENAI_API_KEY` - For OpenAI API
- `OED_*` - Oxford English Dictionary API credentials

## Git Workflow

### Branch Strategy
- `main` - Production-ready code
- `dev` - Development branch (current)
- Feature branches - Create from `dev` for new features

### Commit Messages
- Be descriptive and concise
- Reference issue numbers when applicable
- Use conventional commits if team adopts them

## Recent Progress (January 2025)

### Completed Features
1. **Temporal Evolution Analysis**: 
   - Implemented `temporal_analysis_service.py` for tracking term evolution over time periods
   - Created dedicated temporal experiments UI at `/experiments/temporal`
   - Added period-based filtering and comparison capabilities

2. **Ontology Import Service**:
   - Built robust ontology importer supporting Turtle and JSON-LD formats
   - Implemented caching mechanism for better performance
   - Added support for BFO and PROV-O ontologies

3. **Term Management Interface**:
   - Created interactive term manager for experiments
   - Added temporal term manager variant for evolution analysis
   - Implemented term suggestion and validation features

4. **OED Integration Foundation**:
   - Developed multiple OED parser implementations
   - Created LangExtract-based parser for better accuracy
   - Added layout detection capabilities for dictionary entries

### Test Files Organization (January 19, 2025)
All experimental test files have been moved from root to `scratch/` directory:
- **OED-related tests** (now in `scratch/`):
  - `test_oed_fix.py` - OED API fixes and improvements
  - `test_oed_integration.py` - Integration testing with OED service
  - `test_oed_layout_detection.py` - Dictionary entry layout parsing
  - `test_oed_full_capture.py` - Full OED data capture testing
  - `test_oed_parser.py` - Core OED parser testing
  - `test_langextract_simple.py` - LangExtract parser testing
  
- **Other experimental tests** (now in `scratch/`):
  - `test_ontology_import.py` - Ontology import testing
  - `test_temporal_analysis.py` - Temporal analysis service testing
  - `test_time_periods.py` - Time period handling testing

### Next Goals

#### Priority 1: OED Lookup in Temporal Experiments
**Objective**: Integrate OED lookup functionality into the temporal experiments page to provide historical dictionary definitions for tracked terms.

**Implementation Plan**:
1. Add OED lookup button/interface to temporal term manager
2. Display historical definitions alongside temporal evolution data
3. Cache OED responses to minimize API calls
4. Show etymology and historical usage examples
5. Link definitions to specific time periods in the analysis

**Technical Requirements**:
- Modify `app/templates/experiments/temporal_term_manager.html` to include OED lookup UI
- Extend `app/routes/experiments.py` with OED lookup endpoints
- Use existing OED service infrastructure from `app/services/oed_service.py`
- Leverage the LangExtract parser for better definition extraction

## Notes for Claude

When working on this project:
1. **Formal tests**: Place in `tests/` folder
2. **Experimental/temporary tests**: Place in `scratch/` folder
3. Always place documentation in `docs/`
4. Use `archive/` and `pending_delete/` for file organization
5. Remember Flask runs on port 8765, database on port 5434
6. Check for existing similar code before creating new files
7. Run lint and type checks before marking tasks complete

### Current Focus Areas
- **OED Integration**: The OED test files in `scratch/` contain working code for API interaction and parsing
- **Temporal Analysis**: Core functionality is complete, now needs UI integration
- **Term Evolution**: Focus on connecting historical dictionary data with temporal tracking
