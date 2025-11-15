"""
Processing Status and Monitoring Routes

This module handles status monitoring and job tracking for processing operations.

Routes:
- GET /processing/                          - Processing home dashboard
- GET /processing/jobs                      - List processing operations
- GET /processing/api/processing/job/<id>/langextract-details - LangExtract job details
"""

from flask import render_template, jsonify
from sqlalchemy import func
import os
from app import db
from app.models.document import Document
from app.models.processing_job import ProcessingJob
from app.utils.auth_decorators import api_require_login_for_write

from . import processing_bp


@processing_bp.route('/')
def processing_home():
    """Processing pipeline home page - shows live experiment processing status"""
    from app.models.experiment_processing import ExperimentDocumentProcessing
    from app.models.experiment import Experiment
    from app.models.experiment_document import ExperimentDocument

    # Aggregate document stats (total documents in system)
    doc_total = db.session.query(func.count(Document.id)).scalar() or 0
    doc_uploaded = db.session.query(func.count(Document.id)).filter(Document.status == 'uploaded').scalar() or 0
    doc_processing = db.session.query(func.count(Document.id)).filter(Document.status == 'processing').scalar() or 0
    doc_completed = db.session.query(func.count(Document.id)).filter(Document.status == 'completed').scalar() or 0
    doc_error = db.session.query(func.count(Document.id)).filter(Document.status == 'error').scalar() or 0

    # Aggregate experiment processing stats (actual live processing operations)
    processing_total = db.session.query(func.count(ExperimentDocumentProcessing.id)).scalar() or 0
    processing_pending = db.session.query(func.count(ExperimentDocumentProcessing.id)).filter(ExperimentDocumentProcessing.status == 'pending').scalar() or 0
    processing_running = db.session.query(func.count(ExperimentDocumentProcessing.id)).filter(ExperimentDocumentProcessing.status == 'running').scalar() or 0
    processing_completed = db.session.query(func.count(ExperimentDocumentProcessing.id)).filter(ExperimentDocumentProcessing.status == 'completed').scalar() or 0
    processing_failed = db.session.query(func.count(ExperimentDocumentProcessing.id)).filter(ExperimentDocumentProcessing.status == 'failed').scalar() or 0

    stats = {
        'documents': {
            'total': doc_total,
            'uploaded': doc_uploaded,
            'processing': doc_processing,
            'completed': doc_completed,
            'error': doc_error,
        },
        'processing_operations': {
            'total': processing_total,
            'pending': processing_pending,
            'running': processing_running,
            'completed': processing_completed,
            'failed': processing_failed,
        }
    }

    # Recent documents from experiments
    recent_documents = (
        db.session.query(Document)
        .join(ExperimentDocument, Document.id == ExperimentDocument.document_id)
        .order_by(ExperimentDocument.added_at.desc())
        .limit(10)
        .all()
    )

    # Recent processing operations instead of old processing jobs
    recent_processing = (
        db.session.query(ExperimentDocumentProcessing)
        .join(ExperimentDocument, ExperimentDocumentProcessing.experiment_document_id == ExperimentDocument.id)
        .join(Document, ExperimentDocument.document_id == Document.id)
        .join(Experiment, ExperimentDocument.experiment_id == Experiment.id)
        .order_by(ExperimentDocumentProcessing.created_at.desc())
        .limit(10)
        .all()
    )

    return render_template('processing/index.html', stats=stats, recent_documents=recent_documents, recent_processing=recent_processing)


@processing_bp.route('/jobs')
def job_list():
    """List processing operations - public view"""
    from app.models.experiment_processing import ExperimentDocumentProcessing
    from app.models.experiment import Experiment
    from app.models.experiment_document import ExperimentDocument

    # Get processing operations from experiments
    processing_operations = (
        db.session.query(ExperimentDocumentProcessing)
        .join(ExperimentDocument, ExperimentDocumentProcessing.experiment_document_id == ExperimentDocument.id)
        .join(Document, ExperimentDocument.document_id == Document.id)
        .join(Experiment, ExperimentDocument.experiment_id == Experiment.id)
        .order_by(ExperimentDocumentProcessing.created_at.desc())
        .limit(100)
        .all()
    )

    # Also get legacy processing jobs if any exist
    legacy_jobs = (
        db.session.query(ProcessingJob)
        .order_by(ProcessingJob.created_at.desc())
        .limit(50)
        .all()
    )

    return render_template('processing/jobs.html', processing_operations=processing_operations, legacy_jobs=legacy_jobs)


@processing_bp.route('/api/processing/job/<int:job_id>/langextract-details')
@api_require_login_for_write
def get_langextract_details(job_id):
    """Get detailed LangExtract analysis results for a specific job"""
    try:
        # Get the processing job
        job = ProcessingJob.query.get_or_404(job_id)

        # Verify this is a LangExtract job
        if job.job_type != 'langextract_segmentation':
            return jsonify({
                'success': False,
                'error': 'This endpoint is only for LangExtract segmentation jobs'
            }), 400

        # Get job parameters and results
        params = job.get_parameters()
        results = job.get_result_data()

        # Extract key information
        response_data = {
            'success': True,
            'job_info': {
                'job_id': job.id,
                'document_id': job.document_id,
                'status': job.status,
                'created_at': job.created_at.isoformat() if job.created_at else None,
                'processing_time': job.processing_time
            },
            'parameters': params,
            'results': results
        }

        # Try to load detailed analysis data from temp files if available
        analysis_id = params.get('langextract_analysis_id') or results.get('analysis_id')
        if analysis_id:
            try:
                import tempfile
                import json

                # Look for detailed analysis files
                temp_dir = tempfile.gettempdir()
                analysis_file = os.path.join(temp_dir, f"langextract_analysis_{analysis_id}.json")

                if os.path.exists(analysis_file):
                    with open(analysis_file, 'r') as f:
                        detailed_analysis = json.load(f)

                    response_data['detailed_analysis'] = {
                        'key_concepts': detailed_analysis.get('key_concepts', []),
                        'temporal_markers': detailed_analysis.get('temporal_markers', []),
                        'domain_indicators': detailed_analysis.get('domain_indicators', []),
                        'structural_segments': detailed_analysis.get('structural_segments', []),
                        'semantic_segments': detailed_analysis.get('semantic_segments', []),
                        'analysis_metadata': detailed_analysis.get('metadata', {})
                    }
            except Exception as e:
                # Detailed analysis loading failed, but basic job info is still available
                response_data['detailed_analysis_error'] = str(e)

        # Add summary statistics
        response_data['summary'] = {
            'key_concepts_extracted': params.get('key_concepts_extracted', 0),
            'temporal_markers_found': params.get('temporal_markers_found', 0),
            'domain_indicators_identified': params.get('domain_indicators_identified', 0),
            'segments_created': params.get('segments_created', 0),
            'character_level_positions': params.get('character_level_positions', True),
            'prov_o_tracking_complete': params.get('prov_o_tracking_complete', False)
        }

        return jsonify(response_data)

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
