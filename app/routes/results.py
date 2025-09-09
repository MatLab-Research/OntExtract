from flask import Blueprint, render_template, request, jsonify
from flask_login import current_user
from app.utils.auth_decorators import api_require_login_for_write

results_bp = Blueprint('results', __name__)

@results_bp.route('/')
@api_require_login_for_write
def results_home():
    """Results dashboard"""
    return render_template('results/index.html')

@results_bp.route('/reports')
@api_require_login_for_write
def reports():
    """View analysis reports and summaries"""
    # TODO: Implement reports dashboard
    return render_template('results/reports.html')


@results_bp.route('/job/<int:job_id>')
@api_require_login_for_write
def job_results(job_id):
    """Show results for a specific processing job"""
    # Placeholder for now
    return render_template('results/job_detail.html', job_id=job_id)
