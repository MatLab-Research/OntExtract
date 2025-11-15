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
from app.utils.auth_decorators import api_require_login_for_write
from app import db
from app.models import Document, Experiment
from app.services.text_processing import TextProcessingService
from app.services.experiment_domain_comparison import DomainComparisonService
from datetime import datetime
import json
from typing import Optional

from . import experiments_bp


@experiments_bp.route('/')
def index():
    """List all experiments for all users - public view"""
    experiments = Experiment.query.order_by(Experiment.created_at.desc()).all()
    return render_template('experiments/index.html', experiments=experiments)


@experiments_bp.route('/new')
def new():
    """Show new experiment form - public view, but submit requires login"""
    # Get documents and references separately for all users
    documents = Document.query.filter_by(document_type='document').order_by(Document.created_at.desc()).all()
    references = Document.query.filter_by(document_type='reference').order_by(Document.created_at.desc()).all()
    return render_template('experiments/new.html', documents=documents, references=references)


@experiments_bp.route('/wizard')
def wizard():
    """Guided wizard to create an experiment - public view, but submit requires login"""
    documents = Document.query.filter_by(document_type='document').order_by(Document.created_at.desc()).all()
    references = Document.query.filter_by(document_type='reference').order_by(Document.created_at.desc()).all()
    return render_template('experiments/wizard.html', documents=documents, references=references)


@experiments_bp.route('/create', methods=['POST'])
@api_require_login_for_write
def create():
    """Create a new experiment - requires login"""
    try:
        data = request.get_json()

        # Validate required fields
        if not data.get('name'):
            return jsonify({'error': 'Experiment name is required'}), 400

        if not data.get('experiment_type'):
            return jsonify({'error': 'Experiment type is required'}), 400

        # Validate that at least one document or reference is selected
        # All experiments can use either documents or references
        document_ids = data.get('document_ids') or []
        reference_ids = data.get('reference_ids') or []

        if len(document_ids) == 0 and len(reference_ids) == 0:
            return jsonify({'error': 'At least one document or reference must be selected'}), 400

        # Create the experiment
        experiment = Experiment(
            name=data['name'],
            description=data.get('description', ''),
            experiment_type=data['experiment_type'],
            user_id=current_user.id,
            configuration=json.dumps(data.get('configuration', {}))
        )
        # Important: Add to session before touching dynamic relationships
        db.session.add(experiment)
        db.session.flush()  # ensure experiment has identity for association table

        # Add documents to the experiment
        for doc_id in document_ids:
            document = Document.query.filter_by(id=doc_id).first()
            if document:
                experiment.add_document(document)

        # Add references to the experiment
        for ref_id in reference_ids:
            reference = Document.query.filter_by(id=ref_id, document_type='reference').first()
            if reference:
                experiment.add_reference(reference, include_in_analysis=True)

        db.session.commit()

        # Redirect to document processing pipeline based on experiment type
        return jsonify({
            'success': True,
            'message': 'Experiment created successfully',
            'experiment_id': experiment.id,
            'redirect': url_for('experiments.document_pipeline', experiment_id=experiment.id)
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@experiments_bp.route('/sample', methods=['POST', 'GET'])
@api_require_login_for_write
def create_sample():
    """Create a sample domain comparison experiment using available references and a simple design."""
    try:
        # Pick up to 6 most recent references
        refs = Document.query.filter_by(document_type='reference').order_by(Document.created_at.desc()).limit(6).all()
        if not refs:
            flash('No references found. Please upload reference PDFs first (References → Upload).', 'warning')
            return redirect(url_for('experiments.index'))

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

        experiment = Experiment(
            name='Sample: Agent Domain Comparison',
            description='Auto-created sample comparing terminology across sources with a simple design.',
            experiment_type='domain_comparison',
            user_id=current_user.id,
            configuration=json.dumps(config)
        )
        db.session.add(experiment)
        db.session.flush()

        for r in refs:
            experiment.add_reference(r, include_in_analysis=True)

        db.session.commit()
        flash('Sample experiment created.', 'success')
        return redirect(url_for('experiments.view', experiment_id=experiment.id))
    except Exception as e:
        db.session.rollback()
        flash(f'Error creating sample experiment: {e}', 'danger')
        return redirect(url_for('experiments.index'))


@experiments_bp.route('/<int:experiment_id>')
def view(experiment_id):
    """View experiment details"""
    experiment = Experiment.query.filter_by(id=experiment_id).first_or_404()
    return render_template('experiments/view.html', experiment=experiment)


@experiments_bp.route('/<int:experiment_id>/edit')
@api_require_login_for_write
def edit(experiment_id):
    """Edit experiment"""
    experiment = Experiment.query.filter_by(id=experiment_id).first_or_404()

    # Can only edit experiments that are not running
    if experiment.status == 'running':
        flash('Cannot edit an experiment that is currently running', 'error')
        return redirect(url_for('experiments.view', experiment_id=experiment_id))

    # Get all documents for all users
    documents = Document.query.order_by(Document.created_at.desc()).all()

    # Get IDs of documents already in the experiment
    selected_doc_ids = [doc.id for doc in experiment.documents]

    return render_template('experiments/edit.html',
                         experiment=experiment,
                         documents=documents,
                         selected_doc_ids=selected_doc_ids)


@experiments_bp.route('/<int:experiment_id>/update', methods=['POST'])
@api_require_login_for_write
def update(experiment_id):
    """Update experiment"""
    try:
        experiment = Experiment.query.filter_by(id=experiment_id).first_or_404()

        # Can only update experiments that are not running
        if experiment.status == 'running':
            return jsonify({'error': 'Cannot update an experiment that is currently running'}), 400

        data = request.get_json()

        # Update basic fields
        if 'name' in data:
            experiment.name = data['name']
        if 'description' in data:
            experiment.description = data['description']
        if 'experiment_type' in data:
            experiment.experiment_type = data['experiment_type']
        if 'configuration' in data:
            experiment.configuration = json.dumps(data['configuration'])

        # Update documents if provided
        if 'document_ids' in data:
            # Clear existing documents
            experiment.documents = []

            # Add new documents
            for doc_id in data['document_ids']:
                document = Document.query.filter_by(id=doc_id).first()
                if document:
                    experiment.add_document(document)

        experiment.updated_at = datetime.utcnow()
        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Experiment updated successfully'
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@experiments_bp.route('/<int:experiment_id>/delete', methods=['POST'])
@api_require_login_for_write
def delete(experiment_id):
    """Delete experiment and all associated processing data (but preserve original documents)"""
    try:
        experiment = Experiment.query.filter_by(id=experiment_id).first_or_404()

        # Can only delete experiments that are not running
        if experiment.status == 'running':
            return jsonify({'error': 'Cannot delete an experiment that is currently running'}), 400

        # Import models here to avoid circular imports
        from app.models.experiment_document import ExperimentDocument
        from app.models.experiment_processing import (
            ExperimentDocumentProcessing,
            ProcessingArtifact,
            DocumentProcessingIndex
        )

        # Delete all processing artifacts first (most dependent)
        # Get all processing operations for this experiment's documents
        processing_ops = db.session.query(ExperimentDocumentProcessing).join(
            ExperimentDocument,
            ExperimentDocumentProcessing.experiment_document_id == ExperimentDocument.id
        ).filter(
            ExperimentDocument.experiment_id == experiment_id
        ).all()

        for processing_op in processing_ops:
            # Delete all artifacts for this processing operation
            ProcessingArtifact.query.filter_by(processing_id=processing_op.id).delete()

            # Delete index entries for this processing operation
            DocumentProcessingIndex.query.filter_by(processing_id=processing_op.id).delete()

            # Delete the processing operation itself
            db.session.delete(processing_op)

        # Delete all ExperimentDocument associations
        ExperimentDocument.query.filter_by(experiment_id=experiment_id).delete()

        # Clear the many-to-many relationships (experiment_documents and experiment_references)
        # These use association tables, so we need to clear them manually
        experiment.documents = []  # This clears the association table entries
        experiment.references = []  # This clears the reference associations
        db.session.flush()  # Ensure the associations are cleared before deleting the experiment

        # Finally delete the experiment itself
        db.session.delete(experiment)

        # Commit all deletions
        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Experiment and all associated processing data deleted successfully'
        })

    except Exception as e:
        db.session.rollback()
        import traceback
        error_details = traceback.format_exc()
        print(f"Error deleting experiment {experiment_id}: {error_details}")
        return jsonify({'error': str(e)}), 500


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
    """API endpoint to list experiments"""
    experiments = Experiment.query.order_by(Experiment.created_at.desc()).all()
    return jsonify({
        'experiments': [exp.to_dict() for exp in experiments]
    })


@experiments_bp.route('/api/<int:experiment_id>')
def api_get(experiment_id):
    """API endpoint to get experiment details"""
    experiment = Experiment.query.filter_by(id=experiment_id).first_or_404()
    return jsonify(experiment.to_dict(include_documents=True))
