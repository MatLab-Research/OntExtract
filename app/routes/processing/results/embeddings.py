"""Embedding result views."""

from flask import render_template

from app.models.document import Document
from app.models.processing_job import ProcessingJob
from app.services.processing_results import (
    append_experiment_jobs,
    get_document_family_ids,
)

from .. import processing_bp


@processing_bp.route('/document/<string:document_uuid>/results/embeddings', methods=['GET'])
def view_embeddings_results(document_uuid):
    """View embeddings results for a document (supports both manual and experiment processing)"""
    try:
        document = Document.query.filter_by(uuid=document_uuid).first_or_404()

        # Get all embedding jobs for this document (including processing versions)
        jobs = ProcessingJob.query.filter_by(document_id=document.id, job_type='generate_embeddings').all()

        # Also check for jobs in processing versions
        all_potential_jobs = ProcessingJob.query.filter(
            ProcessingJob.document_id != document.id,
            ProcessingJob.job_type == 'generate_embeddings'
        ).all()

        for job in all_potential_jobs:
            params = job.get_parameters()
            if params.get('original_document_id') == document.id:
                jobs.append(job)

        append_experiment_jobs(jobs, [document.id], 'embeddings')

        # Get embeddings from multiple sources
        all_version_ids = get_document_family_ids(document)

        # Get embeddings from ProcessingArtifact table (unified storage)
        embeddings = []
        from app.models.experiment_processing import ProcessingArtifact

        artifact_embeddings = ProcessingArtifact.query.filter(
            ProcessingArtifact.document_id.in_(all_version_ids),
            ProcessingArtifact.artifact_type == 'embedding_vector'
        ).order_by(ProcessingArtifact.artifact_index).all()

        for emb in artifact_embeddings:
            content = emb.get_content()
            metadata = emb.get_metadata() or {}
            embeddings.append({
                'document_id': emb.document_id,
                'index': emb.artifact_index,
                'level': 'document' if emb.artifact_index == -1 else 'segment',
                'method': metadata.get('method', 'unknown'),
                'model': content.get('model', metadata.get('model', 'unknown')),
                'dimensions': metadata.get('dimensions', len(content.get('vector', []))),
                'text': content.get('text', '')[:500],  # Truncate for display
                'vector': content.get('vector', []),
                'source': 'artifact',
                # Period-aware metadata
                'period_category': metadata.get('period_category'),
                'document_year': metadata.get('document_year'),
                'selection_reason': metadata.get('selection_reason'),
                'selection_confidence': metadata.get('selection_confidence'),
                # Extended period-aware metadata
                'model_full': metadata.get('model_full'),
                'model_description': metadata.get('model_description'),
                'expected_dimension': metadata.get('expected_dimension'),
                'handles_archaic': metadata.get('handles_archaic'),
                'era': metadata.get('era'),
                'intended_model': metadata.get('intended_model'),
                'fallback_used': metadata.get('fallback_used', False)
            })

        # Compute statistics
        total_embeddings = len(embeddings)
        document_level = [e for e in embeddings if e['level'] == 'document']
        segment_level = [e for e in embeddings if e['level'] == 'segment']

        # Get consistent metadata from first embedding
        first_emb = embeddings[0] if embeddings else {}

        # Check if any embedding is period-aware
        period_aware_emb = next((e for e in embeddings if e.get('period_category')), None)

        from flask import render_template
        return render_template('processing/embeddings_results.html',
                             document=document,
                             jobs=jobs,
                             embeddings=embeddings,
                             total_embeddings=total_embeddings,
                             document_level_count=len(document_level),
                             segment_level_count=len(segment_level),
                             method=first_emb.get('method', 'N/A'),
                             model=first_emb.get('model', 'N/A'),
                             dimensions=first_emb.get('dimensions', 'N/A'),
                             # Period-aware info
                             is_period_aware=period_aware_emb is not None,
                             period_category=period_aware_emb.get('period_category') if period_aware_emb else None,
                             document_year=period_aware_emb.get('document_year') if period_aware_emb else None,
                             selection_reason=period_aware_emb.get('selection_reason') if period_aware_emb else None,
                             selection_confidence=period_aware_emb.get('selection_confidence') if period_aware_emb else None,
                             # Extended period-aware info
                             model_full=period_aware_emb.get('model_full') if period_aware_emb else None,
                             model_description=period_aware_emb.get('model_description') if period_aware_emb else None,
                             expected_dimension=period_aware_emb.get('expected_dimension') if period_aware_emb else None,
                             handles_archaic=period_aware_emb.get('handles_archaic') if period_aware_emb else None,
                             era=period_aware_emb.get('era') if period_aware_emb else None,
                             intended_model=period_aware_emb.get('intended_model') if period_aware_emb else None,
                             fallback_used=period_aware_emb.get('fallback_used', False) if period_aware_emb else False)

    except Exception as e:
        from flask import render_template, abort
        from werkzeug.exceptions import HTTPException
        # Re-raise 404 and other HTTP exceptions properly
        if isinstance(e, HTTPException):
            raise
        # For non-HTTP exceptions, show error page
        return render_template('processing/error.html',
                             document=None,
                             error=str(e)), 500
