"""Temporal experiment document API routes."""

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


@experiments_bp.route('/<int:experiment_id>/documents', methods=['GET'])
@api_require_login_for_write
def get_experiment_documents(experiment_id):
    """
    Get all documents in an experiment for semantic event linking

    Returns basic document information (id, title) for use in dropdowns
    """
    try:
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
