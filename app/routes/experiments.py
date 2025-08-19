from flask import Blueprint, render_template, request, jsonify, flash, redirect, url_for
from flask_login import login_required, current_user
from app import db
from app.models import Document, Experiment
from datetime import datetime
import json
from app.services.text_processing import TextProcessingService
from app.services.experiment_domain_comparison import DomainComparisonService

# Note: experiments.configuration may include a `design` object per Phase 1b of metadata plan.
# Analysis services should read optional design = config.get('design') to drive factor/group logic.

experiments_bp = Blueprint('experiments', __name__, url_prefix='/experiments')

@experiments_bp.route('/')
@login_required
def index():
    """List all experiments for the current user"""
    experiments = Experiment.query.filter_by(user_id=current_user.id).order_by(Experiment.created_at.desc()).all()
    return render_template('experiments/index.html', experiments=experiments)

@experiments_bp.route('/new')
@login_required
def new():
    """Create a new experiment"""
    # Get documents and references separately for the current user
    documents = Document.query.filter_by(user_id=current_user.id, document_type='document').order_by(Document.created_at.desc()).all()
    references = Document.query.filter_by(user_id=current_user.id, document_type='reference').order_by(Document.created_at.desc()).all()
    return render_template('experiments/new.html', documents=documents, references=references)

@experiments_bp.route('/wizard')
@login_required
def wizard():
    """Guided wizard to create an experiment with design options (Choi-inspired)."""
    documents = Document.query.filter_by(user_id=current_user.id, document_type='document').order_by(Document.created_at.desc()).all()
    references = Document.query.filter_by(user_id=current_user.id, document_type='reference').order_by(Document.created_at.desc()).all()
    return render_template('experiments/wizard.html', documents=documents, references=references)

@experiments_bp.route('/create', methods=['POST'])
@login_required
def create():
    """Create a new experiment"""
    try:
        data = request.get_json()
        
        # Validate required fields
        if not data.get('name'):
            return jsonify({'error': 'Experiment name is required'}), 400
        
        if not data.get('experiment_type'):
            return jsonify({'error': 'Experiment type is required'}), 400
        
        # For most experiments, at least one document is required.
        # Exception: domain_comparison can use references only when configuration.use_references is true.
        config = data.get('configuration', {}) or {}
        use_refs_only = data.get('experiment_type') == 'domain_comparison' and config.get('use_references')
        if (not data.get('document_ids') or len(data['document_ids']) == 0) and not use_refs_only:
            return jsonify({'error': 'At least one document must be selected'}), 400

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
        for doc_id in data.get('document_ids', []) or []:
            document = Document.query.filter_by(id=doc_id, user_id=current_user.id).first()
            if document:
                experiment.add_document(document)

        # Add references to the experiment (optional)
        for ref_id in data.get('reference_ids', []) or []:
            reference = Document.query.filter_by(id=ref_id, user_id=current_user.id, document_type='reference').first()
            if reference:
                experiment.add_reference(reference, include_in_analysis=True)

        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Experiment created successfully',
            'experiment_id': experiment.id
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@experiments_bp.route('/sample', methods=['POST', 'GET'])
@login_required
def create_sample():
    """Create a sample domain comparison experiment using available references and a simple design."""
    try:
        # Pick up to 6 most recent references
        refs = Document.query.filter_by(user_id=current_user.id, document_type='reference').order_by(Document.created_at.desc()).limit(6).all()
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
@login_required
def view(experiment_id):
    """View experiment details"""
    experiment = Experiment.query.filter_by(id=experiment_id, user_id=current_user.id).first_or_404()
    return render_template('experiments/view.html', experiment=experiment)

@experiments_bp.route('/<int:experiment_id>/edit')
@login_required
def edit(experiment_id):
    """Edit experiment"""
    experiment = Experiment.query.filter_by(id=experiment_id, user_id=current_user.id).first_or_404()
    
    # Can only edit experiments that are not running
    if experiment.status == 'running':
        flash('Cannot edit an experiment that is currently running', 'error')
        return redirect(url_for('experiments.view', experiment_id=experiment_id))
    
    # Get all documents for the current user
    documents = Document.query.filter_by(user_id=current_user.id).order_by(Document.created_at.desc()).all()
    
    # Get IDs of documents already in the experiment
    selected_doc_ids = [doc.id for doc in experiment.documents]
    
    return render_template('experiments/edit.html', 
                         experiment=experiment, 
                         documents=documents,
                         selected_doc_ids=selected_doc_ids)

@experiments_bp.route('/<int:experiment_id>/update', methods=['POST'])
@login_required
def update(experiment_id):
    """Update experiment"""
    try:
        experiment = Experiment.query.filter_by(id=experiment_id, user_id=current_user.id).first_or_404()
        
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
                document = Document.query.filter_by(id=doc_id, user_id=current_user.id).first()
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
@login_required
def delete(experiment_id):
    """Delete experiment"""
    try:
        experiment = Experiment.query.filter_by(id=experiment_id, user_id=current_user.id).first_or_404()
        
        # Can only delete experiments that are not running
        if experiment.status == 'running':
            return jsonify({'error': 'Cannot delete an experiment that is currently running'}), 400
        
        db.session.delete(experiment)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Experiment deleted successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500

@experiments_bp.route('/<int:experiment_id>/run', methods=['POST'])
@login_required
def run(experiment_id):
    """Run an experiment"""
    try:
        experiment = Experiment.query.filter_by(id=experiment_id, user_id=current_user.id).first_or_404()
        
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
@login_required
def results(experiment_id):
    """View experiment results"""
    experiment = Experiment.query.filter_by(id=experiment_id, user_id=current_user.id).first_or_404()
    
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
@login_required
def api_list():
    """API endpoint to list experiments"""
    experiments = Experiment.query.filter_by(user_id=current_user.id).order_by(Experiment.created_at.desc()).all()
    return jsonify({
        'experiments': [exp.to_dict() for exp in experiments]
    })

@experiments_bp.route('/api/<int:experiment_id>')
@login_required
def api_get(experiment_id):
    """API endpoint to get experiment details"""
    experiment = Experiment.query.filter_by(id=experiment_id, user_id=current_user.id).first_or_404()
    return jsonify(experiment.to_dict(include_documents=True))
