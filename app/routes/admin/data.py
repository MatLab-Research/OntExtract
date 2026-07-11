"""Administrative data-management routes."""

from datetime import datetime, timedelta

from flask import jsonify, render_template

from app import db
from app.utils.auth_decorators import admin_required

from . import admin_bp
from .health import check_disk_space


@admin_bp.route('/admin/data')
@admin_required
def data_management():
    """View data statistics and management options"""
    from app.models.experiment import Experiment
    from app.models.document import Document
    from app.models.processing_job import ProcessingJob
    from app.models.term import Term

    # Experiment stats
    experiment_stats = {
        'total': Experiment.query.count(),
        'draft': Experiment.query.filter_by(status='draft').count(),
        'running': Experiment.query.filter_by(status='running').count(),
        'completed': Experiment.query.filter_by(status='completed').count(),
        'error': Experiment.query.filter_by(status='error').count()
    }

    # Document stats
    document_stats = {
        'total': Document.query.count(),
        'uploaded': Document.query.filter_by(status='uploaded').count(),
        'processing': Document.query.filter_by(status='processing').count(),
        'completed': Document.query.filter_by(status='completed').count(),
        'error': Document.query.filter_by(status='error').count(),
        'orphaned': Document.query.filter(
            ~Document.experiments.any()
        ).count()  # Documents not in any experiment
    }

    # Processing job stats
    job_stats = {
        'total': ProcessingJob.query.count(),
        'pending': ProcessingJob.query.filter_by(status='pending').count(),
        'running': ProcessingJob.query.filter_by(status='running').count(),
        'completed': ProcessingJob.query.filter_by(status='completed').count(),
        'failed': ProcessingJob.query.filter_by(status='failed').count()
    }

    # Term stats
    term_stats = {
        'total': Term.query.count()
    }

    # Storage stats
    storage_stats = check_disk_space()

    return render_template('admin/data.html',
                         experiment_stats=experiment_stats,
                         document_stats=document_stats,
                         job_stats=job_stats,
                         term_stats=term_stats,
                         storage_stats=storage_stats,
                         active_page='data',
                         page_title='Data Management')

@admin_bp.route('/admin/api/data/cleanup-jobs', methods=['POST'])
@admin_required
def cleanup_failed_jobs():
    """Delete all failed processing jobs"""
    from app.models.processing_job import ProcessingJob

    try:
        count = ProcessingJob.query.filter_by(status='failed').delete()
        db.session.commit()
        return jsonify({'success': True, 'deleted': count})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@admin_bp.route('/admin/api/data/cleanup-drafts', methods=['POST'])
@admin_required
def cleanup_draft_experiments():
    """Delete all draft experiments older than 30 days"""
    from app.models.experiment import Experiment

    try:
        cutoff = datetime.utcnow() - timedelta(days=30)
        count = Experiment.query.filter(
            Experiment.status == 'draft',
            Experiment.created_at < cutoff
        ).delete()
        db.session.commit()
        return jsonify({'success': True, 'deleted': count})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
