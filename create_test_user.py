#!/usr/bin/env python3
"""Create test user for OntExtract"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Set environment variables
os.environ['FLASK_APP'] = 'app'
os.environ['FLASK_ENV'] = 'development'

from run import app
from app import db
from app.models.user import User

def create_test_user():
    with app.app_context():
        # Check if user exists
        user = User.query.filter_by(username='chris').first()
        if user:
            print(f'User chris exists with id: {user.id}')
            # Update password
            user.set_password('octopus')
            db.session.commit()
            print('Password updated to: octopus')
        else:
            print('User chris does not exist - creating user')
            user = User(username='chris', email='chris@example.com')
            user.set_password('octopus')
            db.session.add(user)
            db.session.commit()
            print(f'User created with id: {user.id}')
            print('Username: chris')
            print('Password: octopus')

if __name__ == '__main__':
    create_test_user()