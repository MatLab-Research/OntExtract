"""Semantic event creation and removal routes."""

from flask import render_template, request, jsonify, flash, redirect, url_for
from flask_login import current_user
from app.utils.auth_decorators import api_require_login_for_write
from app.services.base_service import ServiceError, ValidationError, NotFoundError
from app.dto.temporal_dto import (
    UpdateTemporalTermsDTO,
    FetchTemporalDataDTO
)
from pydantic import ValidationError as PydanticValidationError
from app.models import Experiment, Document
from app import db
import json
from .. import experiments_bp
from .context import logger


@experiments_bp.route('/<int:experiment_id>/save_semantic_event', methods=['POST'])
@api_require_login_for_write
def save_semantic_event(experiment_id):
    """
    Save a semantic event (transition marker) to experiment configuration

    Semantic events track important temporal transitions like:
    - Inflection points (major semantic shift)
    - Stable polysemy (multiple stable meanings)
    - Domain-specific networks
    - etc.
    """
    try:
        experiment = Experiment.query.filter_by(id=experiment_id).first()
        if not experiment:
            return jsonify({
                'success': False,
                'error': 'Experiment not found'
            }), 404

        # Get event data from request
        event_data = request.get_json()
        event_id = event_data.get('id')
        event_type = event_data.get('event_type')
        from_period = event_data.get('from_period')
        to_period = event_data.get('to_period')
        description = event_data.get('description')
        related_document_ids = event_data.get('related_document_ids', [])

        # Validation
        if not event_type or not from_period or not description:
            return jsonify({
                'success': False,
                'error': 'Missing required fields: event_type, from_period, description'
            }), 400

        # Get ontology metadata for this event type
        from app.services.local_ontology_service import get_ontology_service
        from datetime import datetime

        ontology = get_ontology_service()
        event_types = ontology.get_all_for_dropdown()

        # Find matching event type from ontology
        ontology_metadata = next(
            (et for et in event_types if et['value'] == event_type),
            None
        )

        # Get configuration
        config = json.loads(experiment.configuration) if experiment.configuration else {}
        semantic_events = config.get('semantic_events', [])

        # Get related documents
        related_documents = []
        if related_document_ids:
            documents = Document.query.filter(Document.id.in_(related_document_ids)).all()
            related_documents = [
                {
                    'id': doc.id,
                    'uuid': str(doc.uuid),
                    'title': doc.title or 'Untitled Document'
                }
                for doc in documents
            ]

        # Check if this is an update or new event
        existing_event = next((e for e in semantic_events if e.get('id') == event_id), None)
        is_update = existing_event is not None

        # Create/update event with full metadata
        event_obj = {
            'id': event_id,
            'event_type': event_type,
            'from_period': from_period,
            'to_period': to_period,
            'description': description,
            'related_documents': related_documents,
            # Ontology metadata
            'type_label': ontology_metadata['label'] if ontology_metadata else event_type.replace('_', ' ').title(),
            'type_uri': ontology_metadata['uri'] if ontology_metadata else None,
            'definition': ontology_metadata['definition'] if ontology_metadata else None,
            'citation': ontology_metadata['citation'] if ontology_metadata else None,
            'example': ontology_metadata['example'] if ontology_metadata else None,
            # Provenance metadata
            'created_by': existing_event.get('created_by') if is_update else current_user.id,
            'created_at': existing_event.get('created_at') if is_update else datetime.utcnow().isoformat(),
            'modified_by': current_user.id if is_update else None,
            'modified_at': datetime.utcnow().isoformat() if is_update else None
        }

        # Find and update or append
        existing_index = next((i for i, e in enumerate(semantic_events) if e.get('id') == event_id), None)
        if existing_index is not None:
            semantic_events[existing_index] = event_obj
        else:
            semantic_events.append(event_obj)

        # Save configuration
        config['semantic_events'] = semantic_events
        experiment.configuration = json.dumps(config)
        db.session.commit()

        # Record provenance
        from app.services.provenance_service import ProvenanceService

        ProvenanceService.track_semantic_event(
            event_type=event_type,
            experiment=experiment,
            user=current_user,
            event_metadata=event_obj,
            related_documents=related_documents,
            is_update=is_update
        )

        logger.info(f"Saved semantic event '{event_type}' for experiment {experiment_id}")

        return jsonify({
            'success': True,
            'semantic_events': semantic_events
        }), 200

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error saving semantic event for experiment {experiment_id}: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@experiments_bp.route('/<int:experiment_id>/remove_semantic_event', methods=['POST'])
@api_require_login_for_write
def remove_semantic_event(experiment_id):
    """
    Remove a semantic event from experiment configuration
    """
    try:
        experiment = Experiment.query.filter_by(id=experiment_id).first()
        if not experiment:
            return jsonify({
                'success': False,
                'error': 'Experiment not found'
            }), 404

        # Get event ID from request
        event_id = request.get_json().get('event_id')
        if not event_id:
            return jsonify({
                'success': False,
                'error': 'Missing event_id'
            }), 400

        # Get configuration
        config = json.loads(experiment.configuration) if experiment.configuration else {}
        semantic_events = config.get('semantic_events', [])

        # Find event before removing (for provenance)
        removed_event = next((e for e in semantic_events if e.get('id') == event_id), None)

        # Remove event
        semantic_events = [e for e in semantic_events if e.get('id') != event_id]

        # Save configuration
        config['semantic_events'] = semantic_events
        experiment.configuration = json.dumps(config)
        db.session.commit()

        # Record provenance
        if removed_event:
            from app.services.provenance_service import ProvenanceService

            ProvenanceService.track_semantic_event(
                event_type=removed_event.get('event_type', 'unknown'),
                experiment=experiment,
                user=current_user,
                event_metadata=removed_event,
                related_documents=None,
                is_deletion=True
            )

        logger.info(f"Removed semantic event {event_id} from experiment {experiment_id}")

        return jsonify({
            'success': True,
            'semantic_events': semantic_events
        }), 200

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error removing semantic event for experiment {experiment_id}: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
