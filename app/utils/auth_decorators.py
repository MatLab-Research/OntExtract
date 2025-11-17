from functools import wraps
from flask import jsonify, redirect, url_for, flash, request, abort
from flask_login import current_user

def write_login_required(f):
    """
    Decorator for routes that modify data (upload, process, create).
    Requires user to be authenticated.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            if request.is_json:
                return jsonify({'error': 'Authentication required for this action'}), 401
            flash('Please sign in to access this feature.', 'info')
            return redirect(url_for('auth.login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def ajax_write_login_required(f):
    """
    AJAX version of write_login_required.
    Returns JSON error instead of redirect.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return jsonify({
                'error': 'Authentication required',
                'message': 'Please sign in to perform this action.',
                'redirect': url_for('auth.login')
            }), 401
        return f(*args, **kwargs)
    return decorated_function

def ajax_login_required(f):
    """
    Existing AJAX login decorator for compatibility.
    Can be replaced with ajax_write_login_required where appropriate.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            return jsonify({
                'error': 'Authentication required',
                'message': 'Please sign in to continue.',
                'redirect': url_for('auth.login')
            }), 401
        return f(*args, **kwargs)
    return decorated_function

def public_with_auth_context(f):
    """
    Decorator for routes that are public but can show different content
    based on authentication status.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Route is accessible to everyone
        # current_user.is_authenticated can be checked within the route
        return f(*args, **kwargs)
    return decorated_function

# Simplified decorators for new auth strategy

def require_login_for_write(f):
    """
    Only require login for operations that write to database or call external APIs.
    For GET requests and read-only operations, allow public access.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Allow all GET requests without authentication
        if request.method == 'GET':
            return f(*args, **kwargs)
        
        # Require authentication for POST, PUT, DELETE, PATCH
        if not current_user.is_authenticated:
            if request.is_json:
                return jsonify({'error': 'Authentication required for this action'}), 401
            flash('Please sign in to perform this action.', 'info')
            return redirect(url_for('auth.login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def api_require_login_for_write(f):
    """
    API version - only require login for write operations.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Allow all GET requests without authentication
        if request.method == 'GET':
            return f(*args, **kwargs)

        # Require authentication for POST, PUT, DELETE, PATCH
        if not current_user.is_authenticated:
            return jsonify({
                'error': 'Authentication required',
                'message': 'Please sign in to perform this action.',
                'redirect': url_for('auth.login')
            }), 401
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    """
    Decorator that requires user to be an admin.
    Redirects to index with error flash for non-admins.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Please sign in to access admin features.', 'error')
            return redirect(url_for('auth.login', next=request.url))

        if not current_user.is_admin:
            flash('Admin access required.', 'error')
            abort(403)

        return f(*args, **kwargs)
    return decorated_function
