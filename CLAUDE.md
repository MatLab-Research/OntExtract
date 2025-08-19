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

## Notes for Claude

When working on this project:
1. **Formal tests**: Place in `tests/` folder
2. **Experimental/temporary tests**: Place in `scratch/` folder
3. Always place documentation in `docs/`
4. Use `archive/` and `pending_delete/` for file organization
5. Remember Flask runs on port 8765, database on port 5434
6. Check for existing similar code before creating new files
7. Run lint and type checks before marking tasks complete