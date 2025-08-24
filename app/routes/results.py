from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user

results_bp = Blueprint('results', __name__)

@results_bp.route('/')
@login_required
def results_home():
    """Results dashboard"""
    return render_template('results/index.html')

@results_bp.route('/reports')
@login_required
def reports():
    """View analysis reports and summaries"""
    # TODO: Implement reports dashboard
    return render_template('results/reports.html')


@results_bp.route('/job/<int:job_id>')
@login_required
def job_results(job_id):
    """Show results for a specific processing job"""
    # Placeholder for now
    return render_template('results/job_detail.html', job_id=job_id)
