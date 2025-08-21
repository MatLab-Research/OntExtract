"""
Unified upload route for all content types.
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app.models.experiment import Experiment

upload_bp = Blueprint('upload', __name__, url_prefix='/upload')

@upload_bp.route('/')
@login_required
def unified():
    """
    Unified upload interface for all content types:
    - Documents for analysis
    - References/citations
    - Pasted text
    - Dictionary entries
    """
    # Check if this is linked from an experiment
    experiment_id = request.args.get('experiment_id')
    experiment = None
    
    if experiment_id:
        experiment = Experiment.query.filter_by(
            id=experiment_id,
            user_id=current_user.id
        ).first()
    
    return render_template('upload/unified.html', experiment=experiment)

@upload_bp.route('/redirect', methods=['GET'])
@login_required
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
