"""Processing job listing, status, and diagnostic routes."""

import os

from flask import jsonify, render_template
from sqlalchemy import func

from app import db
from app.models.document import Document
from app.models.processing_job import ProcessingJob
from app.utils.auth_decorators import api_require_login_for_write

from . import processing_bp


@processing_bp.route('/')
def processing_home():
    """Show live document and experiment processing status."""
    from app.models.experiment import Experiment
    from app.models.experiment_document import ExperimentDocument
    from app.models.experiment_processing import ExperimentDocumentProcessing

    stats = {
        'documents': {
            'total': db.session.query(func.count(Document.id)).scalar() or 0,
            'uploaded': db.session.query(func.count(Document.id)).filter(
                Document.status == 'uploaded'
            ).scalar() or 0,
            'processing': db.session.query(func.count(Document.id)).filter(
                Document.status == 'processing'
            ).scalar() or 0,
            'completed': db.session.query(func.count(Document.id)).filter(
                Document.status == 'completed'
            ).scalar() or 0,
            'error': db.session.query(func.count(Document.id)).filter(
                Document.status == 'error'
            ).scalar() or 0,
        },
        'processing_operations': {
            'total': db.session.query(
                func.count(ExperimentDocumentProcessing.id)
            ).scalar() or 0,
            'pending': db.session.query(
                func.count(ExperimentDocumentProcessing.id)
            ).filter(ExperimentDocumentProcessing.status == 'pending').scalar() or 0,
            'running': db.session.query(
                func.count(ExperimentDocumentProcessing.id)
            ).filter(ExperimentDocumentProcessing.status == 'running').scalar() or 0,
            'completed': db.session.query(
                func.count(ExperimentDocumentProcessing.id)
            ).filter(ExperimentDocumentProcessing.status == 'completed').scalar() or 0,
            'failed': db.session.query(
                func.count(ExperimentDocumentProcessing.id)
            ).filter(ExperimentDocumentProcessing.status == 'failed').scalar() or 0,
        },
    }

    recent_documents = (
        db.session.query(Document)
        .join(ExperimentDocument, Document.id == ExperimentDocument.document_id)
        .order_by(ExperimentDocument.added_at.desc())
        .limit(10)
        .all()
    )
    recent_processing = (
        db.session.query(ExperimentDocumentProcessing)
        .join(
            ExperimentDocument,
            ExperimentDocumentProcessing.experiment_document_id
            == ExperimentDocument.id,
        )
        .join(Document, ExperimentDocument.document_id == Document.id)
        .join(Experiment, ExperimentDocument.experiment_id == Experiment.id)
        .order_by(ExperimentDocumentProcessing.created_at.desc())
        .limit(10)
        .all()
    )

    return render_template(
        'processing/index.html',
        stats=stats,
        recent_documents=recent_documents,
        recent_processing=recent_processing,
    )


@processing_bp.route('/jobs')
def job_list():
    """List processing operations - public view"""
    # Import experiment models
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

@processing_bp.route('/job/<int:job_id>/status', methods=['GET'])
def get_job_status(job_id):
    """Get status and progress of a specific processing job"""
    try:
        job = ProcessingJob.query.get_or_404(job_id)

        params = job.get_parameters()
        result_data = job.get_result_data()

        response = {
            'success': True,
            'job_id': job.id,
            'status': job.status,
            'created_at': job.created_at.isoformat() if job.created_at else None,
            'completed_at': job.completed_at.isoformat() if job.completed_at else None,
            'parameters': params,
            'result_data': result_data
        }

        # Add progress info if available
        if 'current_chunk' in params and 'total_chunks' in params:
            response['progress'] = {
                'current': params['current_chunk'],
                'total': params['total_chunks'],
                'message': params.get('progress_message', ''),
                'percentage': int((params['current_chunk'] / params['total_chunks']) * 100) if params['total_chunks'] > 0 else 0
            }

        return jsonify(response)

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@processing_bp.route('/document/<string:document_uuid>/processing-jobs', methods=['GET'])
def get_document_processing_jobs(document_uuid):
    """Get all processing jobs for a document"""
    try:
        document = Document.query.filter_by(uuid=document_uuid).first_or_404()

        # Get all processing jobs for this document in two ways:
        # 1. Jobs directly linked to this document (document_id = this doc's id)
        # 2. Jobs where parameters contain original_document_id = this document's id
        #    (these are jobs created for processing versions like embeddings)

        # First get direct jobs
        jobs = ProcessingJob.query.filter_by(document_id=document.id).all()

        # Then find indirect jobs (processing versions)
        # These have parameters.original_document_id = document.id
        all_potential_jobs = ProcessingJob.query.filter(
            ProcessingJob.document_id != document.id
        ).all()

        indirect_job_ids = []
        for job in all_potential_jobs:
            params = job.get_parameters()
            if params.get('original_document_id') == document.id:
                indirect_job_ids.append(job.id)
                jobs.append(job)

        # Sort by created_at desc (put None values last)
        jobs.sort(key=lambda j: (j.created_at is None, j.created_at), reverse=True)

        # Group jobs by type and method combination to find duplicates
        jobs_by_type = {}
        for job in jobs:
            params = job.get_parameters()

            # Extract method/descriptor based on job type
            method = 'default'
            if job.job_type in ['generate_embeddings', 'segment_document']:
                method = params.get('method', 'default')
            elif job.job_type == 'extract_entities':
                entity_types = params.get('entity_types', [])
                method = f"{len(entity_types)} types" if entity_types else 'default'
            elif job.job_type == 'analyze_metadata':
                method = 'auto'
            elif job.job_type == 'enhanced_processing':
                extract_terms = params.get('extract_terms', False)
                enrich_oed = params.get('enrich_with_oed', False)
                method = 'terms+OED' if extract_terms and enrich_oed else 'terms' if extract_terms else 'default'

            # Create unique key for this job type + method combination
            key = f"{job.job_type}:{method}"

            if key not in jobs_by_type:
                jobs_by_type[key] = {
                    'latest': job,
                    'method': method,
                    'all_jobs': []
                }
            jobs_by_type[key]['all_jobs'].append(job)

        # Build response with only latest job per type, but include count
        processing_operations = []
        for key, group in jobs_by_type.items():
            latest_job = group['latest']
            all_jobs = group['all_jobs']
            count = len(all_jobs)

            processing_operations.append({
                'id': latest_job.id,
                'processing_type': latest_job.job_type,
                'processing_method': group['method'],
                'status': latest_job.status,
                'created_at': latest_job.created_at.isoformat() if latest_job.created_at else None,
                'completed_at': latest_job.completed_at.isoformat() if latest_job.completed_at else None,
                'error_message': latest_job.error_message,
                'run_count': count,
                'has_history': count > 1,
                'all_job_ids': [j.id for j in all_jobs] if count > 1 else []
            })

        # Sort by latest created_at
        processing_operations.sort(key=lambda op: op['created_at'] if op['created_at'] else '', reverse=True)

        return jsonify({
            'success': True,
            'processing_operations': processing_operations
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
