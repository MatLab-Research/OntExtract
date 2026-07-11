"""Upload page and backward-compatible redirects."""

from flask import redirect, render_template, request, url_for

from app.utils.auth_decorators import api_require_login_for_write, require_login_for_write

from . import upload_bp


@upload_bp.route('/')
@require_login_for_write
def unified():
    """
    Enhanced upload interface with CrossRef metadata extraction and provenance tracking.
    """
    return render_template('text_input/upload_enhanced.html')

@upload_bp.route('/redirect', methods=['GET'])
@api_require_login_for_write
def redirect_old_routes():
    """
    Redirect old upload routes to the unified interface.
    This ensures backward compatibility.
    """
    # Capture any query parameters
    experiment_id = request.args.get('experiment_id')
    
    # Determine which tab to open based on the referrer
    referrer = request.referrer or ''
    
    # Build redirect URL
    redirect_url = url_for('upload.unified')
    if experiment_id:
        redirect_url = f"{redirect_url}?experiment_id={experiment_id}"
    
    # You could add logic here to pre-select a tab based on the referrer
    # For example, if coming from references, open the reference tab

    return redirect(redirect_url)
