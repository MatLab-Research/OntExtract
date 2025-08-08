#!/usr/bin/env python3
"""
OntExtract - Ontology-based Text Analysis Application
Main application entry point
"""

import os
from flask.cli import FlaskGroup
from app import create_app, db

# Create Flask application
app = create_app()
cli = FlaskGroup(app)

@app.cli.command()
def init_db():
    """Initialize the database"""
    db.create_all()
    print("Database initialized successfully!")

@app.cli.command()
def create_admin():
    """Create an admin user"""
    from app.models.user import User
    
    username = input("Enter admin username: ")
    email = input("Enter admin email: ")
    password = input("Enter admin password: ")
    
    # Check if user already exists
    if User.query.filter_by(username=username).first():
        print("User already exists!")
        return
    
    admin_user = User(
        username=username,
        email=email,
        password=password,
        is_admin=True
    )
    
    db.session.add(admin_user)
    db.session.commit()
    print(f"Admin user '{username}' created successfully!")

@app.shell_context_processor
def make_shell_context():
    """Shell context for flask shell command"""
    from app.models import User, Document, ProcessingJob, ExtractedEntity, OntologyMapping, TextSegment
    
    return {
        'db': db,
        'User': User,
        'Document': Document,
        'ProcessingJob': ProcessingJob,
        'ExtractedEntity': ExtractedEntity,
        'OntologyMapping': OntologyMapping,
        'TextSegment': TextSegment
    }

if __name__ == '__main__':
    # Set default environment variables if not set
    if not os.environ.get('FLASK_ENV'):
        os.environ['FLASK_ENV'] = 'development'
    
    if not os.environ.get('FLASK_APP'):
        os.environ['FLASK_APP'] = 'run.py'
    
    app.run(debug=True, host='0.0.0.0', port=5000)
