"""
Experiments Temporal Analysis Routes

This module handles temporal evolution analysis for experiments.

Routes:
- GET  /experiments/<id>/manage_temporal_terms    - Temporal term management UI
- POST /experiments/<id>/update_temporal_terms    - Update temporal terms and periods
- GET  /experiments/<id>/get_temporal_terms       - Get saved temporal terms
- POST /experiments/<id>/fetch_temporal_data      - Fetch temporal data for analysis

REFACTORED: Now uses TemporalService with DTO validation
"""

from flask import render_template, request, jsonify, flash, redirect, url_for
from flask_login import current_user
from app.utils.auth_decorators import api_require_login_for_write
from app.services.temporal_service import get_temporal_service
from app.services.base_service import ServiceError, ValidationError, NotFoundError
from app.dto.temporal_dto import (
    UpdateTemporalTermsDTO,
    FetchTemporalDataDTO
)
from pydantic import ValidationError as PydanticValidationError
import logging

from . import experiments_bp

logger = logging.getLogger(__name__)
temporal_service = get_temporal_service()


@experiments_bp.route('/<int:experiment_id>/manage_temporal_terms')
@api_require_login_for_write
def manage_temporal_terms(experiment_id):
    """
    Manage terms for temporal evolution experiment

    REFACTORED: Now uses TemporalService
    """
    try:
        # Get temporal UI data from service
        data = temporal_service.get_temporal_ui_data(experiment_id)

        # Get document date statistics for UI
        # Note: Using Document.publication_date as single source of truth
        from app.models import Document
        documents = Document.query.filter_by(experiment_id=experiment_id).all()

        docs_with_pub_dates = sum(1 for doc in documents if doc.publication_date)
        docs_with_any_dates = sum(1 for doc in documents if doc.publication_date or doc.created_at)

        data['document_count'] = len(documents)
        data['docs_with_pub_dates'] = docs_with_pub_dates
        data['docs_with_any_dates'] = docs_with_any_dates

        return render_template(
            'experiments/temporal_term_manager.html',
            experiment=data['experiment'],
            time_periods=data['time_periods'],
            terms=data['terms'],
            start_year=data['start_year'],
            end_year=data['end_year'],
            use_oed_periods=data['use_oed_periods'],
            oed_period_data=data['oed_period_data'],
            term_periods=data['term_periods'],
            orchestration_decisions=data['orchestration_decisions'],
            document_count=data['document_count'],
            docs_with_pub_dates=data['docs_with_pub_dates'],
            docs_with_any_dates=data['docs_with_any_dates'],
            period_documents=data['period_documents'],
            period_metadata=data['period_metadata'],
            semantic_events=data['semantic_events']
        )

    except ValidationError as e:
        # Business validation errors (wrong experiment type)
        flash(str(e), 'warning')
        return redirect(url_for('experiments.view', experiment_id=experiment_id))

    except NotFoundError as e:
        logger.warning(f"Experiment {experiment_id} not found: {e}")
        from flask import abort
        abort(404)

    except ServiceError as e:
        logger.error(f"Service error getting temporal UI data: {e}", exc_info=True)
        flash('Failed to load temporal term manager', 'danger')
        return redirect(url_for('experiments.view', experiment_id=experiment_id))


@experiments_bp.route('/<int:experiment_id>/update_temporal_terms', methods=['POST'])
@api_require_login_for_write
def update_temporal_terms(experiment_id):
    """
    Update terms and periods for a temporal evolution experiment

    REFACTORED: Now uses TemporalService with DTO validation
    """
    try:
        # Validate request data using DTO
        data = UpdateTemporalTermsDTO(**request.get_json())

        # Call service to update configuration
        temporal_service.update_temporal_configuration(
            experiment_id,
            terms=data.terms,
            periods=data.periods,
            temporal_data=data.temporal_data
        )

        return jsonify({
            'success': True,
            'message': 'Temporal terms updated successfully'
        }), 200

    except PydanticValidationError as e:
        # Validation errors from DTO
        logger.warning(f"Validation error updating temporal terms for experiment {experiment_id}: {e}")
        return jsonify({
            'success': False,
            'error': 'Validation failed',
            'details': e.errors()
        }), 400

    except NotFoundError as e:
        logger.warning(f"Experiment {experiment_id} not found: {e}")
        return jsonify({
            'success': False,
            'error': 'Experiment not found'
        }), 404

    except ServiceError as e:
        # Service errors (database, etc.)
        logger.error(f"Service error updating temporal terms for experiment {experiment_id}: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Failed to update temporal terms'
        }), 500

    except Exception as e:
        # Unexpected errors
        logger.error(f"Unexpected error updating temporal terms for experiment {experiment_id}: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@experiments_bp.route('/<int:experiment_id>/get_temporal_terms')
@api_require_login_for_write
def get_temporal_terms(experiment_id):
    """
    Get saved temporal terms and data for an experiment

    REFACTORED: Now uses TemporalService
    """
    try:
        # Get temporal configuration from service
        config = temporal_service.get_temporal_configuration(experiment_id)

        return jsonify({
            'success': True,
            'terms': config['terms'],
            'periods': config['periods'],
            'temporal_data': config['temporal_data']
        }), 200

    except NotFoundError as e:
        logger.warning(f"Experiment {experiment_id} not found: {e}")
        return jsonify({
            'success': False,
            'error': 'Experiment not found'
        }), 404

    except ServiceError as e:
        logger.error(f"Service error getting temporal terms for experiment {experiment_id}: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Failed to get temporal terms'
        }), 500

    except Exception as e:
        logger.error(f"Unexpected error getting temporal terms for experiment {experiment_id}: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@experiments_bp.route('/<int:experiment_id>/generate_periods_from_documents', methods=['POST'])
@api_require_login_for_write
def generate_periods_from_documents(experiment_id):
    """
    Generate time periods based on document publication dates

    Analyzes all documents in the experiment and creates evenly-spaced
    time periods covering the date range.
    """
    try:
        # Generate periods from document dates
        result = temporal_service.generate_periods_from_documents(experiment_id)

        return jsonify({
            'success': True,
            'periods': result['periods'],
            'document_count': result['document_count'],
            'date_range': result['date_range'],
            'source_type': result.get('source_type', 'publication dates'),
            'using_fallback': result.get('using_fallback', False),
            'message': f"Generated {len(result['periods'])} periods from {result['document_count']} documents"
        }), 200

    except ValidationError as e:
        # Business validation errors
        logger.warning(f"Validation error generating periods: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400

    except NotFoundError as e:
        logger.warning(f"Experiment {experiment_id} not found: {e}")
        return jsonify({
            'success': False,
            'error': 'Experiment not found'
        }), 404

    except ServiceError as e:
        logger.error(f"Service error generating periods for experiment {experiment_id}: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Failed to generate periods from documents'
        }), 500

    except Exception as e:
        logger.error(f"Unexpected error generating periods for experiment {experiment_id}: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@experiments_bp.route('/<int:experiment_id>/fetch_temporal_data', methods=['POST'])
@api_require_login_for_write
def fetch_temporal_data(experiment_id):
    """
    Fetch temporal data for a term across time periods using advanced temporal analysis

    REFACTORED: Now uses TemporalService with DTO validation
    """
    try:
        # Validate request data using DTO
        data = FetchTemporalDataDTO(**request.get_json())

        # Call service to fetch temporal analysis
        result = temporal_service.fetch_temporal_analysis(
            experiment_id,
            term=data.term,
            periods=data.periods,
            use_oed=data.use_oed
        )

        response = {
            'success': True,
            'temporal_data': result['temporal_data'],
            'frequency_data': result['frequency_data'],
            'drift_analysis': result['drift_analysis'],
            'narrative': result['narrative'],
            'periods_used': result['periods_used']
        }

        # Add OED data if available
        if 'oed_data' in result:
            response['oed_data'] = result['oed_data']

        return jsonify(response), 200

    except PydanticValidationError as e:
        # Validation errors from DTO
        logger.warning(f"Validation error fetching temporal data for experiment {experiment_id}: {e}")
        return jsonify({
            'success': False,
            'error': 'Validation failed',
            'details': e.errors()
        }), 400

    except ValidationError as e:
        # Business validation errors
        logger.warning(f"Business validation error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400

    except NotFoundError as e:
        logger.warning(f"Experiment {experiment_id} not found: {e}")
        return jsonify({
            'success': False,
            'error': 'Experiment not found'
        }), 404

    except ServiceError as e:
        # Service errors
        logger.error(f"Service error fetching temporal data for experiment {experiment_id}: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Failed to fetch temporal data'
        }), 500

    except Exception as e:
        # Unexpected errors
        logger.error(f"Unexpected error fetching temporal data for experiment {experiment_id}: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': f'Server error: {str(e)}'
        }), 500


@experiments_bp.route('/<int:experiment_id>/documents', methods=['GET'])
@api_require_login_for_write
def get_experiment_documents(experiment_id):
    """
    Get all documents in an experiment for semantic event linking

    Returns basic document information (id, title) for use in dropdowns
    """
    try:
        from app.models import Document

        experiment = Experiment.query.filter_by(id=experiment_id).first()
        if not experiment:
            return jsonify({
                'success': False,
                'error': 'Experiment not found'
            }), 404

        documents = Document.query.filter_by(experiment_id=experiment_id).all()

        return jsonify({
            'success': True,
            'documents': [
                {
                    'id': doc.id,
                    'uuid': str(doc.uuid),
                    'title': doc.title or 'Untitled Document',
                    'publication_date': doc.publication_date.isoformat() if doc.publication_date else None
                }
                for doc in documents
            ]
        }), 200

    except Exception as e:
        logger.error(f"Error getting documents for experiment {experiment_id}: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


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
        from app.models import Document
        import json

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

        # Create/update event
        event_obj = {
            'id': event_id,
            'event_type': event_type,
            'from_period': from_period,
            'to_period': to_period,
            'description': description,
            'related_documents': related_documents
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
        import json

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

        # Remove event
        semantic_events = [e for e in semantic_events if e.get('id') != event_id]

        # Save configuration
        config['semantic_events'] = semantic_events
        experiment.configuration = json.dumps(config)
        db.session.commit()

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
