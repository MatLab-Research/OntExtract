"""Enhanced processing result views."""

from flask import render_template

from app.models.document import Document
from app.models.processing_job import ProcessingJob
from app.services.processing_results import append_experiment_jobs

from .. import processing_bp


@processing_bp.route('/document/<string:document_uuid>/results/enhanced', methods=['GET'])
def view_enhanced_results(document_uuid):
    """View enhanced processing results for a document (supports both manual and experiment processing)"""
    try:
        document = Document.query.filter_by(uuid=document_uuid).first_or_404()

        # Get enhanced processing jobs
        jobs = ProcessingJob.query.filter_by(
            document_id=document.id,
            job_type='enhanced_processing'
        ).order_by(ProcessingJob.created_at.desc()).all()

        append_experiment_jobs(jobs, [document.id], 'enhanced_processing')

        # Note: Terms are standalone entities for semantic change analysis, not extracted from documents
        # They are created manually via /terms/add, not from document processing
        terms = []

        from flask import render_template
        return render_template('processing/enhanced_results.html',
                             document=document,
                             jobs=jobs,
                             terms=terms,
                             total_terms=len(terms))

    except Exception as e:
        from flask import render_template
        return render_template('processing/error.html',
                             document=document,
                             error=str(e)), 500
