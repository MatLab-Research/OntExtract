from flask import Blueprint, render_template, request, jsonify
from flask_login import login_required, current_user
from sqlalchemy import func
from app import db
from app.models.document import Document
from app.models.processing_job import ProcessingJob

processing_bp = Blueprint('processing', __name__)

@processing_bp.route('/')
@login_required
def processing_home():
    """Processing pipeline home page"""
    # Aggregate document stats
    doc_total = db.session.query(func.count(Document.id)).scalar() or 0
    doc_uploaded = db.session.query(func.count(Document.id)).filter(Document.status == 'uploaded').scalar() or 0
    doc_processing = db.session.query(func.count(Document.id)).filter(Document.status == 'processing').scalar() or 0
    doc_completed = db.session.query(func.count(Document.id)).filter(Document.status == 'completed').scalar() or 0
    doc_error = db.session.query(func.count(Document.id)).filter(Document.status == 'error').scalar() or 0

    # Aggregate job stats
    job_total = db.session.query(func.count(ProcessingJob.id)).scalar() or 0
    job_running = db.session.query(func.count(ProcessingJob.id)).filter(getattr(ProcessingJob, 'status') == 'running').scalar() or 0
    job_pending = db.session.query(func.count(ProcessingJob.id)).filter(getattr(ProcessingJob, 'status') == 'pending').scalar() or 0
    job_completed = db.session.query(func.count(ProcessingJob.id)).filter(getattr(ProcessingJob, 'status') == 'completed').scalar() or 0
    job_failed = db.session.query(func.count(ProcessingJob.id)).filter(getattr(ProcessingJob, 'status') == 'failed').scalar() or 0

    stats = {
        'documents': {
            'total': doc_total,
            'uploaded': doc_uploaded,
            'processing': doc_processing,
            'completed': doc_completed,
            'error': doc_error,
        },
        'jobs': {
            'total': job_total,
            'pending': job_pending,
            'running': job_running,
            'completed': job_completed,
            'failed': job_failed,
        }
    }

    recent_documents = (
        db.session.query(Document)
        .order_by(Document.created_at.desc())
        .limit(10)
        .all()
    )
    recent_jobs = (
        db.session.query(ProcessingJob)
        .order_by(ProcessingJob.created_at.desc())
        .limit(10)
        .all()
    )

    return render_template('processing/index.html', stats=stats, recent_documents=recent_documents, recent_jobs=recent_jobs)

@processing_bp.route('/jobs')
@login_required
def job_list():
    """List processing jobs"""
    jobs = (
        db.session.query(ProcessingJob)
        .order_by(ProcessingJob.created_at.desc())
        .limit(50)
        .all()
    )
    return render_template('processing/jobs.html', jobs=jobs)

@processing_bp.route('/start/<int:document_id>')
@login_required
def start_processing(document_id):
    """Start processing a document"""
    # Placeholder for now
    return jsonify({'message': 'Processing will be implemented in phase 2'})
