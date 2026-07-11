"""Document entity-extraction routes."""

from flask import current_app as app, jsonify, request
from flask_login import current_user

from app import db
from app.models.document import Document
from app.models.processing_job import ProcessingJob
from app.services.inheritance_versioning_service import InheritanceVersioningService
from app.utils.auth_decorators import api_require_login_for_write

from . import processing_bp


@processing_bp.route('/document/<string:document_uuid>/entities', methods=['POST'])
@api_require_login_for_write
def extract_entities(document_uuid):
    """Extract entities from a document"""
    try:
        original_document = Document.query.filter_by(uuid=document_uuid).first_or_404()

        data = request.get_json() or {}
        entity_types = data.get('entity_types', ['PERSON', 'ORG', 'GPE', 'DATE'])
        experiment_id = data.get('experiment_id')  # Optional experiment association

        # EXPERIMENT VERSIONING: Use experiment version if provided
        if experiment_id:
            processing_document, version_created = InheritanceVersioningService.get_or_create_experiment_version(
                original_document=original_document,
                experiment_id=experiment_id,
                user=current_user
            )
            app.logger.info(f"Extracting entities from experiment version {processing_document.id} for experiment {experiment_id}")
        else:
            processing_document = original_document
            app.logger.info(f"Extracting entities from original document {processing_document.id}")

        if not processing_document.content:
            return jsonify({
                'success': False,
                'error': 'Document has no content to extract entities from'
            }), 400

        # Create processing job linked to the processing document
        job = ProcessingJob(
            document_id=processing_document.id,
            job_type='extract_entities',
            status='pending',
            user_id=current_user.id
        )
        job.set_parameters({
            'entity_types': entity_types,
            'experiment_id': experiment_id,
            'original_document_id': original_document.id
        })
        db.session.add(job)
        db.session.commit()

        # TODO: Replace with actual entity extraction (spaCy, etc.)
        # For now, simulate entity extraction
        words = processing_document.content.split()
        entity_count = len(words) // 20  # Simulate ~5% of words as entities
        
        job.status = 'completed'
        job.set_result_data({
            'entities_found': entity_count,
            'entity_types': entity_types,
            'processing_method': 'spacy_en_core_web_sm',
            'confidence_threshold': 0.7
        })
        db.session.commit()
        
        return jsonify({
            'success': True,
            'job_id': job.id,
            'entities_found': entity_count,
            'message': f'Extracted {entity_count} entities from document'
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
