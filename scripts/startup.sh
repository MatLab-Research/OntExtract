#!/bin/bash
set -e

echo "Starting OntExtract application..."

# Function to check and update git repository
check_git_updates() {
    if [ "$CHECK_GIT_UPDATES" = "true" ]; then
        echo "Checking for git updates..."
        
        # Set git config for container
        git config --global --add safe.directory /app
        
        # Check if we're in a git repository
        if [ -d ".git" ]; then
            echo "Git repository detected."
            
            # Fetch latest changes
            git fetch origin
            
            # Get current branch
            CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
            TARGET_BRANCH=${GIT_BRANCH:-main}
            
            # Check if we need to update
            LOCAL_COMMIT=$(git rev-parse HEAD)
            REMOTE_COMMIT=$(git rev-parse origin/$TARGET_BRANCH)
            
            if [ "$LOCAL_COMMIT" != "$REMOTE_COMMIT" ]; then
                echo "Updates available. Current: $LOCAL_COMMIT, Remote: $REMOTE_COMMIT"
                
                # Switch to target branch if different
                if [ "$CURRENT_BRANCH" != "$TARGET_BRANCH" ]; then
                    echo "Switching to branch: $TARGET_BRANCH"
                    git checkout $TARGET_BRANCH
                fi
                
                # Pull latest changes
                echo "Pulling latest changes..."
                git pull origin $TARGET_BRANCH
                
                # Reinstall dependencies if requirements.txt changed
                if git diff --name-only HEAD~1 HEAD | grep -q "requirements.txt"; then
                    echo "Requirements.txt changed, updating dependencies..."
                    pip install -r requirements.txt
                fi
                
                echo "Repository updated successfully."
            else
                echo "Repository is up to date."
            fi
        else
            echo "Not a git repository, skipping git updates."
        fi
    else
        echo "Git updates disabled."
    fi
}

# Function to initialize database
init_database() {
    echo "Initializing database..."
    
    # Wait for database to be ready
    echo "Waiting for database to be ready..."
    while ! pg_isready -h db -p 5432 -U postgres; do
        sleep 2
    done
    
    echo "Database is ready, initializing tables..."
    flask init-db || echo "Database already initialized or error occurred."
}

# Function to start the application
start_application() {
    echo "Starting Flask application..."
    
    if [ "$FLASK_ENV" = "development" ]; then
        echo "Starting in development mode..."
        python run.py
    else
        echo "Starting in production mode..."
        # Use gunicorn for production
        if command -v gunicorn &> /dev/null; then
            gunicorn --bind 0.0.0.0:5000 --workers 4 --timeout 120 run:app
        else
            echo "Gunicorn not available, using Flask dev server..."
            python run.py
        fi
    fi
}

# Main execution
main() {
    # Check git updates if enabled
    check_git_updates
    
    # Initialize database
    init_database
    
    # Start the application
    start_application
}

# Execute main function
main "$@"
