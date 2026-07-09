"""Text cleanup result views."""

from flask import render_template

from app.models.document import Document
from app.models.processing_job import ProcessingJob
from app.services.inheritance_versioning_service import InheritanceVersioningService

from .. import processing_bp


@processing_bp.route('/document/<string:document_uuid>/results/clean-text', methods=['GET'])
def view_clean_text_results(document_uuid):
    """View text cleanup results for a document"""
    try:
        document = Document.query.filter_by(uuid=document_uuid).first_or_404()

        # Get clean text jobs
        jobs = ProcessingJob.query.filter_by(
            document_id=document.id,
            job_type='clean_text'
        ).order_by(ProcessingJob.created_at.desc()).all()

        from flask import render_template
        return render_template('processing/clean_text_results.html',
                             document=document,
                             jobs=jobs)

    except Exception as e:
        from flask import render_template
        return render_template('processing/error.html',
                             document=document,
                             error=str(e)), 500
