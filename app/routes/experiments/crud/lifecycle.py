"""Experiment duplication, execution, completion, and deletion."""

from flask import render_template, request, jsonify, flash, redirect, url_for
from flask_login import current_user
from app.utils.auth_decorators import api_require_login_for_write, write_login_required
from app import db
from app.models import Document, Experiment
from app.services.text_processing import TextProcessingService
from app.services.experiment_domain_comparison import DomainComparisonService
from app.dto.experiment_dto import (
    CreateExperimentDTO,
    UpdateExperimentDTO,
    ExperimentResponseDTO,
    ExperimentListItemDTO,
    ExperimentDetailDTO
)
from app.services.base_service import ServiceError, ValidationError
from pydantic import ValidationError as PydanticValidationError
from datetime import datetime
import json
from typing import Optional
from .. import experiments_bp
from .context import experiment_service, logger


@experiments_bp.route('/<int:experiment_id>/delete', methods=['POST'])
@api_require_login_for_write
def delete(experiment_id):
    """
    Delete experiment and all associated processing data

    REFACTORED: Now uses ExperimentService with cascading deletes
    Note: Original documents are preserved (not deleted)
    """
    try:
        # Call service to delete experiment (all cascading logic in service)
        experiment_service.delete_experiment(experiment_id, current_user.id)

        # Return consistent response
        return jsonify({
            'success': True,
            'message': 'Experiment and all associated processing data deleted successfully'
        }), 200

    except ValidationError as e:
        # Business validation errors (e.g., cannot delete running experiment)
        logger.warning(f"Validation error deleting experiment {experiment_id}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400

    except PermissionError as e:
        # Permission errors
        logger.warning(f"Permission error deleting experiment {experiment_id}: {e}")
        return jsonify({
            'success': False,
            'error': 'Permission denied'
        }), 403

    except ServiceError as e:
        # Service errors (database, etc.)
        logger.error(f"Service error deleting experiment {experiment_id}: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Failed to delete experiment'
        }), 500

    except Exception as e:
        # Unexpected errors
        logger.error(f"Unexpected error deleting experiment {experiment_id}: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'An unexpected error occurred'
        }), 500

@experiments_bp.route('/<int:experiment_id>/duplicate', methods=['POST'])
@api_require_login_for_write
def duplicate(experiment_id):
    """
    Duplicate an experiment to create an editable copy.

    Used when an experiment has been run and is locked for provenance.
    Creates a new experiment in 'draft' status with the same configuration.
    """
    from app.models.experiment import ExperimentDocument, ExperimentReference

    try:
        original = Experiment.query.filter_by(id=experiment_id).first_or_404()

        # Create new experiment with copied settings
        new_experiment = Experiment(
            name=f"{original.name} (Copy)",
            description=original.description,
            experiment_type=original.experiment_type,
            status='draft',
            created_by=current_user.id
        )
        db.session.add(new_experiment)
        db.session.flush()  # Get the new ID

        # Copy document associations
        for exp_doc in original.experiment_documents:
            new_exp_doc = ExperimentDocument(
                experiment_id=new_experiment.id,
                document_id=exp_doc.document_id,
                processing_status='pending'
            )
            db.session.add(new_exp_doc)

        # Copy reference associations
        for exp_ref in original.experiment_references:
            new_exp_ref = ExperimentReference(
                experiment_id=new_experiment.id,
                document_id=exp_ref.document_id
            )
            db.session.add(new_exp_ref)

        # Copy term associations if any
        for term in original.terms:
            new_experiment.terms.append(term)

        db.session.commit()

        flash(f'Created new experiment "{new_experiment.name}" from "{original.name}". You can now edit and run it.', 'success')

        return jsonify({
            'success': True,
            'message': f'Experiment duplicated successfully',
            'new_experiment_id': new_experiment.id,
            'redirect_url': url_for('experiments.edit', experiment_id=new_experiment.id)
        }), 200

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error duplicating experiment {experiment_id}: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Failed to duplicate experiment'
        }), 500

@experiments_bp.route('/<int:experiment_id>/mark-complete', methods=['POST'])
@api_require_login_for_write
def mark_complete(experiment_id):
    """
    Manually mark a draft experiment as complete.

    Use this for experiments that were processed manually (without LLM orchestration)
    to lock them and preserve provenance integrity.
    """
    try:
        experiment = Experiment.query.get_or_404(experiment_id)

        # Can only mark draft experiments as complete
        if experiment.status != 'draft':
            return jsonify({
                'success': False,
                'error': f'Cannot mark {experiment.status} experiment as complete. Only draft experiments can be marked complete.'
            }), 400

        # Check that there are some processing results
        from app.models.processing_artifact_group import ProcessingArtifactGroup
        from app.models.document_index import DocumentProcessingIndex
        processing_count = ProcessingArtifactGroup.query.filter_by(experiment_id=experiment_id).count()
        index_count = DocumentProcessingIndex.query.join(Document).filter(Document.experiment_id == experiment_id).count()

        if processing_count == 0 and index_count == 0:
            return jsonify({
                'success': False,
                'error': 'No processing results found. Process at least one document before marking complete.'
            }), 400

        # Mark as completed
        experiment.status = 'completed'
        experiment.completed_at = datetime.utcnow()
        db.session.commit()

        logger.info(f"Experiment {experiment_id} manually marked as complete by user {current_user.id}")

        return jsonify({
            'success': True,
            'message': 'Experiment marked as complete',
            'status': 'completed'
        }), 200

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error marking experiment {experiment_id} as complete: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Failed to mark experiment as complete'
        }), 500

@experiments_bp.route('/<int:experiment_id>/run', methods=['POST'])
@api_require_login_for_write
def run(experiment_id):
    """Run an experiment"""
    try:
        experiment = Experiment.query.filter_by(id=experiment_id).first_or_404()

        if not experiment.can_run():
            return jsonify({'error': 'Experiment cannot be run in its current state'}), 400

        # Update experiment status
        experiment.status = 'running'
        experiment.started_at = datetime.utcnow()
        db.session.commit()

        # Run analysis based on experiment type
        results = None
        summary = None
        if experiment.experiment_type == 'domain_comparison':
            text_service = TextProcessingService()
            service = DomainComparisonService()
            results, summary = service.run(experiment, text_service)
        else:
            # Placeholder for other experiment types
            results = {
                'document_count': experiment.get_document_count(),
                'total_words': experiment.get_total_word_count(),
                'experiment_type': experiment.experiment_type,
                'timestamp': datetime.utcnow().isoformat()
            }
            summary = f"Analyzed {experiment.get_document_count()} documents with {experiment.get_total_word_count()} total words."

        # Save results
        experiment.status = 'completed'
        experiment.completed_at = datetime.utcnow()
        experiment.results_summary = summary
        experiment.results = json.dumps(results)

        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Experiment completed successfully',
            'results_summary': experiment.results_summary
        })

    except Exception as e:
        db.session.rollback()
        experiment.status = 'error'
        db.session.commit()
        return jsonify({'error': str(e)}), 500
