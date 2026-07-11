"""Processing dashboard and job-list pages."""

from flask import render_template

from .. import processing_bp
from . import processing_status_service


@processing_bp.route('/')
def processing_home():
    """Show live document and experiment processing status."""
    return render_template(
        'processing/index.html',
        **processing_status_service.get_dashboard_context(),
    )


@processing_bp.route('/jobs')
def job_list():
    """List current experiment operations and legacy jobs."""
    return render_template(
        'processing/jobs.html',
        **processing_status_service.get_job_list_context(),
    )
