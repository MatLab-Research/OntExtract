"""Temporal extraction result views."""

from flask import render_template

from app.models.document import Document
from app.models.processing_job import ProcessingJob
from app.services.processing_results import (
    append_experiment_jobs,
    get_document_family_ids,
)

from .. import processing_bp


@processing_bp.route('/document/<string:document_uuid>/results/temporal', methods=['GET'])
def view_temporal_results(document_uuid):
    """View temporal extraction results for a document (supports both manual and experiment processing)"""
    try:
        document = Document.query.filter_by(uuid=document_uuid).first_or_404()

        # Get temporal extraction jobs from all versions
        all_version_ids = get_document_family_ids(document)

        # Get temporal extraction jobs from ProcessingJob (manual processing)
        jobs = ProcessingJob.query.filter(
            ProcessingJob.document_id.in_(all_version_ids),
            ProcessingJob.job_type == 'temporal_extraction'
        ).order_by(ProcessingJob.created_at.desc()).all()

        append_experiment_jobs(jobs, all_version_ids, 'temporal')

        # Get temporal expressions from ProcessingArtifact table
        # This is the unified storage for both orchestrated and manual processing
        temporal_expressions = []
        from app.models.experiment_processing import ProcessingArtifact

        artifacts = ProcessingArtifact.query.filter(
            ProcessingArtifact.document_id.in_(all_version_ids),
            ProcessingArtifact.artifact_type == 'temporal_marker'
        ).order_by(ProcessingArtifact.artifact_index).all()

        for artifact in artifacts:
            content = artifact.get_content()
            metadata = artifact.get_metadata()

            # Handle both dict and string content
            if isinstance(content, str):
                expr_text = content
                expr_type = 'UNKNOWN'
                normalized = None
                confidence = 0.75
            else:
                expr_text = content.get('text', '')
                expr_type = content.get('type', 'UNKNOWN')
                normalized = content.get('normalized')
                confidence = content.get('confidence', 0.75)

            # Get position from content first, fall back to metadata
            start_char = content.get('start') if isinstance(content, dict) else None
            end_char = content.get('end') if isinstance(content, dict) else None
            if start_char is None and isinstance(metadata, dict):
                start_char = metadata.get('start_char')
                end_char = metadata.get('end_char')

            temporal_expressions.append({
                'text': expr_text,
                'type': expr_type,
                'normalized': normalized,
                'confidence': confidence,
                'start_char': start_char,
                'end_char': end_char,
                'method': metadata.get('method', 'spacy_ner_plus_regex') if isinstance(metadata, dict) else 'spacy_ner_plus_regex',
                'context': content.get('context', '') if isinstance(content, dict) else '',
                'source': 'spacy'
            })

        # Group expressions by type
        expressions_by_type = {}
        for expr in temporal_expressions:
            expr_type = expr['type']
            if expr_type not in expressions_by_type:
                expressions_by_type[expr_type] = []
            expressions_by_type[expr_type].append(expr)

        from flask import render_template
        return render_template('processing/temporal_results.html',
                             document=document,
                             jobs=jobs,
                             temporal_expressions=temporal_expressions,
                             expressions_by_type=expressions_by_type,
                             total_expressions=len(temporal_expressions))

    except Exception as e:
        from flask import render_template
        return render_template('processing/error.html',
                             document=document,
                             error=str(e)), 500
