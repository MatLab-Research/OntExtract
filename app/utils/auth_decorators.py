"""Authentication decorators for AJAX-aware requests."""

from functools import wraps
from flask import request, jsonify
from flask_login import current_user


def ajax_login_required(f):
    """
    Login required decorator that returns JSON for AJAX requests instead of HTML redirects.
    
    For regular requests: behaves like @login_required (redirects to login page)
    For AJAX requests: returns JSON error response with 401 status
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            # Check if this is an AJAX request
            if request.is_json or request.headers.get('Content-Type') == 'application/json':
                return jsonify({
                    'success': False,
                    'error': 'Authentication required',
                    'redirect_to_login': True
                }), 401
            else:
                # For regular requests, use standard Flask-Login behavior
                from flask_login import login_required
                return login_required(f)(*args, **kwargs)
        
        return f(*args, **kwargs)
    
    return decorated_function