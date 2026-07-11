"""Experiment creation routes."""

from flask import flash, jsonify, redirect, request, url_for
from flask_login import current_user
from pydantic import ValidationError as PydanticValidationError

from app.dto.experiment_dto import CreateExperimentDTO
from app.models import Document
from app.services.base_service import (
    NotFoundError,
    PermissionError,
    ServiceError,
    ValidationError,
)
from app.utils.auth_decorators import api_require_login_for_write, write_login_required

from .. import experiments_bp
from .context import experiment_service, logger


@experiments_bp.route('/create', methods=['POST'])
@api_require_login_for_write
def create():
    """
    Create a new experiment - requires login

    REFACTORED: Now uses ExperimentService with DTO validation
    """
    try:
        # Validate request data using DTO (automatic validation)
        data = CreateExperimentDTO(**(request.get_json(silent=True) or {}))

        # Call service to create experiment (all business logic in service)
        experiment = experiment_service.create_experiment(data, current_user.id)

        # Return consistent response
        return jsonify({
            'success': True,
            'message': 'Experiment created successfully',
            'experiment_id': experiment.id,
            'redirect': url_for('experiments.document_pipeline', experiment_id=experiment.id)
        }), 201

    except PydanticValidationError as e:
        # Validation errors from DTO
        logger.warning(f"Validation error creating experiment: {e}")
        return jsonify({
            'success': False,
            'error': 'Validation failed',
            'details': e.errors(include_context=False)
        }), 400

    except NotFoundError as e:
        return jsonify({'success': False, 'error': str(e)}), 404

    except PermissionError:
        return jsonify({'success': False, 'error': 'Permission denied'}), 403

    except ValidationError as e:
        # Business validation errors from service
        logger.warning(f"Business validation error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400

    except ServiceError as e:
        # Service errors (database, etc.)
        logger.error(f"Service error creating experiment: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Failed to create experiment'
        }), 500

    except Exception as e:
        # Unexpected errors
        logger.error(f"Unexpected error creating experiment: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'An unexpected error occurred'
        }), 500

@experiments_bp.route('/sample', methods=['POST'])
@write_login_required
def create_sample():
    """
    Create a sample domain comparison experiment

    REFACTORED: Now uses ExperimentService with DTO validation
    """
    try:
        # Pick up to 6 most recent references
        query = Document.query.filter_by(
            document_type='reference',
            version_type='original',
        )
        if not current_user.is_admin:
            query = query.filter_by(user_id=current_user.id)
        refs = query.order_by(
            Document.created_at.desc()
        ).limit(6).all()

        if not refs:
            flash('No references found. Please upload reference PDFs first (References → Upload).', 'warning')
            return redirect(url_for('experiments.index'))

        # Build sample configuration
        config = {
            "use_references": True,
            "target_terms": ["agent", "agency"],
            "design": {
                "type": "experimental",
                "variables": {
                    "independent": [{"name": "definition_source", "levels": ["OED", "AI textbook"]}]
                },
                "groups": [{"name": "OED"}, {"name": "AI"}]
            }
        }

        # Create DTO with sample data
        data = CreateExperimentDTO(
            name='Sample: Agent Domain Comparison',
            description='Auto-created sample comparing terminology across sources with a simple design.',
            experiment_type='domain_comparison',
            reference_uuids=[str(reference.uuid) for reference in refs],
            configuration=config
        )

        # Call service to create experiment (all business logic in service)
        experiment = experiment_service.create_experiment(data, current_user.id)

        flash('Sample experiment created.', 'success')
        return redirect(url_for('experiments.view', experiment_id=experiment.id))

    except (NotFoundError, PermissionError, ValidationError) as e:
        logger.warning(f"Could not create sample experiment: {e}")
        flash('Could not create sample experiment', 'danger')
        return redirect(url_for('experiments.index'))

    except ServiceError as e:
        logger.error(f"Service error creating sample experiment: {e}", exc_info=True)
        flash('Error creating sample experiment', 'danger')
        return redirect(url_for('experiments.index'))

    except Exception as e:
        logger.error(f"Unexpected error creating sample experiment: {e}", exc_info=True)
        flash('Error creating sample experiment', 'danger')
        return redirect(url_for('experiments.index'))
