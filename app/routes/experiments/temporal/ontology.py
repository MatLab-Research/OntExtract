"""Semantic event and period ontology routes."""

from flask import render_template, request, jsonify, flash, redirect, url_for
from flask_login import current_user
from app.utils.auth_decorators import api_require_login_for_write
from app.services.temporal_service import get_temporal_service
from app.services.ontserve_client import get_ontserve_client
from app.services.base_service import ServiceError, ValidationError, NotFoundError
from app.dto.temporal_dto import (
    UpdateTemporalTermsDTO,
    FetchTemporalDataDTO
)
from pydantic import ValidationError as PydanticValidationError
from app.models import Experiment, Document
from app import db
import logging
import json
from .. import experiments_bp


@experiments_bp.route('/ontology/info', methods=['GET'])
def ontology_info():
    """Display ontology validation information and event types"""
    try:
        from app.services.local_ontology_service import get_ontology_service
        from pathlib import Path

        ontology = get_ontology_service()
        event_types = ontology.get_semantic_change_event_types()

        # Get ontology file path for display
        ontology_path = 'ontologies/semantic-change-ontology-v2.ttl'

        # Check if validation guide exists
        validation_guide_path = Path('VALIDATION_GUIDE.md')
        validation_exists = validation_guide_path.exists()

        return render_template(
            'experiments/ontology_info.html',
            event_types=event_types,
            event_count=len(event_types),
            ontology_path=ontology_path,
            validation_exists=validation_exists
        )

    except Exception as e:
        logger.error(f"Error displaying ontology info: {e}", exc_info=True)
        flash('Failed to load ontology information', 'danger')
        return redirect(url_for('experiments.index'))

@experiments_bp.route('/<int:experiment_id>/semantic_event_types', methods=['GET'])
@api_require_login_for_write
def get_semantic_event_types(experiment_id):
    """
    Get semantic change event types from ontology for dropdown.

    Returns event types with definitions and citations for UI display.
    Uses LocalOntologyService to load from local .ttl file (JCDL standalone mode).
    """
    try:
        from app.services.local_ontology_service import get_ontology_service

        ontology = get_ontology_service()
        event_types = ontology.get_all_for_dropdown()

        return jsonify({
            'success': True,
            'event_types': event_types,
            'count': len(event_types),
            'source': 'semantic-change-ontology-v2.ttl'
        }), 200

    except Exception as e:
        logger.error(f"Failed to load event types: {e}", exc_info=True)

        # Fallback to hardcoded types if ontology load fails
        fallback_types = [
            {
                'value': 'pejoration',
                'label': 'Pejoration',
                'definition': 'Negative shift in word meaning or connotation',
                'citation': 'Jatowt & Duh 2014',
                'example': None,
                'uri': None
            },
            {
                'value': 'amelioration',
                'label': 'Amelioration',
                'definition': 'Positive shift in word meaning or connotation',
                'citation': 'Jatowt & Duh 2014',
                'example': None,
                'uri': None
            },
            {
                'value': 'semantic_drift',
                'label': 'Semantic Drift',
                'definition': 'Gradual, incremental meaning change over extended period',
                'citation': 'Hamilton et al. 2016',
                'example': None,
                'uri': None
            }
        ]

        return jsonify({
            'success': True,
            'event_types': fallback_types,
            'count': len(fallback_types),
            'source': 'fallback (ontology load failed)',
            'error': str(e)
        }), 200

@experiments_bp.route('/period_types', methods=['GET'])
def get_period_types():
    """
    Get list of temporal period types from SCO ontology

    Returns:
        JSON with period types array containing:
        - uri: Ontology URI
        - name: Class name
        - label: Human-readable label
        - description: Period type description
        - color: UI color code
        - icon: FontAwesome icon class
    """
    try:
        period_types = ontserve_client.get_period_types()

        # Transform to frontend format
        transformed_types = []
        for period_type in period_types:
            transformed_types.append({
                'value': period_type['name'],
                'label': period_type['label'],
                'description': period_type['description'],
                'uri': period_type['uri'],
                'color': period_type['color'],
                'icon': period_type['icon']
            })

        return jsonify({
            'success': True,
            'period_types': transformed_types,
            'count': len(transformed_types),
            'source': 'ontology'
        }), 200

    except Exception as e:
        logger.error(f"Error fetching period types: {e}", exc_info=True)

        # Return hardcoded fallback
        fallback_types = [
            {
                'value': 'HistoricalPeriod',
                'label': 'Historical Period',
                'description': 'Historically-defined temporal span',
                'color': '#6f42c1',
                'icon': 'fas fa-landmark',
                'uri': None
            },
            {
                'value': 'DisciplinaryEra',
                'label': 'Disciplinary Era',
                'description': 'Era defined by disciplinary conventions',
                'color': '#0d6efd',
                'icon': 'fas fa-graduation-cap',
                'uri': None
            },
            {
                'value': 'TechnologicalEpoch',
                'label': 'Technological Epoch',
                'description': 'Period marked by technological developments',
                'color': '#198754',
                'icon': 'fas fa-microchip',
                'uri': None
            },
            {
                'value': 'CulturalMovement',
                'label': 'Cultural Movement',
                'description': 'Period defined by cultural or intellectual movement',
                'color': '#d63384',
                'icon': 'fas fa-palette',
                'uri': None
            }
        ]

        return jsonify({
            'success': True,
            'period_types': fallback_types,
            'count': len(fallback_types),
            'source': 'fallback (ontology load failed)',
            'error': str(e)
        }), 200
