"""Entity extraction result views."""

from flask import render_template

from app.models.document import Document
from app.models.processing_job import ProcessingJob
from app.services.processing_results import (
    append_experiment_jobs,
    get_document_family_ids,
)

from .. import processing_bp


@processing_bp.route('/document/<string:document_uuid>/results/entities', methods=['GET'])
def view_entities_results(document_uuid):
    """View entity extraction results for a document (supports both manual and experiment processing)"""
    try:
        document = Document.query.filter_by(uuid=document_uuid).first_or_404()

        # Get all entity extraction jobs
        jobs = ProcessingJob.query.filter_by(
            document_id=document.id,
            job_type='extract_entities'
        ).order_by(ProcessingJob.created_at.desc()).all()

        append_experiment_jobs(jobs, [document.id], 'entities')

        # Get entities from multiple sources
        all_version_ids = get_document_family_ids(document)

        # Get entities from ProcessingArtifact table (unified storage)
        entities = []
        from app.models.experiment_processing import ProcessingArtifact

        artifacts = ProcessingArtifact.query.filter(
            ProcessingArtifact.document_id.in_(all_version_ids),
            ProcessingArtifact.artifact_type == 'extracted_entity'
        ).order_by(ProcessingArtifact.artifact_index).all()

        for artifact in artifacts:
            content_data = artifact.get_content()
            # Handle field naming from processing_tools.py: entity, type, start, end
            entity_text = content_data.get('entity', content_data.get('text', ''))
            entity_type = content_data.get('type', content_data.get('entity_type', 'UNKNOWN'))
            start_pos = content_data.get('start', content_data.get('start_char'))
            end_pos = content_data.get('end', content_data.get('end_char'))
            entities.append({
                'entity_text': entity_text,
                'text': entity_text,
                'entity_type': entity_type,
                'start_position': start_pos,
                'end_position': end_pos,
                'confidence_score': content_data.get('confidence', 0),
                'confidence': content_data.get('confidence', 0),
                'context': content_data.get('context', ''),
                'source': 'artifact'
            })

        # Group entities by type
        entities_by_type = {}
        for entity in entities:
            entity_type = entity.get('entity_type', 'UNKNOWN')
            if entity_type not in entities_by_type:
                entities_by_type[entity_type] = []
            entities_by_type[entity_type].append(entity)

        # Prepare displaCy-style data
        displacy_data = {
            'text': document.content[:5000] if document.content else '',  # Limit to first 5000 chars
            'ents': []
        }

        for entity in entities:
            start_pos = entity.get('start_position')
            end_pos = entity.get('end_position')
            if start_pos is not None and end_pos is not None:
                displacy_data['ents'].append({
                    'start': start_pos,
                    'end': end_pos,
                    'label': entity.get('entity_type', 'UNKNOWN')
                })

        from flask import render_template
        return render_template('processing/entities_results.html',
                             document=document,
                             jobs=jobs,
                             entities=entities,
                             entities_by_type=entities_by_type,
                             displacy_data=displacy_data,
                             total_entities=len(entities))

    except Exception as e:
        from flask import render_template
        return render_template('processing/error.html',
                             document=document,
                             error=str(e)), 500
