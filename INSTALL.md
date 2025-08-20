# OntExtract Installation Guide

## Quick Start (5 Minutes)

### Prerequisites
- Docker Desktop installed ([Download Docker](https://docs.docker.com/get-docker/))
- Git installed (for cloning the repository)
- The `.env` file provided by your administrator

### Installation Steps

1. **Clone the repository:**
   ```bash
   git clone https://github.com/MatLab-Research/OntExtract.git
   cd OntExtract
   ```

2. **Add your .env file:**
   - Copy the provided `.env` file to the project root directory
   - This file contains all necessary API keys and configuration

3. **Run the installer:**
   ```bash
   chmod +x install.sh
   ./install.sh
   ```

4. **Access the application:**
   - Open your browser to: http://localhost:8765
   - Register a new account through the web interface
   - Or use the admin setup script if provided by your administrator

That's it! The application is now running with all features enabled.

## Updating the Application

To get the latest features and bug fixes:

```bash
chmod +x update.sh
./update.sh
```

This will:
- Pull the latest code from GitHub
- Rebuild containers if needed
- Preserve all your data (database, uploads, logs)
- Restart the application

## Daily Usage

### Starting the Application
```bash
docker-compose start
```

### Stopping the Application
```bash
docker-compose stop
```

### Viewing Logs
```bash
docker-compose logs -f
```

### Restarting Services
```bash
docker-compose restart
```

## Data Persistence

All your data is automatically preserved in Docker volumes:
- **Database**: All experiments, documents, and configurations
- **Uploads**: All uploaded documents
- **Logs**: Application logs for troubleshooting

These persist across:
- Container restarts
- Application updates
- System reboots

## Troubleshooting

### Application won't start
1. Check if Docker is running:
   ```bash
   docker info
   ```

2. Check container logs:
   ```bash
   docker-compose logs web
   ```

3. Ensure port 8765 is not in use:
   ```bash
   lsof -i :8765
   ```

### Database connection issues
1. Restart the database:
   ```bash
   docker-compose restart db
   ```

2. Check database logs:
   ```bash
   docker-compose logs db
   ```

### Can't access the web interface
1. Verify the container is running:
   ```bash
   docker-compose ps
   ```

2. Check if the port is accessible:
   ```bash
   curl http://localhost:8765
   ```

### Reset everything (WARNING: Deletes all data)
```bash
docker-compose down -v
./install.sh
```

## Environment Configuration

If you need to modify settings, edit the `.env` file:

### Essential Settings
- `ANTHROPIC_API_KEY`: Your Claude API key
- `OPENAI_API_KEY`: Your OpenAI API key
- `SECRET_KEY`: Flask session secret (auto-generated)

### Optional Settings
- `GOOGLE_APPLICATION_CREDENTIALS`: For Google Cloud services
- `MAX_CONTENT_LENGTH`: Maximum file upload size (default: 16MB)
- `LOG_LEVEL`: Logging verbosity (INFO, DEBUG, ERROR)

After changing `.env`, restart the application:
```bash
docker-compose restart
```

## System Requirements

### Minimum Requirements
- 2 GB RAM
- 10 GB disk space
- Docker Desktop
- Internet connection (for API calls)

### Recommended
- 4 GB RAM
- 20 GB disk space
- Stable internet connection

## Security Notes

1. **Keep your .env file secure** - It contains API keys
2. **Don't commit .env to git** - It's in .gitignore
3. **Use strong passwords** for all user accounts
4. **Create admin accounts only through secure methods**

## Getting Help

If you encounter issues:

1. Check the logs:
   ```bash
   docker-compose logs -f
   ```

2. Restart the services:
   ```bash
   docker-compose restart
   ```

3. Contact your administrator with:
   - Error messages from logs
   - Steps to reproduce the issue
   - Your current version (check with `git log -1`)

## Advanced Usage

### Running in Development Mode
```bash
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up
```

### Accessing the Database Directly
```bash
docker-compose exec db psql -U postgres -d ontextract_db
```

### Backing Up the Database
```bash
docker-compose exec db pg_dump -U postgres ontextract_db > backup.sql
```

### Restoring from Backup
```bash
docker-compose exec -T db psql -U postgres ontextract_db < backup.sql
```

## Uninstallation

To completely remove OntExtract:

1. Stop and remove containers:
   ```bash
   docker-compose down
   ```

2. Remove data volumes (WARNING: Deletes all data):
   ```bash
   docker-compose down -v
   ```

3. Remove the project directory:
   ```bash
   cd ..
   rm -rf OntExtract
   ```

---

**Version**: 1.0  
**Last Updated**: January 2025  
**Support**: Contact your administrator
