from flask import Blueprint, render_template, request, jsonify
from flask_login import current_user
from app.utils.auth_decorators import api_require_login_for_write
from app.models.experiment import Experiment
from app.models.processing_job import ProcessingJob
from sqlalchemy import desc

results_bp = Blueprint('results', __name__)

@results_bp.route('/')
@api_require_login_for_write
def results_home():
    """Results dashboard showing recent experiments and processing jobs"""
    # Get recent experiments
    recent_experiments = Experiment.query.order_by(desc(Experiment.created_at)).limit(10).all()

    # Get recent processing jobs
    recent_jobs = ProcessingJob.query.order_by(desc(ProcessingJob.created_at)).limit(10).all()

    # Calculate summary statistics
    total_experiments = Experiment.query.count()
    completed_experiments = Experiment.query.filter_by(status='completed').count()
    total_jobs = ProcessingJob.query.count()
    completed_jobs = ProcessingJob.query.filter_by(status='completed').count()

    return render_template('results/index.html',
                         recent_experiments=recent_experiments,
                         recent_jobs=recent_jobs,
                         total_experiments=total_experiments,
                         completed_experiments=completed_experiments,
                         total_jobs=total_jobs,
                         completed_jobs=completed_jobs)

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
