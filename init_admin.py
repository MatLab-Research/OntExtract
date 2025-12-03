#!/usr/bin/env python3
"""
Initialize Admin User for OntExtract

This script creates an admin user for OntExtract.
Can be run interactively or with environment variables.

Usage:
    # Interactive mode
    python init_admin.py

    # Environment variable mode (for Docker)
    ADMIN_USERNAME=admin ADMIN_PASSWORD=changeme ADMIN_EMAIL=admin@example.com python init_admin.py

    # Docker exec
    docker-compose exec web python init_admin.py
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from app import create_app, db
from app.models.user import User


def get_input(prompt, default=None, required=True):
    """Get user input with optional default"""
    if default:
        prompt = f"{prompt} [{default}]: "
    else:
        prompt = f"{prompt}: "

    value = input(prompt).strip()

    if not value and default:
        return default

    if not value and required:
        print("This field is required!")
        return get_input(prompt.rstrip(': '), default, required)

    return value


def create_admin_user(username, email, password, first_name=None, last_name=None):
    """Create an admin user"""
    app = create_app()

    with app.app_context():
        # Check if user already exists
        existing_user = User.query.filter(
            (User.username == username) | (User.email == email)
        ).first()

        if existing_user:
            if existing_user.username == username:
                print(f"✗ Username '{username}' already exists")
            if existing_user.email == email:
                print(f"✗ Email '{email}' already exists")

            # Offer to make existing user admin
            if existing_user.is_admin:
                print(f"✓ User '{existing_user.username}' is already an admin")
                return True
            else:
                response = input(f"Make existing user '{existing_user.username}' an admin? (y/n): ")
                if response.lower() == 'y':
                    existing_user.is_admin = True
                    db.session.commit()
                    print(f"✓ User '{existing_user.username}' is now an admin")
                    return True
                else:
                    return False

        # Create new admin user
        try:
            user = User(
                username=username,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
                is_admin=True,
                account_status='active',
                email_verified=True
            )

            db.session.add(user)
            db.session.commit()

            print(f"✓ Admin user created successfully!")
            print(f"  Username: {username}")
            print(f"  Email: {email}")
            print(f"  Admin: Yes")
            return True

        except Exception as e:
            db.session.rollback()
            print(f"✗ Error creating admin user: {e}")
            return False


def main():
    """Main entry point"""
    print("=" * 60)
    print("OntExtract - Admin User Setup")
    print("=" * 60)

    # Check for environment variables first (for Docker)
    username = os.environ.get('ADMIN_USERNAME')
    password = os.environ.get('ADMIN_PASSWORD')
    email = os.environ.get('ADMIN_EMAIL')
    first_name = os.environ.get('ADMIN_FIRST_NAME')
    last_name = os.environ.get('ADMIN_LAST_NAME')

    # If environment variables not set, prompt interactively
    if not all([username, password, email]):
        print("\nCreate a new admin user or upgrade existing user to admin.\n")

        username = get_input("Username", default="admin")
        email = get_input("Email", default="admin@ontextract.local")
        password = get_input("Password", required=True)

        if len(password) < 6:
            print("✗ Password must be at least 6 characters long")
            sys.exit(1)

        confirm = get_input("Confirm password", required=True)
        if password != confirm:
            print("✗ Passwords do not match")
            sys.exit(1)

        first_name = get_input("First name (optional)", required=False)
        last_name = get_input("Last name (optional)", required=False)
    else:
        print("\nUsing environment variables for admin creation...\n")

    # Create the admin user
    success = create_admin_user(username, email, password, first_name, last_name)

    print("=" * 60)

    if success:
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == '__main__':
    main()
