"""
Experiments CRUD Operations

This module handles basic Create, Read, Update, Delete operations for experiments.

Routes:
- GET  /experiments/                     - List all experiments
- GET  /experiments/new                  - New experiment form
- GET  /experiments/wizard               - Experiment creation wizard
- POST /experiments/create               - Create experiment
- POST /experiments/sample               - Create sample experiment
- GET  /experiments/<id>                 - View experiment details
- GET  /experiments/<id>/edit            - Edit experiment form
- POST /experiments/<id>/update          - Update experiment
- POST /experiments/<id>/delete          - Delete experiment
- POST /experiments/<id>/run             - Run experiment
- GET  /experiments/<id>/results         - View experiment results
- GET  /experiments/api/list             - API: List experiments
- GET  /experiments/api/<id>             - API: Get experiment
"""

from flask import render_template, request, jsonify, flash, redirect, url_for
from flask_login import current_user
from app.utils.auth_decorators import api_require_login_for_write, write_login_required
from app import db
from app.models import Document, Experiment
from app.services.text_processing import TextProcessingService
from app.services.experiment_domain_comparison import DomainComparisonService
from app.services.experiment_service import get_experiment_service
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
import logging

from . import experiments_bp

logger = logging.getLogger(__name__)
experiment_service = get_experiment_service()


@experiments_bp.route('/')
def index():
    """List all experiments for all users - public view"""
    experiments = Experiment.query.order_by(Experiment.created_at.desc()).all()
    return render_template('experiments/index.html', experiments=experiments)


@experiments_bp.route('/new')
@write_login_required
def new():
    """Show new experiment form - requires login"""
    from app.models import Term

    # Get documents and references separately for all users
    # Only show original (v1) documents - derived versions belong to their source experiments
    documents = Document.query.filter_by(document_type='document', version_type='original').order_by(Document.created_at.desc()).all()
    references = Document.query.filter_by(document_type='reference', version_type='original').order_by(Document.created_at.desc()).all()

    # Get all terms for the focus term dropdown
    terms = Term.query.order_by(Term.term_text).all()

    # Handle single document mode
    mode = request.args.get('mode')
    selected_document = None
    document_title = None
    document_uuid = None
    generated_description = None

    if mode == 'single_document':
        document_uuid = request.args.get('document_uuid')
        document_title = request.args.get('document_title')

        if document_uuid:
            selected_document = Document.query.filter_by(uuid=document_uuid).first()
            if selected_document:
                # Use document title (from metadata), fall back to display name
                title = selected_document.title or selected_document.get_display_name()
                generated_description = f"Document analysis of {title}"

    return render_template('experiments/new.html',
                         documents=documents,
                         references=references,
                         terms=terms,
                         mode=mode,
                         selected_document=selected_document,
                         document_title=document_title,
                         document_uuid=document_uuid,
                         generated_description=generated_description)


@experiments_bp.route('/wizard')
@write_login_required
def wizard():
    """Guided wizard to create an experiment - requires login"""
    # Only show original (v1) documents - derived versions belong to their source experiments
    documents = Document.query.filter_by(document_type='document', version_type='original').order_by(Document.created_at.desc()).all()
    references = Document.query.filter_by(document_type='reference', version_type='original').order_by(Document.created_at.desc()).all()
    return render_template('experiments/wizard.html', documents=documents, references=references)


@experiments_bp.route('/create', methods=['POST'])
@api_require_login_for_write
def create():
    """
    Create a new experiment - requires login

    REFACTORED: Now uses ExperimentService with DTO validation
    """
    try:
        # Validate request data using DTO (automatic validation)
        data = CreateExperimentDTO(**request.get_json())

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
            'details': e.errors()
        }), 400

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


@experiments_bp.route('/sample', methods=['POST', 'GET'])
@write_login_required
def create_sample():
    """
    Create a sample domain comparison experiment

    REFACTORED: Now uses ExperimentService with DTO validation
    """
    try:
        # Pick up to 6 most recent references
        refs = Document.query.filter_by(document_type='reference').order_by(
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
            reference_ids=[r.id for r in refs],
            configuration=config
        )

        # Call service to create experiment (all business logic in service)
        experiment = experiment_service.create_experiment(data, current_user.id)

        flash('Sample experiment created.', 'success')
        return redirect(url_for('experiments.view', experiment_id=experiment.id))

    except ServiceError as e:
        logger.error(f"Service error creating sample experiment: {e}", exc_info=True)
        flash(f'Error creating sample experiment: {e}', 'danger')
        return redirect(url_for('experiments.index'))

    except Exception as e:
        logger.error(f"Unexpected error creating sample experiment: {e}", exc_info=True)
        flash(f'Error creating sample experiment: {e}', 'danger')
        return redirect(url_for('experiments.index'))


@experiments_bp.route('/<int:experiment_id>')
def view(experiment_id):
    """View experiment details - Enhanced dashboard view"""
    experiment = Experiment.query.filter_by(id=experiment_id).first_or_404()

    # Get most recent orchestration run for this experiment
    from app.models import ExperimentOrchestrationRun
    from sqlalchemy import func

    recent_orchestration = ExperimentOrchestrationRun.query.filter_by(
        experiment_id=experiment_id
    ).order_by(ExperimentOrchestrationRun.started_at.desc()).first()

    # Get all documents in this experiment
    experiment_docs = list(experiment.documents)
    doc_ids = [doc.id for doc in experiment_docs]

    # --- Processing Summary ---
    # Use the same data sources as document_pipeline: ExperimentDocumentProcessing & DocumentProcessingIndex
    from app.models.experiment_processing import ExperimentDocumentProcessing, DocumentProcessingIndex
    from app.models import ExperimentDocument

    processing_summary = {}  # artifact_type -> count

    # --- Document Details with Versions and Cross-Experiment Usage ---
    documents_enhanced = []
    for doc in experiment_docs:
        # Count how many OTHER experiments use this document
        other_exp_count = doc.experiments.count() - 1  # Exclude current experiment

        # Get ExperimentDocument for this doc+experiment
        exp_doc = ExperimentDocument.query.filter_by(
            experiment_id=experiment_id,
            document_id=doc.id
        ).first()

        # Collect processing operations from both systems
        operations_list = []

        if exp_doc:
            # 1. Check manual processing operations (from process_document page buttons)
            manual_ops = ExperimentDocumentProcessing.query.filter_by(
                experiment_document_id=exp_doc.id,
                status='completed'
            ).all()

            for op in manual_ops:
                operations_list.append({
                    'type': op.processing_type,
                    'method': op.processing_method,
                    'source': 'manual'
                })

        # 2. Check DocumentProcessingIndex (experiment-specific processing)
        index_entries = DocumentProcessingIndex.query.filter_by(
            document_id=doc.id,
            experiment_id=experiment_id,
            status='completed'
        ).all()

        for entry in index_entries:
            operations_list.append({
                'type': entry.processing_type,
                'method': entry.processing_method,
                'source': 'experiment'
            })

        # 3. Check orchestration results if available
        if recent_orchestration and recent_orchestration.processing_results:
            doc_id_str = str(doc.id)
            if doc_id_str in recent_orchestration.processing_results:
                llm_ops = recent_orchestration.processing_results[doc_id_str]
                for tool_name, tool_result in llm_ops.items():
                    if tool_result.get('status') == 'executed':
                        operations_list.append({
                            'type': tool_name,
                            'method': 'llm',
                            'source': 'llm'
                        })

        # Deduplicate by (type, method)
        seen = set()
        unique_operations = []
        for op in operations_list:
            key = (op['type'], op['method'])
            if key not in seen:
                seen.add(key)
                unique_operations.append(op)

        # Group by artifact type for template display
        doc_processing_by_type = {}
        for op in unique_operations:
            artifact_type = op['type']
            if artifact_type not in doc_processing_by_type:
                doc_processing_by_type[artifact_type] = []
            doc_processing_by_type[artifact_type].append({
                'method_key': op['method'],
                'source': op['source']
            })
            # Update global summary
            processing_summary[artifact_type] = processing_summary.get(artifact_type, 0) + 1

        documents_enhanced.append({
            'document': doc,
            'other_experiments_count': other_exp_count,
            'processing_by_type': doc_processing_by_type,
            'processing_count': len(unique_operations)
        })

    # Count total processing operations across all documents
    total_processing_ops = sum(processing_summary.values())

    # --- Temporal Periods (for temporal_evolution experiments) ---
    temporal_data = None
    if experiment.experiment_type == 'temporal_evolution':
        try:
            from app.services.temporal_service import get_temporal_service
            temporal_service = get_temporal_service()
            temporal_data = temporal_service.get_temporal_ui_data(experiment_id)
        except Exception as e:
            logger.warning(f"Failed to get temporal data for experiment {experiment_id}: {e}")
            temporal_data = None

    return render_template(
        'experiments/view.html',
        experiment=experiment,
        recent_orchestration=recent_orchestration,
        processing_summary=processing_summary,
        total_processing_ops=total_processing_ops,
        documents_enhanced=documents_enhanced,
        temporal_data=temporal_data
    )


@experiments_bp.route('/<int:experiment_id>/edit')
@write_login_required
def edit(experiment_id):
    """Edit experiment"""
    from app.models import Term

    experiment = Experiment.query.filter_by(id=experiment_id).first_or_404()

    # Can only edit experiments that are not running
    if experiment.status == 'running':
        flash('Cannot edit an experiment that is currently running', 'error')
        return redirect(url_for('experiments.view', experiment_id=experiment_id))

    # Get documents and references separately (matching new route structure)
    documents = Document.query.filter_by(document_type='document').order_by(Document.created_at.desc()).all()
    references = Document.query.filter_by(document_type='reference').order_by(Document.created_at.desc()).all()

    # Get all terms for the focus term dropdown
    terms = Term.query.order_by(Term.term_text).all()

    # Get IDs of documents and references already in the experiment
    selected_doc_ids = [doc.id for doc in experiment.documents]
    selected_ref_ids = [ref.id for ref in experiment.references]

    # Get focus term ID from proper term_id foreign key column
    selected_term_ids = []
    if experiment.term_id:
        selected_term_ids = [str(experiment.term_id)]

    return render_template('experiments/edit.html',
                         experiment=experiment,
                         documents=documents,
                         references=references,
                         terms=terms,
                         selected_doc_ids=selected_doc_ids,
                         selected_ref_ids=selected_ref_ids,
                         selected_term_ids=selected_term_ids)


@experiments_bp.route('/<int:experiment_id>/update', methods=['POST'])
@api_require_login_for_write
def update(experiment_id):
    """
    Update an existing experiment

    REFACTORED: Now uses ExperimentService with DTO validation
    """
    try:
        # Validate request data using DTO (automatic validation)
        data = UpdateExperimentDTO(**request.get_json())

        # Call service to update experiment (all business logic in service)
        experiment = experiment_service.update_experiment(experiment_id, data, current_user.id)

        # Return consistent response
        return jsonify({
            'success': True,
            'message': 'Experiment updated successfully',
            'experiment_id': experiment.id
        }), 200

    except PydanticValidationError as e:
        # Validation errors from DTO
        logger.warning(f"Validation error updating experiment {experiment_id}: {e}")
        return jsonify({
            'success': False,
            'error': 'Validation failed',
            'details': e.errors()
        }), 400

    except ValidationError as e:
        # Business validation errors (e.g., cannot update running experiment)
        logger.warning(f"Business validation error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400

    except PermissionError as e:
        # Permission errors
        logger.warning(f"Permission error: {e}")
        return jsonify({
            'success': False,
            'error': 'Permission denied'
        }), 403

    except ServiceError as e:
        # Service errors (database, etc.)
        logger.error(f"Service error updating experiment {experiment_id}: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Failed to update experiment'
        }), 500

    except Exception as e:
        # Unexpected errors
        logger.error(f"Unexpected error updating experiment {experiment_id}: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'An unexpected error occurred'
        }), 500


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


@experiments_bp.route('/<int:experiment_id>/results')
def results(experiment_id):
    """View experiment results"""
    experiment = Experiment.query.filter_by(id=experiment_id).first_or_404()

    if experiment.status != 'completed':
        flash('Experiment has not been completed yet', 'warning')
        return redirect(url_for('experiments.view', experiment_id=experiment_id))

    # Parse results if available
    results_data = {}
    if experiment.results:
        try:
            results_data = json.loads(experiment.results)
        except:
            results_data = {}
    # Parse configuration JSON for template convenience
    config_data = {}
    if experiment.configuration:
        try:
            config_data = json.loads(experiment.configuration)
        except Exception:
            config_data = {}

    return render_template('experiments/results.html',
                         experiment=experiment,
                         results_data=results_data,
                         config_data=config_data)


@experiments_bp.route('/api/list')
def api_list():
    """
    API endpoint to list experiments

    REFACTORED: Now uses ExperimentService with DTOs
    """
    try:
        # Get experiments from service (returns DTOs)
        experiments = experiment_service.list_experiments()

        # Convert DTOs to dicts for JSON response
        return jsonify({
            'success': True,
            'experiments': [exp.to_dict() for exp in experiments]
        }), 200

    except ServiceError as e:
        logger.error(f"Service error listing experiments: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Failed to list experiments'
        }), 500

    except Exception as e:
        logger.error(f"Unexpected error listing experiments: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'An unexpected error occurred'
        }), 500


@experiments_bp.route('/api/<int:experiment_id>')
def api_get(experiment_id):
    """
    API endpoint to get experiment details

    REFACTORED: Now uses ExperimentService with DTOs
    """
    try:
        # Get experiment detail from service (returns DTO)
        experiment = experiment_service.get_experiment_detail(experiment_id)

        # Convert DTO to dict for JSON response
        return jsonify({
            'success': True,
            'experiment': experiment.to_dict()
        }), 200

    except ServiceError as e:
        logger.error(f"Service error getting experiment {experiment_id}: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Experiment not found'
        }), 404

    except Exception as e:
        logger.error(f"Unexpected error getting experiment {experiment_id}: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'An unexpected error occurred'
        }), 500
