"""Definition extraction result views."""

from flask import render_template

from app.models.document import Document
from app.models.processing_job import ProcessingJob
from app.services.processing_results import (
    append_experiment_jobs,
    get_document_family_ids,
)

from .. import processing_bp


@processing_bp.route('/document/<string:document_uuid>/results/definitions', methods=['GET'])
def view_definitions_results(document_uuid):
    """View definition extraction results for a document (supports both manual and experiment processing)"""
    try:
        document = Document.query.filter_by(uuid=document_uuid).first_or_404()

        # Get definition extraction jobs from all versions
        all_version_ids = get_document_family_ids(document)

        # Get definition extraction jobs from ProcessingJob (manual processing)
        jobs = ProcessingJob.query.filter(
            ProcessingJob.document_id.in_(all_version_ids),
            ProcessingJob.job_type == 'definition_extraction'
        ).order_by(ProcessingJob.created_at.desc()).all()

        append_experiment_jobs(jobs, all_version_ids, 'definitions')

        # Get definitions from ProcessingArtifact table (unified storage)
        definitions = []
        from app.models.experiment_processing import ProcessingArtifact

        artifacts = ProcessingArtifact.query.filter(
            ProcessingArtifact.document_id.in_(all_version_ids),
            ProcessingArtifact.artifact_type == 'term_definition'
        ).order_by(ProcessingArtifact.artifact_index).all()

        for artifact in artifacts:
            content = artifact.get_content()
            metadata = artifact.get_metadata()
            definitions.append({
                'term': content.get('term', ''),
                'definition': content.get('definition', ''),
                'pattern': content.get('pattern', 'unknown'),
                'confidence': content.get('confidence', 0),
                'sentence': content.get('sentence', ''),
                'start_char': metadata.get('start_char'),
                'end_char': metadata.get('end_char'),
                'method': metadata.get('method', 'artifact'),
                'source': 'artifact'
            })

        # Group definitions by pattern type
        definitions_by_pattern = {}
        for defn in definitions:
            pattern = defn.get('pattern', 'unknown')
            if pattern not in definitions_by_pattern:
                definitions_by_pattern[pattern] = []
            definitions_by_pattern[pattern].append(defn)

        from flask import render_template
        return render_template('processing/definitions_results.html',
                             document=document,
                             jobs=jobs,
                             definitions=definitions,
                             definitions_by_pattern=definitions_by_pattern,
                             total_definitions=len(definitions))

    except Exception as e:
        from flask import render_template
        return render_template('processing/error.html',
                             document=document,
                             error=str(e)), 500
